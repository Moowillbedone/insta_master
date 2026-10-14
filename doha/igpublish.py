"""승인된 게시물을 Instagram API(Instagram 로그인 방식)로 게시 — research/ig-auto-publish.md 의 B안.

  python doha.py ig-publish <게시물> --dry-run      4:5 렌더 → JPEG 변환·검사까지만 (업로드·API 호출 없음)
  python doha.py ig-publish <게시물> --mock         내장 모의 서버로 전체 흐름 리허설 (post.yaml 은 그대로)
  python doha.py ig-publish <게시물>                실제 게시 (post.yaml status: approved 필요)
  python doha.py ig-publish <게시물> --reel --account-ai-label-on    릴스(out/reel/reel.mp4) 게시
  python doha.py ig-publish --refresh-token         60일 장기 토큰 갱신 (토큰 값은 출력하지 않음)
  python doha.py ig-publish --check-setup           환경 변수·SigV4 서명 자체 시험·API 연결 확인

흐름 (카드뉴스): 검수(check) → 1080x1350(4:5) 렌더 → sRGB JPEG(8MB 이하, 최대 10장) → R2 업로드 → 공개 주소 확인
  → 장마다 컨테이너(is_carousel_item) → CAROUSEL 컨테이너(캡션 = preview.build_caption) → status_code FINISHED 대기
  → 게시 한도 확인 → media_publish → permalink 조회 → post.yaml 의 posted.url·posted_at·status 기록 → R2 정리.

안전장치:
  - post.yaml status 가 approved 여야 함 (사람의 하루 1번 승인). --force-status 는 경고 후 진행
  - post.yaml date·time(KST) 예정 시각 전이면 게시하지 않음 (--now 로 지금 게시)
  - check 오류, 사진 파일 없음(자리표시), 반려 사진이 있으면 게시하지 않음
  - 광고·협찬·제휴 게시물은 --paid-partnership 을 줘야 게시 (is_paid_partnership=true, Instagram 로그인 방식 지원 [미확인])
  - 이미 posted.url 이 있거나 최근 게시물에 같은 캡션이 있으면 다시 올리지 않음 (중복 게시 방지)
  - media_publish 응답이 끊기거나 서버 오류(5xx)면 최근 게시물 목록부터 확인하고, 못 찾으면 다음 실행에서 이어서 확인
    (지난 실행의 캡션도 함께 비교 — 사이에 캡션을 고쳐도 중복 게시 안 함)
  - JPEG 에 IPTC DigitalSourceType(AI 합성) XMP 를 넣음 — Meta 가 읽고 'AI 정보' 라벨을 붙일 수 있음 [미확인]

환경 변수 (값은 절대 출력하지 않음): IG_ACCESS_TOKEN, IG_USER_ID(비우면 /me 로 조회), IG_API_BASE(기본
https://graph.instagram.com), IG_API_VERSION(선택, 예: v24.0), R2_* (doha/r2.py 참고).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import struct
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

from doha.core import ROOT, Post, load_config, load_persona, resolve_post, shortcode, skip_if_legacy

KST = timezone(timedelta(hours=9))
DEFAULT_BASE = "https://graph.instagram.com"
MAX_ITEMS = 10                      # API 캐러셀 최대 장수 (앱은 20)
MAX_JPEG_BYTES = 8 * 1024 * 1024
RATIO_RANGE = (0.8, 1.91)           # 피드 이미지 허용 비율 4:5 ~ 1.91:1
WIDTH_RANGE = (320, 1440)
CAPTION_LIMIT = 2200
MAX_HASHTAGS_API = 30
LOCK_STALE = timedelta(hours=1)
EXIT_OK, EXIT_ERROR, EXIT_REFUSED = 0, 1, 2

# IPTC 디지털 출처 유형: AI 생성 이미지 위에 글자를 얹은 합성물 (https://cv.iptc.org/newscodes/digitalsourcetype/)
DIGITAL_SOURCE_TYPE = "http://cv.iptc.org/newscodes/digitalsourcetype/compositeWithTrainedAlgorithmicMedia"
XMP_PACKET = (
    '<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>'
    '<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
    '<rdf:Description rdf:about="" xmlns:Iptc4xmpExt="http://iptc.org/std/Iptc4xmpExt/2008-02-29/" '
    f'Iptc4xmpExt:DigitalSourceType="{DIGITAL_SOURCE_TYPE}"/>'
    '</rdf:RDF></x:xmpmeta><?xpacket end="r"?>'
).encode("utf-8")
XMP_HEADER = b"http://ns.adobe.com/xap/1.0/\x00"


# ================================================================ CLI

def add_arguments(parser) -> None:
    parser.add_argument("post", nargs="?", help="게시물 id 일부, 폴더 또는 post.yaml 경로")
    parser.add_argument("--dry-run", action="store_true", help="렌더·JPEG 변환·검사만 하고 업로드·게시하지 않음")
    parser.add_argument("--mock", action="store_true",
                        help="내장 모의 서버(R2+Graph API)로 전체 흐름 리허설. post.yaml 은 바뀌지 않음")
    parser.add_argument("--now", action="store_true",
                        help="post.yaml 의 date·time(KST) 예정 시각 전이어도 지금 게시 (기본: 예정 시각 전이면 거부)")
    parser.add_argument("--keep-media", action="store_true", help="게시 후 R2 에 올린 파일을 지우지 않음")
    parser.add_argument("--force-status", action="store_true",
                        help="post.yaml status 가 approved 가 아니어도 게시 (경고 출력). 검수 오류는 못 넘김")
    parser.add_argument("--reel", action="store_true", help="카드뉴스 대신 out/reel/reel.mp4 를 릴스로 게시")
    parser.add_argument("--account-ai-label-on", action="store_true",
                        help="(--reel 필수) 프로필 'AI 생성 프로필' 라벨을 켜 두었고, 게시 직후 앱 '수정'에서 "
                             "게시물 'AI 정보' 라벨을 켜겠다는 확인")
    parser.add_argument("--reels-tab-only", action="store_true", help="릴스를 피드에 공유하지 않음 (share_to_feed=false)")
    parser.add_argument("--paid-partnership", action="store_true",
                        help="광고·협찬·제휴 게시물: is_paid_partnership=true 로 게시 (없으면 이런 게시물은 거부)")
    parser.add_argument("--skip-render", action="store_true", help="이미 있는 out/ig/slides 의 4:5 PNG 를 그대로 사용")
    parser.add_argument("--no-ai-metadata", action="store_true", help="JPEG 에 AI 합성(IPTC) 메타데이터를 넣지 않음")
    parser.add_argument("--poll-interval", type=float, default=5.0, help="컨테이너 상태 확인 간격(초, 기본 5)")
    parser.add_argument("--max-wait", type=float, default=0,
                        help="컨테이너 처리 최대 대기(초). 기본: 이미지 300, 릴스 900")
    parser.add_argument("--refresh-token", action="store_true",
                        help="IG_ACCESS_TOKEN(60일) 갱신. 만료일과 지문(앞4…뒤4)만 출력")
    parser.add_argument("--token-out", help="(--refresh-token) 새 토큰을 저장할 파일 (기본: 저장소의 .env.ig_token.new, 권한 600)")
    parser.add_argument("--check-setup", action="store_true", help="환경 변수·SigV4 서명 자체 시험·API 연결 확인")


def run(args) -> int:
    if args.refresh_token:
        return _cmd_refresh(args)
    if args.check_setup:
        return _cmd_check_setup(args)
    if not args.post:
        print("게시할 게시물을 지정하세요: python doha.py ig-publish <게시물> [--dry-run | --mock]")
        return EXIT_REFUSED
    return _cmd_publish(args)


# ================================================================ Graph API

class GraphError(Exception):
    def __init__(self, message: str, *, http_status: int = 0, code: int = 0, subcode: int = 0,
                 kind: str = "other", outcome_unknown: bool = False):
        super().__init__(message)
        self.http_status, self.code, self.subcode = http_status, code, subcode
        self.kind, self.outcome_unknown = kind, outcome_unknown

    def explain(self) -> str:
        hint = HINTS.get(self.kind, "")
        codes = f" (code {self.code}" + (f"/{self.subcode}" if self.subcode else "") + ")" if self.code else ""
        return f"{self}{codes}" + (f"\n  → {hint}" if hint else "")


HINTS = {
    "token": "액세스 토큰이 만료됐거나 잘못됐어요 (장기 토큰은 60일). 아직 만료 전이면 "
             "`python doha.py ig-publish --refresh-token` 으로 갱신하고, 이미 만료됐으면 Meta 앱 대시보드에서 "
             "새로 발급해 IG_ACCESS_TOKEN 비밀값을 바꿔 주세요. 토큰은 채팅·문서에 붙여넣지 마세요.",
    "permission": "권한이 없어요. 토큰에 instagram_business_basic + instagram_business_content_publish 가 있는지, "
                  "계정이 프로페셔널(크리에이터·비즈니스)인지, IG_USER_ID 가 이 토큰의 계정인지 확인하세요.",
    "rate": "게시 한도(content_publishing_limit, 24시간 이동 창) 또는 호출 한도에 걸렸어요. "
            "바로 반복하지 말고 1시간 뒤 다시 실행하세요. 한도는 숫자를 외우지 말고 --check-setup 으로 조회하세요.",
    "fetch": "Meta 가 미디어 주소를 열지 못했어요 (9004/2207052). R2 공개 주소가 로그인 없이 200 · image/jpeg 로 "
             "열리는지, R2_PUBLIC_BASE_URL(내 도메인 권장, r2.dev 는 시험용)이 맞는지 확인하세요.",
    "aspect": "이미지 비율이 허용 범위(4:5 ~ 1.91:1) 밖이에요. 3:4(1080x1440)는 API 로 못 올려요. "
              "--skip-render 를 썼다면 빼고 다시 실행해 4:5 로 렌더링하세요.",
    "size": "파일이 너무 커요. 이미지는 8MB 이하 JPEG, 가로 320~1440px 이어야 해요.",
    "format": "형식이 맞지 않아요. 이미지는 일반 JPEG(MPO·JPS 불가), 릴스는 MP4(H.264·AAC)여야 해요.",
    "expired": "컨테이너가 만료됐어요(만든 뒤 오래 지남). 처음부터 다시 실행하세요.",
    "network": "네트워크 연결이 끊기거나 시간이 초과됐어요. 잠시 뒤 다시 실행하세요.",
    "param": "요청 값이 거부됐어요. 메시지를 확인하세요.",
}


def classify(http_status: int, code: int, subcode: int, message: str) -> str:
    m = message.lower()
    if code == 190 or subcode in (458, 459, 460, 463, 464, 467) or "access token" in m and "expired" in m:
        return "token"
    if code in (4, 17, 32, 613) or subcode == 2207042 or "publishing limit" in m or "request limit" in m:
        return "rate"
    if code == 9004 or subcode == 2207052 or "could not be fetched" in m or "only photo or video" in m:
        return "fetch"
    if code == 36003 or subcode == 2207009 or "aspect ratio" in m:
        return "aspect"
    if subcode == 2207004 or "too large" in m:
        return "size"
    if subcode in (2207005, 2207026) or "format" in m and "support" in m:
        return "format"
    if subcode == 2207008 or "expired" in m:
        return "expired"
    if code in (3, 10, 200) or 200 <= code < 300 or http_status == 403 or "permission" in m:
        return "permission"
    if code == 100:
        return "param"
    return "other"


class Graph:
    """graph.instagram.com 호출. 토큰은 요청에만 넣고, 오류 메시지·출력에는 남기지 않는다."""

    def __init__(self, token: str, base: str = "", version: str = "", timeout: float = 60):
        self.token = token
        self.base = (base or os.environ.get("IG_API_BASE", "").strip() or DEFAULT_BASE).rstrip("/")
        self.version = (version or os.environ.get("IG_API_VERSION", "")).strip().strip("/")
        self.timeout = timeout

    def _url(self, path: str, versioned: bool = True) -> str:
        path = path.lstrip("/")
        return f"{self.base}/{self.version}/{path}" if versioned and self.version else f"{self.base}/{path}"

    def _scrub(self, text: str) -> str:
        return text.replace(self.token, "***") if self.token else text

    def get(self, path: str, versioned: bool = True, timeout: float | None = None, **params) -> dict:
        return self.request("GET", path, params, versioned=versioned, timeout=timeout)

    def post(self, path: str, timeout: float | None = None, **params) -> dict:
        return self.request("POST", path, params, timeout=timeout)

    def request(self, method: str, path: str, params: dict | None = None, *, versioned: bool = True,
                timeout: float | None = None) -> dict:
        from doha.insights import _ssl_context

        params = {k: ("true" if v is True else "false" if v is False else str(v))
                  for k, v in (params or {}).items() if v is not None}
        body = urllib.parse.urlencode({**params, "access_token": self.token})
        url = self._url(path, versioned)
        if method == "GET":
            req = urllib.request.Request(f"{url}?{body}", method="GET")
        else:
            req = urllib.request.Request(url, data=body.encode("utf-8"), method=method,
                                         headers={"Content-Type": "application/x-www-form-urlencoded"})
        try:
            with urllib.request.urlopen(req, timeout=timeout or self.timeout, context=_ssl_context()) as resp:
                raw = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            raise self._http_error(e) from None
        except (OSError, ValueError) as e:  # URLError·시간 초과·연결 끊김(RemoteDisconnected) 포함
            reason = getattr(e, "reason", None) or e
            raise GraphError(self._scrub(f"연결 실패·시간 초과: {type(e).__name__} {reason}"), kind="network",
                             outcome_unknown=True) from None
        try:
            return json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError:
            raise GraphError("API 응답을 읽지 못했어요 (JSON 아님)", kind="other") from None

    def _http_error(self, e: urllib.error.HTTPError) -> GraphError:
        try:
            err = json.loads(e.read().decode("utf-8", "replace")).get("error") or {}
        except Exception:
            err = {}
        code = int(err.get("code") or 0)
        subcode = int(err.get("error_subcode") or 0)
        msg = str(err.get("error_user_msg") or err.get("message") or f"HTTP {e.code}")
        msg = self._scrub(msg)[:300]
        # 5xx·code 1/2(알 수 없는 오류·일시 장애)는 서버에서 처리가 끝났을 수 있다 → media_publish 면 게시 여부부터 확인
        return GraphError(f"Instagram API 오류: {msg}", http_status=e.code, code=code, subcode=subcode,
                          kind=classify(e.code, code, subcode, msg), outcome_unknown=e.code >= 500 or code in (1, 2))


def resolve_user_id(graph: Graph) -> str:
    uid = os.environ.get("IG_USER_ID", "").strip()
    if uid:
        return uid
    me = graph.get("me", fields="user_id,username")
    uid = str(me.get("user_id") or me.get("id") or "")
    if not uid:
        raise GraphError("IG 사용자 ID 를 알 수 없어요. IG_USER_ID 를 설정하세요.")
    return uid


# ================================================================ 미디어 준비

@dataclass
class Item:
    src: Path                 # 원본 PNG/MP4
    path: Path                # 올릴 파일 (JPEG/MP4)
    content_type: str
    alt: str = ""
    ai: bool = False
    size: tuple[int, int] = (0, 0)
    key: str = ""             # R2 키
    url: str = ""             # 공개 주소


class _IgPost(Post):
    """API 게시용 4:5 렌더는 out/ig/ 아래에 둔다 — 앱 업로드용 3:4(out/slides)를 덮어쓰지 않게."""

    @property
    def out_dir(self) -> Path:
        return self.dir / "out" / "ig"


def ig_dir(post: Post) -> Path:
    return post.dir / "out" / "ig"


def _insert_xmp(jpeg: bytes, xmp: bytes) -> bytes:
    """JPEG 의 SOI(·JFIF APP0) 바로 뒤에 XMP APP1 세그먼트를 넣는다."""
    if jpeg[:2] != b"\xff\xd8":
        raise ValueError("JPEG 가 아니에요")
    payload = XMP_HEADER + xmp
    segment = b"\xff\xe1" + struct.pack(">H", len(payload) + 2) + payload
    pos = 2
    if jpeg[2:4] == b"\xff\xe0":  # JFIF APP0 는 맨 앞에 두는 것이 규칙
        pos = 4 + struct.unpack(">H", jpeg[4:6])[0]
    return jpeg[:pos] + segment + jpeg[pos:]


def to_jpeg(src: Path, dst: Path, *, ai_tag: bool, check_ratio: bool = True) -> tuple[int, int]:
    """PNG → sRGB 기본(baseline) JPEG, 8MB 이하. 비율·폭이 API 규격 밖이면 ValueError."""
    from PIL import Image

    with Image.open(src) as im:
        im.load()
        icc = im.info.get("icc_profile")
        if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
            rgba = im.convert("RGBA")
            bg = Image.new("RGB", rgba.size, (255, 255, 255))
            bg.paste(rgba, mask=rgba.getchannel("A"))
            rgb = bg
        else:
            rgb = im.convert("RGB")
    srgb_bytes = None
    try:
        from PIL import ImageCms

        srgb = ImageCms.createProfile("sRGB")
        if icc:  # 원본에 다른 색 공간이 박혀 있으면 sRGB 로 변환
            rgb = ImageCms.profileToProfile(rgb, ImageCms.ImageCmsProfile(BytesIO(icc)), srgb, outputMode="RGB")
        srgb_bytes = ImageCms.ImageCmsProfile(srgb).tobytes()
    except Exception:  # littlecms 없는 Pillow: 프로필 없는 JPEG 은 sRGB 로 간주된다
        pass
    if rgb.width > WIDTH_RANGE[1]:
        rgb = rgb.resize((WIDTH_RANGE[1], round(rgb.height * WIDTH_RANGE[1] / rgb.width)), Image.LANCZOS)
    w, h = rgb.size
    if check_ratio:
        ratio = w / h
        if not (RATIO_RANGE[0] - 0.001 <= ratio <= RATIO_RANGE[1] + 0.001):
            raise ValueError(f"{src.name}: {w}x{h} (비율 {ratio:.3f}) 은 API 허용 범위 4:5~1.91:1 밖이에요")
        if w < WIDTH_RANGE[0]:
            raise ValueError(f"{src.name}: 가로 {w}px 은 너무 작아요 (최소 {WIDTH_RANGE[0]}px)")
    data = b""
    for quality in (90, 85, 80, 72, 64, 55):
        buf = BytesIO()
        opts = {"quality": quality, "optimize": True, "progressive": False, "subsampling": 0 if quality >= 85 else 2}
        if srgb_bytes:
            opts["icc_profile"] = srgb_bytes
        rgb.save(buf, "JPEG", **opts)
        data = buf.getvalue()
        if ai_tag:
            data = _insert_xmp(data, XMP_PACKET)
        if len(data) <= MAX_JPEG_BYTES:
            break
    if len(data) > MAX_JPEG_BYTES:
        raise ValueError(f"{src.name}: JPEG 가 8MB 를 넘어요 ({len(data) / 1e6:.1f}MB)")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(data)
    return w, h


def _slide_has_photo(slide: dict) -> bool:
    if slide.get("image"):
        return True
    return any(isinstance(slide.get(s), dict) and slide[s].get("image") for s in ("left", "right"))


def _slide_alt(slide: dict, index: int, post_alt: str) -> str:
    """장마다 대체 텍스트: 1번은 post.yaml alt_text, 나머지는 슬라이드 글자로 만든다 (장 안의 글이 곧 내용)."""
    if slide.get("alt"):
        return str(slide["alt"])[:1000]
    if index == 1 and post_alt:
        return post_alt[:1000]
    parts: list[str] = []
    for k in ("label", "number", "title", "subtitle", "body", "tip", "verdict", "note"):
        if slide.get(k):
            parts.append(str(slide[k]))
    for k in ("items", "checks", "bullets"):
        if isinstance(slide.get(k), list):
            parts.append(", ".join(str(x) for x in slide[k] if x))
    for side in ("left", "right"):
        if isinstance(slide.get(side), dict):
            parts.append(" ".join(str(slide[side].get(k) or "") for k in ("label", "caption")).strip())
    text = " / ".join(" ".join(p.split()) for p in parts if p.strip())
    if _slide_has_photo(slide):
        text = (text + " — " if text else "") + "AI로 생성한 가상인물 도하의 출근룩 이미지"
    return text[:1000]


def prepare_carousel(post: Post, args) -> list[Item]:
    slides = post.data.get("slides") or []
    if not slides:
        raise SystemExit("카드뉴스 슬라이드가 없어요 (릴스 전용이면 --reel).")
    png_dir = ig_dir(post) / "slides"
    if args.skip_render:
        pngs = sorted(png_dir.glob("[0-9][0-9].png"))
        if len(pngs) != len(slides):
            raise SystemExit(f"--skip-render: {png_dir} 에 PNG {len(pngs)}장 / 슬라이드 {len(slides)}장 — 렌더링부터 다시 하세요.")
    else:
        from doha.render import render_post

        print(f"· 4:5(1080x1350) 렌더링 → {png_dir.relative_to(post.dir)}/", flush=True)
        pngs = render_post(_IgPost(dir=post.dir, data=post.data), "4x5")
    if len(pngs) > MAX_ITEMS:
        print(f"주의: 슬라이드 {len(pngs)}장 중 앞 {MAX_ITEMS}장만 올려요 (API 캐러셀 최대 {MAX_ITEMS}장). "
              f"빠지는 장: {', '.join(p.stem for p in pngs[MAX_ITEMS:])} — 앱 업로드는 20장까지 돼요.", file=sys.stderr)
        pngs = pngs[:MAX_ITEMS]
    post_alt = " ".join(str(post.data.get("alt_text") or "").split())
    jpg_dir = ig_dir(post) / "jpeg"
    for old in jpg_dir.glob("*.jpg"):
        old.unlink()
    items = []
    for png in pngs:
        idx = int(png.stem)
        slide = slides[idx - 1] if idx - 1 < len(slides) else {}
        ai = _slide_has_photo(slide) and not args.no_ai_metadata
        dst = jpg_dir / f"{idx:02d}.jpg"
        try:
            size = to_jpeg(png, dst, ai_tag=ai)
        except ValueError as e:
            raise SystemExit(f"이미지 규격 오류: {e}") from None
        items.append(Item(src=png, path=dst, content_type="image/jpeg", alt=_slide_alt(slide, idx, post_alt),
                          ai=ai, size=size))
    return items


def prepare_reel(post: Post, args) -> tuple[Item, Item]:
    reel_dir = post.out_dir / "reel"
    mp4, cover = reel_dir / "reel.mp4", reel_dir / "cover.png"
    if not mp4.exists() or not cover.exists():
        raise SystemExit(f"릴스 파일이 없어요: {mp4.relative_to(post.dir)} / cover.png — 먼저 python doha.py reel {post.id}")
    size_mb = mp4.stat().st_size / 1e6
    if size_mb > 300:
        raise SystemExit(f"릴스 파일이 {size_mb:.0f}MB 예요. 300MB 이하로 줄여 주세요.")
    cover_jpg = ig_dir(post) / "jpeg" / "reel-cover.jpg"
    try:
        size = to_jpeg(cover, cover_jpg, ai_tag=not args.no_ai_metadata, check_ratio=False)
    except ValueError as e:
        raise SystemExit(f"릴스 커버 오류: {e}") from None
    video = Item(src=mp4, path=mp4, content_type="video/mp4")
    return video, Item(src=cover, path=cover_jpg, content_type="image/jpeg", ai=not args.no_ai_metadata, size=size)


# ================================================================ 게시 전 관문

def _sponsored(data: dict) -> bool:
    d = data.get("disclosure") or {}
    return any(d.get(k) is True for k in ("paid", "gifted", "affiliate"))


def scheduled_at(data: dict) -> datetime | None:
    """post.yaml 의 date + time 을 KST 시각으로. date 가 없거나 형식이 틀리면 None (time 이 비면 그날 00:00)."""
    d = str(data.get("date") or "").strip()
    t = data.get("time")
    if isinstance(t, int):  # YAML 1.1 은 따옴표 없는 7:40 을 60진수 정수(460)로 읽는다
        t = f"{t // 60:02d}:{t % 60:02d}"
    t = str(t or "").strip() or "00:00"
    try:
        return datetime.strptime(f"{d} {t}", "%Y-%m-%d %H:%M").replace(tzinfo=KST)
    except ValueError:
        return None


def target_field(data: dict, target: str) -> str:
    """이번 게시가 채울 posted 필드. 릴스 전용 게시물의 릴스는 url, both 의 릴스는 reel_url."""
    return "reel_url" if target == "reel" and (data.get("format") or "both") == "both" else "url"


def gates(post: Post, target: str, args, config: dict, persona: dict, live: bool) -> list[str]:
    """게시를 막는 이유 목록 (빈 목록이면 통과). 검수 보고서도 출력한다."""
    from doha.check import check_post, counts, format_report, post_format

    d = post.data
    problems: list[str] = []
    has_c, has_r = post_format(d)
    if target == "carousel" and not has_c:
        problems.append(f"format: {d.get('format')} — 카드뉴스가 없어요. 릴스는 --reel 로 게시하세요.")
    if target == "reel" and not has_r:
        problems.append(f"format: {d.get('format')} — 릴스가 없는 게시물이에요.")
    fieldname = target_field(d, target)
    posted = d.get("posted") or {}
    if str(posted.get(fieldname) or "").strip():
        problems.append(f"이미 게시됐어요: posted.{fieldname} = {posted.get(fieldname)} (중복 게시 방지)")
    status = d.get("status")
    status_ok = status == "approved" or (status == "posted" and (d.get("format") == "both"))
    if not status_ok:
        if args.force_status:
            print(f"경고: status 가 '{status}' 인데 --force-status 로 진행해요. 사람 승인 없이 공개됩니다.", file=sys.stderr)
        else:
            problems.append(f"status 가 '{status}' 예요. 휴대폰에서 미리보기를 확인하고 post.yaml 의 status 를 approved 로 "
                            "바꾼 뒤 실행하세요 (하루 1번 승인).")
    issues = check_post(post, persona, config)
    print(format_report(post.id, issues))
    errors, _ = counts(issues)
    if errors:
        problems.append(f"검수 오류 {errors}건 — python doha.py check {post.id} 로 고친 뒤 다시 실행하세요.")
    codes = {i.code for i in issues}
    if "image.file_missing" in codes:
        problems.append("사진 파일이 없는 장이 있어요 — 자리표시 이미지를 공개 계정에 올리지 않아요.")
    if "image.rejected" in codes:
        problems.append("반려(rejected)된 사진을 쓰고 있어요.")
    if _sponsored(d) and not args.paid_partnership:
        problems.append("광고·협찬·제휴 게시물이에요. API 의 유료 파트너십 라벨(is_paid_partnership)은 Instagram 로그인 "
                        "방식에서 동작 확인 전[미확인]이라 기본은 앱에서 올려요 (A안). 시험하려면 --paid-partnership.")
    if target == "reel" and live and not args.account_ai_label_on:
        problems.append("실사형 AI 영상은 게시물마다 'AI 정보' 라벨이 의무인데 API 로는 켤 수 없어요 [미확인]. 릴스는 앱에서 "
                        "올리는 것을 권해요 (프로필 'AI 생성 프로필' 라벨은 게시물 라벨을 대신하지 못해요). 그래도 API 로 "
                        "올리려면 프로필 라벨을 켜 두고 게시 직후 앱 '수정'에서 'AI 정보'를 켜겠다는 뜻으로 "
                        "--account-ai-label-on 을 붙이세요.")
    return problems


# ================================================================ 상태 파일·잠금 (중복 게시 방지)

class State:
    """out/ig/state-<대상>.json — 실행이 중간에 끊겨도 같은 게시물을 두 번 올리지 않게."""

    def __init__(self, path: Path | None):
        self.path = path
        self.data: dict = {}
        if path and path.exists():
            try:
                self.data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                self.data = {}

    def save(self, **kw) -> None:
        self.data.update(kw)
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, self.path)

    def clear(self) -> None:
        self.data = {}
        if self.path:
            self.path.unlink(missing_ok=True)


class Lock:
    def __init__(self, path: Path | None):
        self.path = path

    def __enter__(self):
        if not self.path:
            return self
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(2):
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.write(fd, f"{os.getpid()} {datetime.now(KST).isoformat()}".encode())
                os.close(fd)
                return self
            except FileExistsError:
                age = datetime.now().timestamp() - self.path.stat().st_mtime
                if age > LOCK_STALE.total_seconds():
                    self.path.unlink(missing_ok=True)
                    continue
                raise SystemExit(f"다른 ig-publish 가 같은 게시물을 게시 중이에요 ({self.path.name}). "
                                 "1시간이 지나도 남아 있으면 그 파일을 지우세요.") from None
        raise SystemExit("잠금 파일을 만들지 못했어요.")

    def __exit__(self, *exc):
        if self.path:
            self.path.unlink(missing_ok=True)


# ================================================================ post.yaml 기록 (주석 보존)

def _q(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=False)  # JSON 문자열 = YAML 큰따옴표 문자열


def update_post_yaml(path: Path, posted: dict[str, str], status: str | None = None) -> None:
    """post.yaml 의 posted.<키> 와 최상위 status 만 줄 단위로 고친다 (Post.save 는 주석을 지워서 쓰지 않음)."""
    import yaml

    original = path.read_bytes().decode("utf-8")  # read_text 는 \r\n 을 \n 으로 바꿔 버린다
    nl = "\r\n" if "\r\n" in original else "\n"
    lines = original.splitlines(keepends=True)
    if lines and not lines[-1].endswith(("\n", "\r")):
        lines[-1] += nl
    if status:
        for i, ln in enumerate(lines):
            m = re.match(r"^status:[ \t]*([^#\r\n]*?)([ \t]+#[^\r\n]*)?(\r?\n)$", ln)
            if m:
                lines[i] = f"status: {status}{m.group(2) or ''}{m.group(3)}"
                break
        else:
            lines.append(f"status: {status}{nl}")
    start = next((i for i, ln in enumerate(lines) if re.match(r"^posted:", ln)), None)
    rest = lines[start][len("posted:"):].strip() if start is not None else ""
    if start is None or (rest and not rest.startswith("#")):
        # 블록이 없거나 'posted: {…}' · 'posted: null' 한 줄 → 기존 값과 합쳐 블록으로 다시 쓴다
        old = {}
        if start is not None:
            old = (yaml.safe_load(original) or {}).get("posted") or {}
            del lines[start]
        else:
            start = len(lines)
            if lines and lines[-1].strip():
                lines.append(nl)
                start += 1
        merged = {**{k: str(v) for k, v in old.items() if v is not None}, **posted}
        lines[start:start] = [f"posted:{nl}"] + [f"  {k}: {_q(v)}{nl}" for k, v in merged.items()]
    else:
        end = start + 1
        while end < len(lines) and (not lines[end].strip() or lines[end][:1] in (" ", "\t")):
            end += 1
        key_lines = [j for j in range(start + 1, end) if re.match(r"^[ \t]+[\w-]+:", lines[j])]
        indent = re.match(r"^([ \t]+)", lines[key_lines[0]]).group(1) if key_lines else "  "
        last = key_lines[-1] if key_lines else start
        for key, val in posted.items():
            pat = re.compile(rf"^{re.escape(indent)}{re.escape(key)}:[ \t]*(.*?)([ \t]+#[^\r\n]*)?(\r?\n)$")
            for j in range(start + 1, end):
                m = pat.match(lines[j])
                if m:
                    lines[j] = f"{indent}{key}: {_q(val)}{m.group(2) or ''}{m.group(3)}"
                    break
            else:
                last += 1
                end += 1
                lines.insert(last, f"{indent}{key}: {_q(val)}{nl}")
    new = "".join(lines)
    data = yaml.safe_load(new) or {}
    got = data.get("posted") or {}
    if any(str(got.get(k)) != v for k, v in posted.items()) or (status and data.get("status") != status):
        raise SystemExit("post.yaml 을 고치다 형식이 어긋났어요 — 파일은 그대로 두었어요. posted 칸을 직접 채워 주세요: "
                         + ", ".join(f"{k}={v}" for k, v in posted.items()))
    tmp = path.with_name(".post.yaml.tmp")
    tmp.write_bytes(new.encode("utf-8"))
    os.replace(tmp, path)


# ================================================================ 게시

def _norm_caption(text: str) -> str:
    return " ".join(str(text or "").split())


def _same_kind(m: dict, target: str) -> bool:
    """릴스·카드뉴스가 같은 캡션을 쓰는 format: both 에서 서로를 '이미 게시됨'으로 착각하지 않게."""
    mtype, product = m.get("media_type"), m.get("media_product_type")
    if not mtype and not product:
        return True
    is_reel = product == "REELS" or mtype == "VIDEO"
    return is_reel if target == "reel" else not is_reel


def caption_key(text: str) -> str:
    return hashlib.sha256(_norm_caption(text).encode("utf-8")).hexdigest()


def find_existing(graph: Graph, uid: str, caption: str, target: str, since: datetime | None = None,
                  exclude: set[str] | None = None, also_keys: set[str] | None = None) -> dict | None:
    """최근 게시물 중 같은 종류·같은 캡션인 것 (앱으로 이미 올렸거나, 지난 실행의 응답이 끊긴 경우).

    exclude: 건너뛸 숏코드 (format: both 에서 먼저 올린 다른 쪽). also_keys: 지난 실행 캡션의 caption_key
    (응답이 끊긴 뒤 캡션을 고쳐 다시 실행해도 이미 올라간 글을 찾게).
    """
    listing = graph.get(f"{uid}/media", fields="id,caption,permalink,timestamp,media_type,media_product_type",
                        limit="10")
    want = {caption_key(caption)} | set(also_keys or ())
    for m in listing.get("data") or []:
        if caption_key(m.get("caption")) not in want or not _same_kind(m, target):
            continue
        if exclude and shortcode(m.get("permalink")) in exclude:
            continue
        if since:
            try:
                ts = datetime.strptime(m.get("timestamp", ""), "%Y-%m-%dT%H:%M:%S%z")
                if ts < since - timedelta(minutes=10):
                    continue
            except ValueError:
                pass
        return m
    return None


def wait_finished(graph: Graph, container_id: str, interval: float, max_wait: float, label: str) -> None:
    deadline = time.monotonic() + max_wait
    last = ""
    while True:
        info = graph.get(container_id, fields="status_code,status")
        code = str(info.get("status_code") or "")
        if code in ("FINISHED", "PUBLISHED"):
            return
        if code in ("ERROR", "EXPIRED"):
            detail = str(info.get("status") or "")
            sub = re.search(r"(\d{7})", detail)
            subcode = int(sub.group(1)) if sub else 0
            kind = "expired" if code == "EXPIRED" else classify(0, 0, subcode, detail)
            raise GraphError(f"{label} 처리 실패: {code} {detail}".strip(), subcode=subcode, kind=kind)
        if code != last:
            print(f"  · {label}: {code or '상태 없음'} …", flush=True)
            last = code
        if time.monotonic() >= deadline:
            raise GraphError(f"{label} 처리가 {max_wait:.0f}초 안에 끝나지 않았어요 (마지막 상태 {code}).", kind="network")
        time.sleep(interval)


def check_quota(graph: Graph, uid: str) -> None:
    try:
        info = graph.get(f"{uid}/content_publishing_limit", fields="quota_usage,config")
    except GraphError as e:
        if e.kind in ("token", "permission"):
            raise
        print(f"  · 게시 한도 조회 실패 — 계속 진행 ({e})", file=sys.stderr)
        return
    row = (info.get("data") or [{}])[0]
    used = row.get("quota_usage")
    total = (row.get("config") or {}).get("quota_total")
    print(f"  · 게시 한도: 24시간 {used}/{total}")
    if isinstance(used, int) and isinstance(total, int) and used >= total:
        raise GraphError("24시간 게시 한도를 다 썼어요.", kind="rate")


@dataclass
class Session:
    mode: str                         # live | mock
    graph: Graph
    r2cfg: object
    mock: "MockServer | None" = None
    uploaded: list[str] = field(default_factory=list)


def _upload(sess: Session, items: list[Item], prefix: str, state: State) -> None:
    from doha.r2 import check_public_url, put_object

    for it in items:
        it.key = f"{prefix}/{it.path.name}"
        print(f"  · R2 업로드 {it.path.name} ({it.path.stat().st_size / 1e6:.2f}MB)", flush=True)
        it.url = put_object(it.path, it.key, it.content_type, cfg=sess.r2cfg)
        sess.uploaded.append(it.key)
        state.save(r2_keys=list(sess.uploaded))
        problem = check_public_url(it.url, it.content_type)
        if problem:
            raise GraphError(f"공개 주소 점검 실패 ({it.path.name}): {problem}", kind="fetch")


def _cleanup(sess: Session, keep: bool, state: State) -> None:
    keys = list(dict.fromkeys(sess.uploaded + list(state.data.get("r2_keys") or [])))
    if not keys:
        return
    if keep:
        print(f"  · R2 파일 {len(keys)}개를 남겨 둡니다 (--keep-media).")
        return
    from doha.r2 import R2Error, delete_object

    failed = []
    for key in keys:
        try:
            delete_object(key, cfg=sess.r2cfg)
        except R2Error:
            failed.append(key)
    if failed:
        print(f"주의: R2 파일 {len(failed)}개를 지우지 못했어요 (버킷에서 직접 삭제): {', '.join(failed[:3])}…", file=sys.stderr)
    else:
        print(f"  · R2 임시 파일 {len(keys)}개 삭제")
    sess.uploaded.clear()
    state.save(r2_keys=[])


def _create_items(sess: Session, uid: str, items: list[Item], caption: str, extra: dict, state: State) -> str:
    """컨테이너를 만들고 게시할 creation_id 를 돌려준다."""
    g = sess.graph
    alt_ok = True

    def image_container(it: Item, **params) -> str:
        nonlocal alt_ok
        if alt_ok and it.alt:
            try:
                return g.post(f"{uid}/media", image_url=it.url, alt_text=it.alt, **params)["id"]
            except GraphError as e:
                if not (e.kind == "param" and "alt" in str(e).lower()):
                    raise
                alt_ok = False
                print("  · alt_text 를 API 가 받지 않아 빼고 진행해요 — 앱의 고급 설정에서 넣어 주세요.", file=sys.stderr)
        return g.post(f"{uid}/media", image_url=it.url, **params)["id"]

    if len(items) == 1:
        cid = image_container(items[0], caption=caption, **extra)
        state.save(creation_id=cid)
        return cid
    children = []
    for i, it in enumerate(items, 1):
        children.append(image_container(it, is_carousel_item=True))
        print(f"  · 컨테이너 {i}/{len(items)}", flush=True)
    state.save(children=children)
    cid = g.post(f"{uid}/media", media_type="CAROUSEL", children=",".join(children), caption=caption, **extra)["id"]
    state.save(creation_id=cid)
    return cid


def _finish(sess: Session, post: Post, target: str, media_id: str, state: State) -> str:
    info = sess.graph.get(media_id, fields="permalink,timestamp")
    permalink = str(info.get("permalink") or "")
    try:
        ts = datetime.strptime(info.get("timestamp", ""), "%Y-%m-%dT%H:%M:%S%z").astimezone(KST)
    except ValueError:
        ts = datetime.now(KST)
    posted_at = ts.isoformat(timespec="seconds")
    state.save(media_id=media_id, permalink=permalink)
    fieldname = target_field(post.data, target)
    if sess.mode == "mock":
        print(f"  · (모의) post.yaml 에 기록할 값: posted.{fieldname}={permalink}, posted_at={posted_at}, status=posted")
    else:
        update_post_yaml(post.dir / "post.yaml", {fieldname: permalink, "posted_at": posted_at}, status="posted")
        print(f"  · post.yaml 기록: posted.{fieldname}, posted_at, status: posted")
    return permalink


def publish(sess: Session, post: Post, target: str, items: list[Item], caption: str, args) -> int:
    live = sess.mode == "live"
    state = State(ig_dir(post) / f"state-{target}.json" if live else None)
    g = sess.graph
    uid = resolve_user_id(g) if live else sess.mock.user_id
    since = None

    # 1) 지난 실행이 게시 직후 끊겼는지 먼저 정리
    if state.data.get("media_id"):
        print("이전 실행에서 게시는 끝났지만 기록이 남지 않았어요 → 기록만 마무리합니다.")
        url = _finish(sess, post, target, state.data["media_id"], state)
        _cleanup(sess, args.keep_media, state)
        state.clear()
        print(f"✓ 게시 확인: {url}")
        return EXIT_OK
    # format: both 에서 먼저 올린 다른 쪽(카드뉴스↔릴스)만 비교에서 뺀다. 이번 대상의 기록은 빼지 않는다
    other = {"url": "reel_url", "reel_url": "url"}[target_field(post.data, target)]
    recorded = {shortcode((post.data.get("posted") or {}).get(other))} - {None}
    prev_keys: set[str] = set()
    if state.data.get("publish_requested_at"):
        since = datetime.fromisoformat(state.data["publish_requested_at"])
        prev_keys = {state.data["caption_sha256"]} if state.data.get("caption_sha256") else set()
        print("이전 실행의 게시 요청 결과를 모릅니다 → 최근 게시물에서 먼저 확인해요.")
    # 2) 같은 캡션이 이미 올라가 있으면 다시 올리지 않는다 (앱으로 올렸거나 응답이 끊긴 경우)
    try:
        found = find_existing(g, uid, caption, target, since, recorded, prev_keys)
    except GraphError as e:
        if since or e.kind in ("token", "permission"):
            raise
        print(f"  · 최근 게시물 확인 실패 — 계속 진행 ({e})", file=sys.stderr)
        found = None
    if found:
        print(f"같은 캡션의 게시물이 이미 있어요: {found.get('permalink')} → 다시 올리지 않고 기록만 해요.")
        _finish(sess, post, target, str(found["id"]), state)
        _cleanup(sess, args.keep_media, state)
        state.clear()
        return EXIT_OK
    if since:
        print("  · 최근 게시물에 없어요 → 게시되지 않은 것으로 보고 처음부터 다시 진행합니다.")
    _cleanup(sess, False, state)  # 실패한 지난 실행이 남긴 R2 파일
    state.clear()

    run_id = secrets.token_hex(6)
    state.save(post_id=post.id, target=target, run=run_id, started_at=datetime.now(KST).isoformat(timespec="seconds"),
               caption_sha256=caption_key(caption))
    prefix = f"media/{post.id}/{run_id}"   # 게시 전 시안이 추측 가능한 주소에 열리지 않게 무작위 폴더
    extra = {"is_paid_partnership": True} if args.paid_partnership and _sponsored(post.data) else {}
    interval = max(args.poll_interval, 1.0) if live else min(args.poll_interval, 0.2)
    published = False
    try:
        if target == "reel":
            video, cover = items
            _upload(sess, [video, cover], prefix, state)
            cid = g.post(f"{uid}/media", media_type="REELS", video_url=video.url, cover_url=cover.url,
                         caption=caption, share_to_feed=not args.reels_tab_only, **extra)["id"]
            state.save(creation_id=cid)
            wait_finished(g, cid, interval, args.max_wait or 900, "릴스 처리")
        else:
            _upload(sess, items, prefix, state)
            cid = _create_items(sess, uid, items, caption, extra, state)
            wait_finished(g, cid, interval, args.max_wait or 300, "컨테이너")
        check_quota(g, uid)
        state.save(publish_requested_at=datetime.now(KST).isoformat(timespec="seconds"))
        print("  · 게시(media_publish) 요청", flush=True)
        try:
            media_id = str(g.post(f"{uid}/media_publish", creation_id=cid, timeout=120)["id"])
        except GraphError as e:
            if e.outcome_unknown:
                print(f"게시 요청의 결과를 알 수 없어요 (응답 끊김·서버 오류: {e}) — 올라갔을 수 있어요. "
                      "30초 뒤 최근 게시물을 확인합니다.", file=sys.stderr)
                time.sleep(30 if live else 0)
                found = find_existing(g, uid, caption, target,
                                      datetime.fromisoformat(state.data["publish_requested_at"]), recorded)
                if not found:
                    raise GraphError("게시 여부를 확인하지 못했어요. 앱에서 프로필을 확인한 뒤 같은 명령을 다시 실행하면 "
                                     "최근 게시물부터 확인하고 이어서 처리해요 (중복 게시 안 함).", kind="network") from None
                media_id = str(found["id"])
            else:
                state.save(publish_requested_at="")
                raise
        published = True
        state.save(media_id=media_id)
        url = _finish(sess, post, target, media_id, state)
    finally:
        if not published:
            # 컨테이너 처리 전에 실패했어도 R2 에 남은 시안은 지운다 (게시 여부를 모르면 남겨 둔다)
            if not state.data.get("publish_requested_at"):
                _cleanup(sess, args.keep_media, state)
    _cleanup(sess, args.keep_media, state)
    state.clear()
    if not live:
        print(f"\n✓ (모의) 리허설 완료: {url} — 실제 Instagram 에는 아무것도 올라가지 않았어요.")
        return EXIT_OK
    print(f"\n✓ 게시 완료: {url}")
    _after_reminders(post, target, args)
    return EXIT_OK


def _after_reminders(post: Post, target: str, args) -> None:
    print("\n게시 후 휴대폰에서 할 일 (1분):")
    if target == "reel":
        print("  1. 지금 바로 릴스 → ⋯ → 수정: 'AI 정보' 라벨 켜기 — 실사형 AI 영상은 의무예요. 토글이 없으면 릴스를 "
              "보관(숨김)하고 앱에서 라벨을 켜 다시 올리세요")
    else:
        print("  1. 게시물 → ⋯ → 수정: 'AI 정보' 라벨을 켤 수 있으면 켜기 — API 로는 못 켜요 [미확인] "
              "(JPEG 에 AI 메타데이터를 넣어 자동 라벨을 시도했지만 보장되지 않아요)")
    print("  2. 프로필의 'AI 생성 프로필' 라벨이 켜져 있는지 확인 (없으면 비팔로워 추천에서 빠질 수 있음)")
    if _sponsored(post.data):
        print("  3. '유료 파트너십' 라벨이 실제로 붙었는지 확인 — 안 붙었으면 앱에서 직접 추가")
    print("  · 24시간 뒤: python doha.py insights")


# ================================================================ 명령: 게시

def _cmd_publish(args) -> int:
    from doha.preview import build_caption, normalize_hashtags

    target = "reel" if args.reel else "carousel"
    post = resolve_post(args.post)
    if skip_if_legacy(post):
        return EXIT_OK
    config = load_config()
    persona = load_persona(config)
    mode = "dry-run" if args.dry_run else "mock" if args.mock else "live"
    label = {"dry-run": "점검만 (업로드·게시 안 함)", "mock": "모의 서버 리허설", "live": "실제 게시"}[mode]
    print(f"ig-publish: {post.id} · {'릴스' if target == 'reel' else '카드뉴스'} · {label}\n")

    # dry-run 도 실제 게시와 같은 관문으로 본다 (모의 리허설만 릴스 AI 라벨 확인을 건너뜀)
    problems = gates(post, target, args, config, persona, live=mode != "mock")
    when = scheduled_at(post.data)
    if when and datetime.now(KST) < when:
        if mode == "live" and not args.now:
            problems.append(f"예정 시각 전이에요 ({when:%Y-%m-%d %H:%M} KST, post.yaml date·time). 그 뒤에 실행하거나, "
                            "지금 올리려면 --now 를 붙이세요.")
        elif mode != "live":
            print(f"· 예정 시각 {when:%Y-%m-%d %H:%M} KST — 실제 게시는 그 뒤에 실행하세요 (지금 올리려면 --now).")
    if problems and mode != "dry-run":
        print("\n게시하지 않아요:")
        for p in problems:
            print(f"  ✗ {p}")
        return EXIT_REFUSED

    caption = build_caption(post, persona, config)
    tags = len(normalize_hashtags(re.findall(r"#(\w+)", caption)))
    if len(caption) > CAPTION_LIMIT or tags > MAX_HASHTAGS_API:
        print(f"캡션이 API 한도를 넘어요 ({len(caption)}자 / 해시태그 {tags}개; 최대 {CAPTION_LIMIT}자 · {MAX_HASHTAGS_API}개).")
        return EXIT_REFUSED
    items = list(prepare_reel(post, args)) if target == "reel" else prepare_carousel(post, args)

    print(f"\n올릴 파일 ({len(items)}개):")
    for it in items:
        dims = f"{it.size[0]}x{it.size[1]} " if it.size[0] else ""
        tag = " · AI 메타데이터" if it.ai else ""
        print(f"  - {it.path.relative_to(post.dir)}  {dims}{it.path.stat().st_size / 1e6:.2f}MB{tag}")
    first = caption.split("\n", 1)[0]
    print(f"캡션 {len(caption)}자 · 첫 줄: {first[:80]}")
    if mode == "dry-run":
        if problems:
            print("\n실제 게시라면 거부될 이유:")
            for p in problems:
                print(f"  ✗ {p}")
            return EXIT_REFUSED
        print("\n점검 통과. 실제 게시: python doha.py ig-publish " + post.id + (" --reel --account-ai-label-on" if args.reel else ""))
        return EXIT_OK

    if target == "reel":
        print("\n" + "!" * 64)
        print("!! 실사형 AI 영상은 'AI 정보' 라벨 공개가 의무예요 (research/ig-platform.md §3-1).")
        print("!! API 로는 게시물 AI 라벨을 켤 수 없어요 [미확인]. 게시 직후 앱 '수정'에서 'AI 정보'를 켜세요.")
        print("!! 수정 화면에 그 토글이 없으면 다음 릴스부터는 앱에서 올리세요 (업로드 화면에서 AI 라벨 토글).")
        print("!" * 64 + "\n")

    from doha.r2 import R2Config, R2Error

    mock = None
    try:
        if mode == "mock":
            mock = MockServer().start()
            sess = Session("mock", Graph(mock.token, base=mock.graph_base, version="v24.0"), mock.r2_config(), mock)
        else:
            token = os.environ.get("IG_ACCESS_TOKEN", "").strip()
            if not token:
                print("IG_ACCESS_TOKEN 이 없어요. .env(또는 서버 비밀값)에 넣어 주세요 — 발급: docs/07-automation.md")
                return EXIT_ERROR
            sess = Session("live", Graph(token), R2Config.from_env())
        with Lock(ig_dir(post) / f".lock-{target}" if mode == "live" else None):
            return publish(sess, post, target, items, caption, args)
    except GraphError as e:
        print(f"\n✗ {e.explain()}")
        return EXIT_ERROR
    except R2Error as e:
        print(f"\n✗ {e}")
        return EXIT_ERROR
    finally:
        if mock:
            mock.stop()


# ================================================================ 명령: 토큰 갱신·설정 점검

def fingerprint(token: str) -> str:
    return f"{token[:4]}…{token[-4:]}" if len(token) >= 12 else "(짧은 값)"


def _cmd_refresh(args) -> int:
    mock = MockServer().start() if args.mock else None
    try:
        token = mock.token if mock else os.environ.get("IG_ACCESS_TOKEN", "").strip()
        if not token:
            print("IG_ACCESS_TOKEN 이 없어요. 먼저 Meta 앱 대시보드에서 장기 토큰을 발급해 비밀값에 넣어 주세요.")
            return EXIT_ERROR
        graph = Graph(token, base=mock.graph_base if mock else "")
        try:
            # 갱신 엔드포인트는 버전 없이 호출한다 (공식 문서 예시)
            resp = graph.get("refresh_access_token", versioned=False, grant_type="ig_refresh_token")
        except GraphError as e:
            print(f"✗ 토큰 갱신 실패: {e.explain()}")
            print("  갱신 조건: 발급 후 24시간 경과 · 아직 만료 전 · instagram_business_basic 권한. "
                  "이미 만료됐으면 앱 대시보드에서 새로 발급해야 해요.")
            return EXIT_ERROR
        new = str(resp.get("access_token") or "")
        seconds = int(resp.get("expires_in") or 0)
        expires = datetime.now(KST) + timedelta(seconds=seconds)
        print(f"✓ 갱신 완료: 만료까지 {seconds / 86400:.0f}일 (약 {expires:%Y-%m-%d} KST)")
        if seconds and seconds < 14 * 86400:
            print("주의: 만료가 14일 안이에요. 비밀값이 제대로 바뀌었는지 확인하세요.")
        if not new:
            print("응답에 토큰이 없어요 — 기존 값을 그대로 쓰세요.")
            return EXIT_ERROR
        if new == token:
            print(f"토큰 값은 그대로예요 (지문 {fingerprint(token)}). 비밀값을 바꿀 필요가 없어요.")
            return EXIT_OK
        out = Path(args.token_out) if args.token_out else ROOT / ".env.ig_token.new"
        if mock:
            print(f"(모의) 새 토큰 지문 {fingerprint(new)} — 파일은 쓰지 않아요.")
            return EXIT_OK
        fd = os.open(out, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(new + "\n")
        os.chmod(out, 0o600)
        print(f"토큰 값이 바뀌었어요: 이전 {fingerprint(token)} → 새 {fingerprint(new)}")
        print(f"  새 값을 {out} 에 저장했어요 (권한 600, git 제외 파일).")
        print("  1) 이 값으로 IG_ACCESS_TOKEN 비밀값(.env 또는 서버 비밀 저장소)을 바꾸고")
        print("  2) 파일을 지우세요. 값은 채팅·문서·로그에 붙여넣지 마세요.")
        print("  (이전 토큰도 원래 만료일까지는 동작한다는 보고가 있어요 [주장].) 주 1회 갱신을 권해요.")
        return EXIT_OK
    finally:
        if mock:
            mock.stop()


def _cmd_check_setup(args) -> int:
    from doha.r2 import ENV_VARS, R2Config, R2Error, self_test

    ok = True
    print("환경 변수 (값은 표시하지 않아요):")
    for name in ("IG_ACCESS_TOKEN", "IG_USER_ID", "IG_API_BASE", "IG_API_VERSION") + ENV_VARS + ("R2_ENDPOINT",):
        has = bool(os.environ.get(name, "").strip())
        optional = name in ("IG_USER_ID", "IG_API_BASE", "IG_API_VERSION", "R2_ENDPOINT")
        mark = "✓" if has else ("·" if optional else "✗")
        print(f"  {mark} {name}{'' if has else (' (선택)' if optional else ' — 없음')}")
        ok &= has or optional
    print("SigV4 서명 자체 시험 (AWS 문서 공개 예제):")
    ok &= self_test()
    try:
        cfg = R2Config.from_env()
        host = urllib.parse.urlsplit(cfg.endpoint).netloc
        if host.endswith(".r2.cloudflarestorage.com"):
            host = "<계정ID>.r2.cloudflarestorage.com"  # 계정 ID 도 값이라 화면·로그에 남기지 않는다
        print(f"R2: 엔드포인트 {host} · 버킷 설정됨 · 공개 주소 {cfg.public_base_url}")
        if ".r2.dev" in cfg.public_base_url:
            print("  주의: r2.dev 주소는 시험용이에요 (속도 제한 변동). 운영은 내 도메인을 연결하세요.")
    except R2Error as e:
        print(f"R2: {e}")
        ok = False
    token = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    if token:
        g = Graph(token)
        print(f"Instagram API: {g.base}{'/' + g.version if g.version else ''}")
        try:
            me = g.get("me", fields="user_id,username")
            uid = os.environ.get("IG_USER_ID", "").strip() or str(me.get("user_id") or me.get("id"))
            print(f"  ✓ 계정 @{me.get('username', '?')}")
            check_quota(g, uid)
        except GraphError as e:
            print(f"  ✗ {e.explain()}")
            ok = False
    print("\n준비 완료" if ok else "\n빠진 설정이 있어요 (위 ✗).")
    return EXIT_OK if ok else EXIT_ERROR


# ================================================================ 모의 서버 (--mock · 시험용)

class MockServer:
    """R2(S3 서명 검증 포함) + Graph API 게시 흐름을 흉내 내는 로컬 HTTP 서버. 네트워크 밖으로 나가지 않는다.

    faults 로 오류 경로를 재현한다: token_expired, permission, rate_limit, quota_full, aspect_strict, fetch_fail,
    status_error, publish_drop(게시는 되고 응답만 끊김), no_alt_text, same_token.
    """

    def __init__(self, faults: set[str] | None = None, polls_before_finished: int = 1):
        self.faults = set(faults or ())
        self.polls_before_finished = polls_before_finished
        self.token = "mock-ig-token-0000000000000000"
        self.access, self.secret, self.bucket = "MOCKACCESSKEY", "mock-secret-key", "doha-mock"
        self.user_id = "17841400000000001"
        self.objects: dict[str, tuple[bytes, str]] = {}
        self.containers: dict[str, dict] = {}
        self.published: list[dict] = []
        self.calls: list[tuple[str, str, dict]] = []
        self.sig_checked = 0
        self._seq = 1000
        self._lock = threading.Lock()
        self.httpd = None

    # -- 수명
    def start(self) -> "MockServer":
        from http.server import ThreadingHTTPServer

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self.httpd.daemon_threads = True
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        return self

    def stop(self) -> None:
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()

    @property
    def graph_base(self) -> str:
        return self.base + "/graph"

    def r2_config(self):
        from doha.r2 import R2Config

        return R2Config(self.access, self.secret, self.bucket, self.base + "/s3", self.base + "/pub")

    def _id(self) -> str:
        with self._lock:
            self._seq += 1
            return f"{self.user_id[-4:]}{self._seq}"

    # -- 요청 처리
    def _handler(self):
        server = self
        from http.server import BaseHTTPRequestHandler

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):  # 조용히
                pass

            def _send(self, status: int, body: bytes = b"", ctype: str = "application/json", head: bool = False):
                self.send_response(status)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                if not head:
                    self.wfile.write(body)

            def _json(self, status: int, obj: dict):
                self._send(status, json.dumps(obj).encode())

            def do_HEAD(self):
                self._route("HEAD")

            def do_GET(self):
                self._route("GET")

            def do_PUT(self):
                self._route("PUT")

            def do_DELETE(self):
                self._route("DELETE")

            def do_POST(self):
                self._route("POST")

            def _route(self, method: str):
                parts = urllib.parse.urlsplit(self.path)
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                try:
                    if parts.path.startswith("/s3/"):
                        return server._s3(self, method, parts, body)
                    if parts.path.startswith("/pub/"):
                        key = urllib.parse.unquote(parts.path[len("/pub/"):])
                        if key not in server.objects:
                            return self._send(404, b"not found", "text/plain", head=method == "HEAD")
                        data, ctype = server.objects[key]
                        return self._send(200, data, ctype, head=method == "HEAD")
                    if parts.path.startswith("/graph/"):
                        params = dict(urllib.parse.parse_qsl(parts.query))
                        if method == "POST":
                            params.update(urllib.parse.parse_qsl(body.decode("utf-8")))
                        return server._graph(self, method, parts.path[len("/graph/"):], params)
                    self._send(404, b"", "text/plain")
                except _Drop:
                    self.close_connection = True
                    self.connection.shutdown(2)

        return H

    def _s3(self, h, method: str, parts, body: bytes):
        from doha.r2 import signature_v4

        auth = h.headers.get("Authorization") or ""
        m = re.match(r"AWS4-HMAC-SHA256 Credential=([^/]+)/(\d{8})/([^/]+)/s3/aws4_request, "
                     r"SignedHeaders=([^,]+), Signature=([0-9a-f]{64})$", auth)
        payload_hash = h.headers.get("x-amz-content-sha256") or ""
        if not m or m.group(1) != self.access or m.group(3) != "auto":
            return h._send(403, b"<Error><Code>AccessDenied</Code></Error>", "application/xml")
        if payload_hash != hashlib.sha256(body).hexdigest():
            return h._send(400, b"<Error><Code>XAmzContentSHA256Mismatch</Code></Error>", "application/xml")
        signed = {n: h.headers.get(n, "") for n in m.group(4).split(";")}
        _, sig, _ = signature_v4(method, self.base + parts.path, signed, payload_hash, access_key=self.access,
                                 secret_key=self.secret, region="auto", service="s3",
                                 amz_date=h.headers.get("x-amz-date", ""))
        if sig != m.group(5):
            return h._send(403, b"<Error><Code>SignatureDoesNotMatch</Code></Error>", "application/xml")
        self.sig_checked += 1
        prefix = f"/s3/{self.bucket}/"
        if not parts.path.startswith(prefix):
            return h._send(404, b"<Error><Code>NoSuchBucket</Code></Error>", "application/xml")
        key = urllib.parse.unquote(parts.path[len(prefix):])
        if method == "PUT":
            self.objects[key] = (body, h.headers.get("Content-Type") or "application/octet-stream")
            return h._send(200, b"")
        if method == "DELETE":
            self.objects.pop(key, None)
            return h._send(204)
        return h._send(405, b"")

    def _err(self, h, status: int, code: int, msg: str, subcode: int = 0):
        err = {"message": msg, "type": "OAuthException", "code": code, "fbtrace_id": "mock"}
        if subcode:
            err["error_subcode"] = subcode
        return h._json(status, {"error": err})

    def _fetch(self, url: str) -> tuple[bytes, str] | None:
        if "fetch_fail" in self.faults or not url.startswith(self.base + "/pub/"):
            return None
        return self.objects.get(urllib.parse.unquote(url[len(self.base + "/pub/"):]))

    def _graph(self, h, method: str, path: str, p: dict):
        path = re.sub(r"^v\d+\.\d+/", "", path)
        self.calls.append((method, path, {k: v for k, v in p.items() if k != "access_token"}))
        if path == "refresh_access_token":
            if p.get("access_token") != self.token:
                return self._err(h, 400, 190, "Invalid OAuth access token.")
            new = self.token if "same_token" in self.faults else self.token[:-4] + "9999"
            return h._json(200, {"access_token": new, "token_type": "bearer", "expires_in": 5183944})
        if p.get("access_token") != self.token or "token_expired" in self.faults:
            return self._err(h, 400, 190, "Error validating access token: Session has expired.", 463)
        if "permission" in self.faults:
            return self._err(h, 403, 10, "Application does not have permission for this action")
        uid = self.user_id
        if method == "GET" and path == "me":
            return h._json(200, {"user_id": uid, "username": "doha.mock", "id": "mock-app-scoped"})
        if method == "GET" and path == f"{uid}/content_publishing_limit":
            used = 100 if "quota_full" in self.faults else len(self.published)
            return h._json(200, {"data": [{"quota_usage": used, "config": {"quota_total": 100, "quota_duration": 86400}}]})
        if method == "GET" and path == f"{uid}/media":
            fields = (p.get("fields") or "id").split(",")
            rows = [{k: m.get(k) for k in fields if k in m} for m in reversed(self.published)]
            return h._json(200, {"data": rows[: int(p.get("limit") or 25)]})
        if method == "POST" and path == f"{uid}/media":
            return self._create(h, p)
        if method == "POST" and path == f"{uid}/media_publish":
            if "rate_limit" in self.faults:
                return self._err(h, 400, 9, "Application request limit reached", 2207042)
            c = self.containers.get(p.get("creation_id", ""))
            if not c or c["status"] != "FINISHED":
                return self._err(h, 400, 9007, "Media ID is not available", 2207027)
            if c.get("published"):
                return self._err(h, 400, 9007, "Media already published", 2207027)
            c["published"] = True
            mid = self._id()
            self.published.append({"id": mid, "caption": c.get("caption", ""),
                                   "media_type": {"CAROUSEL": "CAROUSEL_ALBUM", "REELS": "VIDEO"}.get(c["kind"], "IMAGE"),
                                   "media_product_type": "REELS" if c["kind"] == "REELS" else "FEED",
                                   "permalink": f"https://www.instagram.com/{'reel' if c['kind'] == 'REELS' else 'p'}/MOCK{mid}/",
                                   "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000")})
            if "publish_drop" in self.faults:
                self.faults.discard("publish_drop")
                raise _Drop()
            return h._json(200, {"id": mid})
        if method == "GET":
            if path in self.containers:
                c = self.containers[path]
                if c["status"] == "IN_PROGRESS":
                    c["polls"] += 1
                    if c["polls"] > self.polls_before_finished:
                        c["status"] = "FINISHED"
                    elif "status_error" in self.faults:
                        c["status"] = "ERROR"
                return h._json(200, {"id": path, "status_code": c["status"],
                                     "status": "Error: Media upload has failed with error code 2207026"
                                     if c["status"] == "ERROR" else c["status"]})
            for m in self.published:
                if m["id"] == path:
                    return h._json(200, m)
        return self._err(h, 400, 100, f"Unsupported {method} request: {path}")

    def _create(self, h, p: dict):
        from PIL import Image

        kind = p.get("media_type") or "IMAGE"
        if "alt_text" in p and "no_alt_text" in self.faults:
            return self._err(h, 400, 100, "(#100) Param alt_text is not supported")
        c = {"kind": kind, "status": "IN_PROGRESS", "polls": 0, "caption": p.get("caption", ""), "params": p}
        if kind == "CAROUSEL":
            kids = [k for k in p.get("children", "").split(",") if k]
            if not 2 <= len(kids) <= 10 or any(k not in self.containers for k in kids):
                return self._err(h, 400, 100, "Invalid children for carousel")
        elif kind == "REELS":
            if not self._fetch(p.get("video_url", "")) or not self._fetch(p.get("cover_url", "")):
                return self._err(h, 400, 9004, "Media could not be fetched from this uri", 2207052)
            c["polls"] = -1  # 영상은 한 번 더 기다리게
        else:
            got = self._fetch(p.get("image_url", ""))
            if not got:
                return self._err(h, 400, 9004, "The media could not be fetched from this uri", 2207052)
            data, ctype = got
            if ctype != "image/jpeg" or data[:2] != b"\xff\xd8":
                return self._err(h, 400, 9004, "Only photo or video can be accepted as media type.", 2207052)
            if len(data) > MAX_JPEG_BYTES:
                return self._err(h, 400, 9004, "The image is too large to download.", 2207004)
            with Image.open(BytesIO(data)) as im:
                w, hgt = im.size
            lo = RATIO_RANGE[0] + (0.01 if "aspect_strict" in self.faults else 0)
            if not lo - 0.001 <= w / hgt <= RATIO_RANGE[1] + 0.001:
                return self._err(h, 400, 36003, "The aspect ratio is not supported.", 2207009)
            c["image"] = (w, hgt, len(data))
        cid = self._id()
        self.containers[cid] = c
        return h._json(200, {"id": cid})


class _Drop(Exception):
    """모의 서버: 응답을 보내지 않고 연결을 끊는다 (게시 응답 유실 재현)."""
