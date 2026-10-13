"""게시 전 검수 (check).

광고·AI 표시, 지어낸 체험 표현, 상품 출처·확인일, 효능 주장, 글자 수, 필수 항목을 본다.
오류(error)는 게시를 막고, 주의(warn)는 사람이 보고 판단한다. 파일을 고치지 않는다.

  python doha.py check black-slacks
  python doha.py check --all
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import yaml

from doha.core import (
    ROOT,
    Post,
    disclosure_label,
    load_config,
    load_persona,
    posts_root,
    resolve_post,
)

# 레이아웃별 필수 항목 (렌더러가 빈칸으로 그리면 안 되는 것)
SLIDE_REQUIRED: dict[str, list[str]] = {
    "cover": ["title"],
    "look": ["image", "title", "items"],
    "tip": ["title"],
    "compare": ["left", "right"],
    "checklist": ["title", "checks"],
    "product": ["product"],
    "cta": ["title"],
}
SCENE_REQUIRED: dict[str, list[str]] = {
    "reel-hook": ["text"],
    "reel-look": ["image", "text"],
    "reel-text": ["text"],
    "reel-end": ["text"],
}
MOTIONS = {"zoom-in", "zoom-out", "pan-left", "pan-right", "still"}
FORMATS = {"carousel", "reel", "both"}
STATUSES = ["idea", "draft", "images", "rendered", "reviewed", "approved", "posted"]
PILLARS = {"돌려입기", "컬러공식", "비율", "상황별", "아이템가이드", "협찬", "제휴"}
GOALS = {"save", "share", "follow", "click", "reach"}
FRAMINGS = {"full-body", "three-quarter", "waist-up", "detail", "flatlay"}
IMAGE_STATUSES = {"todo", "generated", "approved", "rejected"}

REEL_SECONDS = (5.0, 90.0)
CAPTION_LIMIT = 2200
FEED_LINE_UNITS = 30            # 피드 캡션 한 줄 폭 (text_width 기준, 390pt 화면 근사)
SLIDES_RANGE = (3, 20)          # 앱 업로드 캐러셀 최대 20장
PRODUCT_STALE_DAYS = (14, 30)   # (주의, 오류)
POST_TIME_RANGE = ("05:00", "23:59")

# 가상 인물이 실제로 입고·쓰고·산 것처럼 말하는 표현 → 오류 (공백 무시하고 비교)
FABRICATED = [
    "입어보니", "입어봤", "써보니", "써봤", "발라보니", "발라봤", "먹어보니", "먹어봤",
    "신어보니", "신어봤", "제가 샀", "제가 산", "저도 샀", "제가 구매", "내돈내산",
    "직접 착용", "직접 사용", "직접 입어", "직접 써", "직접 신어", "직접 발라",
    "실착 후기", "실착해", "솔직 후기", "착용 후기", "사용 후기", "리얼 후기", "찐후기",
    "한 달 사용", "써본 결과", "입어본 결과",
]
# 의학·효능 주장 → 오류 (옷·잡화 계정이 근거 없이 쓰면 표시광고법·의료 광고 문제)
MEDICAL = [
    "치료", "개선 효과", "다이어트 효과", "피부 재생", "의학적", "의약", "질병", "완치", "효능",
    "체지방", "지방 분해", "셀룰라이트", "디톡스", "독소 배출", "살이 빠", "붓기 제거", "부기 제거",
    "혈액순환", "통증 완화", "탈모", "주름 개선", "미백 효과", "항균 효과", "면역",
]
# 과장 표현 → 상품·협찬 맥락에서 주의
EXAGGERATION = [
    "최고", "1위", "무조건", "완벽", "인생템", "역대급", "유일", "최저가", "품절 대란",
    "재구매", "강추", "필수템",
]
# 페르소나 금지 방향 (brand/doha.yaml not_this) → 주의
BODY_SHAMING = ["뚱뚱", "하체비만", "팔뚝살", "뱃살", "살쪄 보", "코끼리 다리", "통통", "다이어트", "군살"]
# 표시 플래그가 꺼져 있는데 대가를 암시하는 말
SPONSOR_WORDS = ["광고", "협찬", "유료 파트너십", "제공받", "지원받", "체험단"]

# 텍스트 검사에서 건너뛰는 키 (파일·식별자·숫자)
_TEXT_SKIP_KEYS = {"layout", "image", "product", "motion", "seconds", "file", "id",
                   "source_url", "link", "checked_at", "price_krw", "audio"}


@dataclass
class Issue:
    level: str      # 'error' | 'warn'
    code: str
    message: str
    where: str = ""

    def __str__(self) -> str:
        loc = f" {self.where}" if self.where else ""
        return f"[{self.code}]{loc} — {self.message}"


# ---------------------------------------------------------------- helpers

def _norm(s: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFC", s))


def find_phrases(text: str, phrases: list[str]) -> list[str]:
    """공백을 무시하고 포함된 표현 목록 ('입어 보니'도 '입어보니'로 잡음)."""
    n = _norm(text)
    return [p for p in phrases if _norm(p) in n]


def text_width(s: str) -> float:
    """화면 폭 기준 글자 수: 한글·전각 1, 영문·숫자·공백 0.5."""
    return sum(1.0 if unicodedata.east_asian_width(c) in "WF" else 0.5 for c in s)


def as_date(v) -> date | None:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v.strip()):
        try:
            return date.fromisoformat(v.strip())
        except ValueError:
            return None
    return None


def as_time(v) -> str | None:
    """'07:40' → '07:40'. YAML이 7:40 을 60진수 정수(460)로 읽은 경우도 되돌린다."""
    if isinstance(v, bool):
        return None
    if isinstance(v, int) and 0 <= v < 24 * 60:
        return f"{v // 60:02d}:{v % 60:02d}"
    if isinstance(v, str):
        m = re.fullmatch(r"(\d{1,2}):(\d{2})", v.strip())
        if m and int(m.group(1)) < 24 and int(m.group(2)) < 60:
            return f"{int(m.group(1)):02d}:{m.group(2)}"
    return None


def _empty(v) -> bool:
    return v is None or (isinstance(v, (str, list, dict)) and not (v.strip() if isinstance(v, str) else v))


def _list(v) -> list:
    return v if isinstance(v, list) else []


def _dict(v) -> dict:
    return v if isinstance(v, dict) else {}


def post_format(data: dict) -> tuple[bool, bool]:
    """(카드뉴스 포함, 릴스 포함)."""
    fmt = data.get("format") or "both"
    return fmt in ("carousel", "both"), fmt in ("reel", "both")


def reel_seconds(data: dict) -> float:
    total = 0.0
    for sc in _list(_dict(data.get("reel")).get("scenes")):
        s = _dict(sc).get("seconds")
        if isinstance(s, (int, float)) and not isinstance(s, bool) and s > 0:
            total += float(s)
    return total


class _Ctx:
    def __init__(self, post: Post, persona: dict, config: dict):
        self.post = post
        self.d = post.data if isinstance(post.data, dict) else {}
        self.persona = persona
        self.config = config
        self.issues: list[Issue] = []
        self.has_carousel, self.has_reel = post_format(self.d)
        self.post_date = as_date(self.d.get("date"))
        disc = _dict(self.d.get("disclosure"))
        self.flags = {k: disc.get(k) is True for k in ("paid", "gifted", "affiliate")}
        self.products = [p for p in _list(self.d.get("products")) if isinstance(p, dict)]
        self.sponsored = any(self.flags.values()) or bool(self.products)

    def error(self, code: str, where: str, msg: str) -> None:
        self.issues.append(Issue("error", code, msg, where))

    def warn(self, code: str, where: str, msg: str) -> None:
        self.issues.append(Issue("warn", code, msg, where))

    def slides(self) -> list[dict]:
        return [s if isinstance(s, dict) else {} for s in _list(self.d.get("slides"))]

    def scenes(self) -> list[dict]:
        return [s if isinstance(s, dict) else {} for s in _list(_dict(self.d.get("reel")).get("scenes"))]


# ---------------------------------------------------------------- sections

def _meta(c: _Ctx) -> None:
    d, post = c.d, c.post
    if not c.d:
        c.error("meta.empty", "post.yaml", "post.yaml 이 비어 있거나 형식이 맞지 않아요.")
        return
    pid = d.get("id")
    if pid != post.dir.name:
        c.error("meta.id", "id", f"id '{pid}' 가 폴더 이름 '{post.dir.name}' 과 달라요. 같게 맞춰주세요.")
    if c.post_date is None:
        c.error("meta.date", "date", f"날짜 형식이 YYYY-MM-DD 가 아니에요: {d.get('date')!r}")
    elif isinstance(pid, str) and not pid.startswith(c.post_date.isoformat()):
        c.warn("meta.id_date", "id", f"id 가 게시 날짜({c.post_date})로 시작하지 않아요. 폴더 이름도 함께 바꾸세요.")
    raw_time = d.get("time")
    t = as_time(raw_time)
    if raw_time is not None and t is None:
        c.error("meta.time", "time", f"시각 형식이 HH:MM 이 아니에요: {raw_time!r}")
    elif isinstance(raw_time, int):
        c.warn("meta.time", "time", f'시각은 따옴표로 감싸주세요 (예: time: "{t}").')
    if t and not (POST_TIME_RANGE[0] <= t <= POST_TIME_RANGE[1]):
        c.warn("meta.time_range", "time", f"게시 시각 {t} 이 05:00–23:59 밖이에요. 새벽 게시가 맞는지 확인하세요.")
    if d.get("format") not in FORMATS:
        c.error("meta.format", "format", f"format 은 carousel | reel | both 중 하나여야 해요: {d.get('format')!r}")
    if d.get("status") not in STATUSES:
        c.warn("meta.status", "status", f"알 수 없는 status: {d.get('status')!r} ({' → '.join(STATUSES)})")
    if d.get("pillar") and d.get("pillar") not in PILLARS:
        c.warn("meta.pillar", "pillar", f"정해진 콘텐츠 기둥이 아니에요: {d.get('pillar')!r} ({' | '.join(sorted(PILLARS))})")
    if d.get("goal") and d.get("goal") not in GOALS:
        c.warn("meta.goal", "goal", f"알 수 없는 goal: {d.get('goal')!r} ({' | '.join(sorted(GOALS))})")
    if _empty(d.get("hook")):
        c.warn("meta.hook", "hook", "hook(첫 문장)이 비어 있어요.")


def _disclosure(c: _Ctx) -> None:
    disc = c.d.get("disclosure")
    if not isinstance(disc, dict):
        c.error("disclosure.ai_persona", "disclosure", "disclosure 항목이 없어요. ai_persona: true 를 포함해 채워주세요.")
        return
    if disc.get("ai_persona") is not True:
        c.error("disclosure.ai_persona", "disclosure.ai_persona",
                "ai_persona 는 항상 true 여야 해요. 도하는 AI 가상 인물이라는 표시를 끌 수 없어요.")
    for k in ("paid", "gifted", "affiliate"):
        v = disc.get(k)
        if v is not None and not isinstance(v, bool):
            c.error("disclosure.type", f"disclosure.{k}", f"{k} 는 따옴표 없이 true/false 로 적어주세요: {v!r}")
    brand = str(disc.get("brand") or "").strip()
    if (c.flags["paid"] or c.flags["gifted"]) and not brand:
        kind = "광고" if c.flags["paid"] else "협찬"
        c.error("disclosure.brand_missing", "disclosure.brand",
                f"{kind} 표시에는 대가를 준 브랜드명이 필요해요 (예: '{kind} · 브랜드명').")
    if any(c.flags.values()) and not disclosure_label(c.d, c.persona):
        c.error("disclosure.label_empty", "brand/doha.yaml disclosure.labels",
                "표시 플래그가 켜져 있는데 표시 문구가 비어 있어요. 페르소나 파일의 labels 를 확인하세요.")
    linked = [str(p.get("id") or i) for i, p in enumerate(c.products, 1) if str(p.get("link") or "").strip()]
    if linked and not c.flags["affiliate"]:
        c.error("disclosure.affiliate_flag", "disclosure.affiliate",
                f"제휴 링크가 있는 상품({', '.join(linked)})이 있는데 affiliate 가 false 예요. 수수료 링크면 true 로 켜야 해요.")
    if c.flags["affiliate"] and not linked:
        c.warn("disclosure.affiliate_link", "products", "affiliate 가 true 인데 link 가 있는 상품이 없어요. 링크·코드를 어디서 안내하는지 확인하세요.")
    pillar = c.d.get("pillar")
    if pillar == "협찬" and not (c.flags["paid"] or c.flags["gifted"]):
        c.warn("disclosure.pillar", "pillar", "pillar 가 '협찬' 인데 paid/gifted 가 모두 false 예요.")
    if pillar == "제휴" and not c.flags["affiliate"]:
        c.warn("disclosure.pillar", "pillar", "pillar 가 '제휴' 인데 affiliate 가 false 예요.")


def _caption(c: _Ctx) -> None:
    from doha.preview import build_caption, caption_fold, normalize_hashtags

    d = c.d
    body = d.get("caption")
    if _empty(body) or not isinstance(body, str):
        c.error("caption.empty", "caption", "캡션이 비어 있어요.")
        body = ""
    caption = build_caption(c.post, c.persona, c.config, warn=lambda _m: None)
    label = disclosure_label(d, c.persona)
    first_line = caption.split("\n", 1)[0]
    if any(c.flags.values()):
        expected = f"[{label}]" if label else ""
        # 소비자가 알아볼 단어가 첫 줄에 있어야 한다 (라벨 설정이 비어 '[ · 브랜드]'가 되는 경우도 잡음)
        keywords = ["광고"] if c.flags["paid"] else ["협찬", "광고"] if c.flags["gifted"] else ["광고", "제휴", "수수료"]
        fold = caption_fold(caption)
        if (not label or not first_line.startswith(expected) or expected not in fold
                or not any(k in first_line for k in keywords)):
            c.error("disclosure.caption_first_line", "caption",
                    f"캡션 첫 줄(더 보기 전)에 '{'/'.join(keywords)}' 표시가 보이지 않아요. 지금 첫 줄: {first_line[:40]!r}")
        # 공정위 지침(2026-06-01): 광고에 AI 가상인물이 나오면 글의 첫 부분에 '가상인물' 표시
        if "가상인물" not in fold.replace(" ", ""):
            c.error("disclosure.virtual_notice", "caption",
                    "광고·협찬·제휴 게시물은 캡션 첫 부분에 '가상인물' 고지가 있어야 해요 "
                    "(brand/doha.yaml disclosure.ad_virtual_notice 또는 캡션 첫 줄).")
        # 피드 첫 줄은 '아이디 + 표시 줄'. 두 줄을 넘기면 고지 끝부분이 '더 보기' 뒤로 밀린다
        if text_width(f"{c.persona.get('handle', '')} {first_line}") > FEED_LINE_UNITS * 2:
            c.warn("caption.fold", "caption",
                   "표시·고지 줄이 길어 휴대폰에서 끝부분이 '더 보기' 뒤로 밀릴 수 있어요. preview 로 확인하세요.")
    pdisc = _dict(c.persona.get("disclosure"))
    footer = str(pdisc.get("caption_footer") or "").strip()
    if not footer or footer not in caption:
        c.warn("caption.ai_footer", "caption", "캡션에 AI 가상인물 안내 문구(persona.disclosure.caption_footer)가 없어요.")
    if c.products:
        note = str(pdisc.get("product_image_note") or "").strip()
        if not note or note not in caption:
            c.warn("product.image_note", "caption",
                   "제품이 있는데 'AI 합성 이미지라 실물과 다를 수 있다'는 안내(persona.disclosure.product_image_note)가 캡션에 없어요.")
        if "확인" not in body:
            c.warn("product.caption_source", "caption",
                   "캡션에 제품 정보 출처·확인일 문장이 없어요 (예: '제품 정보는 브랜드 공식 페이지 기준(10/13 확인)이에요.').")
    if len(caption) > CAPTION_LIMIT:
        c.error("caption.too_long", "caption",
                f"최종 캡션이 {len(caption):,}자예요. 인스타그램 한도 {CAPTION_LIMIT:,}자 안으로 줄여주세요.")
    hook = str(d.get("hook") or "").strip()
    body_first = next((ln.strip() for ln in body.splitlines() if ln.strip()), "")
    if hook and body_first and _norm(hook) not in _norm(body_first):
        c.warn("caption.hook", "caption", f"캡션 첫 줄에 hook('{hook}')이 없어요. 더 보기 전에 보이는 문장이에요.")
    if body and not any(c.flags.values()):
        found = find_phrases(body, SPONSOR_WORDS)
        if found:
            c.warn("disclosure.mention", "caption",
                   f"캡션에 '{', '.join(found)}' 이(가) 있는데 표시 플래그가 모두 꺼져 있어요. 대가가 있었다면 disclosure 를 켜세요.")
    inline = re.findall(r"#[^\s#]+", body)
    if inline:
        c.warn("hashtags.inline", "caption", f"캡션 본문에 해시태그가 있어요({' '.join(inline[:5])}). hashtags 칸으로 옮기면 개수 관리가 돼요.")

    raw = d.get("hashtags")
    raw_list = raw if isinstance(raw, list) else ([] if raw is None else [raw])
    tags = normalize_hashtags(raw_list)
    max_tags = int(_dict(c.config.get("publishing")).get("max_hashtags") or 5)
    if len(tags) > max_tags:
        c.error("hashtags.too_many", "hashtags", f"해시태그 {len(tags)}개 — 운영 기준 최대 {max_tags}개예요.")
    elif len(tags) < 3:
        c.warn("hashtags.too_few", "hashtags", f"해시태그가 {len(tags)}개예요. 주제 해시태그 3–{max_tags}개를 권장해요.")
    bad = [t for t in tags if not re.fullmatch(r"[\w가-힣]+", t)]
    if bad:
        c.error("hashtags.invalid", "hashtags", f"해시태그에 공백·기호가 있으면 끊겨요: {', '.join(bad)}")
    stripped = [str(t).strip().lstrip("#") for t in raw_list if str(t).strip().lstrip("#")]
    if len(stripped) != len(tags):
        c.warn("hashtags.duplicate", "hashtags", "중복된 해시태그가 있어요 (한 번만 넣어요).")
    if not any(c.flags.values()):
        sponsor_tags = [t for t in tags if t in ("광고", "협찬", "유료광고", "제휴")]
        if sponsor_tags:
            c.warn("disclosure.mention", "hashtags", f"#{sponsor_tags[0]} 해시태그가 있는데 표시 플래그가 꺼져 있어요.")


def _slides(c: _Ctx) -> None:
    if not c.has_carousel:
        return
    raw = c.d.get("slides")
    if not isinstance(raw, list) or not raw:
        c.error("layout.required", "slides", "카드뉴스(format: carousel/both)인데 slides 가 비어 있거나 목록이 아니에요.")
        return
    slides = c.slides()
    product_ids = {str(p.get("id")) for p in c.products if p.get("id") is not None}
    n = len(slides)
    if n < SLIDES_RANGE[0] or n > SLIDES_RANGE[1]:
        c.warn("slides.count", "slides", f"슬라이드 {n}장 — {SLIDES_RANGE[0]}–{SLIDES_RANGE[1]}장을 권장해요 (앱 최대 20장).")
    if not any(s.get("layout") == "cta" for s in slides):
        c.warn("slides.no_cta", "slides", "마지막에 저장·팔로우를 권하는 cta 슬라이드가 없어요.")
    for i, s in enumerate(slides, 1):
        where = f"slides[{i:02d}]"
        layout = s.get("layout")
        if layout not in SLIDE_REQUIRED:
            c.error("layout.unknown", f"{where}.layout",
                    f"알 수 없는 레이아웃 {layout!r} ({' | '.join(SLIDE_REQUIRED)})")
            continue
        missing = [f for f in SLIDE_REQUIRED[layout] if _empty(s.get(f))]
        if layout == "tip" and _empty(s.get("body")) and _empty(s.get("bullets")):
            missing.append("body 또는 bullets")
        if layout == "compare":
            for side in ("left", "right"):
                sd = s.get(side)
                if isinstance(sd, dict) and _empty(sd.get("image")) and _empty(sd.get("caption")):
                    missing.append(f"{side}.image/caption")
        if missing:
            c.error("layout.required", where, f"{layout} 레이아웃에 필요한 항목이 비어 있어요: {', '.join(missing)}")
        if layout == "product" and s.get("product") and str(s.get("product")) not in product_ids:
            c.error("product.unknown", f"{where}.product", f"products 에 id '{s.get('product')}' 상품이 없어요.")
        _slide_text_length(c, where, layout, s)


def _slide_text_length(c: _Ctx, where: str, layout: str, s: dict) -> None:
    title = s.get("title") if isinstance(s.get("title"), str) else ""
    if layout == "cover" and title:
        lines = title.split("\n")
        if len(lines) > 3:
            c.warn("slides.text_long", f"{where}.title", f"커버 제목이 {len(lines)}줄이에요. 3줄 이하로 줄여주세요.")
        for ln in lines:
            if text_width(ln) > 14:
                c.warn("slides.text_long", f"{where}.title",
                       f"커버 제목 한 줄이 약 {text_width(ln):.0f}자예요 (권장 14자 이하, \\n 으로 나누기): '{ln}'")
    if layout == "look" and title and text_width(title.replace("\n", "")) > 18:
        c.warn("slides.text_long", f"{where}.title", f"룩 제목이 약 {text_width(title):.0f}자예요 (권장 18자 이하): '{title}'")
    for key, limit, name in (("bullets", 28, "팁 항목"), ("checks", 28, "체크 항목")):
        if layout in ("tip", "checklist"):
            for j, b in enumerate(_list(s.get(key)), 1):
                if isinstance(b, str) and text_width(b) > limit:
                    c.warn("slides.text_long", f"{where}.{key}[{j}]",
                           f"{name}이 약 {text_width(b):.0f}자예요 (권장 {limit}자 이하): '{b}'")


def _reel(c: _Ctx) -> None:
    if not c.has_reel:
        return
    reel = c.d.get("reel")
    scenes = c.scenes()
    if not isinstance(reel, dict) or not scenes:
        c.error("reel.no_scenes", "reel.scenes", "릴스(format: reel/both)인데 장면(scenes) 목록이 없어요.")
        return
    for i, sc in enumerate(scenes, 1):
        where = f"reel.scenes[{i}]"
        layout = sc.get("layout")
        if layout not in SCENE_REQUIRED:
            c.error("layout.unknown", f"{where}.layout",
                    f"알 수 없는 릴스 레이아웃 {layout!r} ({' | '.join(SCENE_REQUIRED)})")
        else:
            missing = [f for f in SCENE_REQUIRED[layout] if _empty(sc.get(f))]
            if missing:
                c.error("layout.required", where, f"{layout} 장면에 필요한 항목이 비어 있어요: {', '.join(missing)}")
        sec = sc.get("seconds")
        if not isinstance(sec, (int, float)) or isinstance(sec, bool) or sec <= 0:
            c.error("reel.seconds", f"{where}.seconds", f"장면 길이(seconds)는 0보다 큰 숫자여야 해요: {sec!r}")
        motion = sc.get("motion")
        if motion is not None and motion not in MOTIONS:
            c.error("layout.unknown", f"{where}.motion", f"알 수 없는 motion {motion!r} ({' | '.join(sorted(MOTIONS))})")
    total = reel_seconds(c.d)
    lo, hi = REEL_SECONDS
    if not (lo <= total <= hi):
        c.error("reel.duration", "reel.scenes", f"릴스 총 길이 {total:.1f}초 — {lo:.0f}–{hi:.0f}초 안으로 맞춰주세요.")
    audio = reel.get("audio")
    if audio:
        cands = [c.post.dir / str(audio), ROOT / str(audio)]
        if not any(p.exists() for p in cands):
            c.error("reel.audio_missing", "reel.audio", f"음원 파일이 없어요: {audio} (없으면 null 로 두고 앱에서 음원 추가)")


def _images(c: _Ctx) -> None:
    images = c.d.get("images")
    images = images if isinstance(images, dict) else {}
    refs: dict[str, list[str]] = {}

    def ref(key, where):
        if key is None or key == "":
            return
        refs.setdefault(str(key), []).append(where)

    if c.has_carousel:
        for i, s in enumerate(c.slides(), 1):
            ref(s.get("image"), f"slides[{i:02d}].image")
            for side in ("left", "right"):
                if isinstance(s.get(side), dict):
                    ref(s[side].get("image"), f"slides[{i:02d}].{side}.image")
    if c.has_reel:
        for i, sc in enumerate(c.scenes(), 1):
            ref(sc.get("image"), f"reel.scenes[{i}].image")

    for key, wheres in refs.items():
        if key not in images:
            c.error("image.key_missing", ", ".join(wheres[:3]), f"images 에 '{key}' 가 없어요. 키 이름을 확인하거나 images 에 추가하세요.")

    used = [k for k in refs if k in images]
    missing_files = [k for k in used if c.post.image_path(k) is None]
    if missing_files:
        c.warn("image.file_missing", "images",
               f"사진 파일이 아직 없어요 ({', '.join(missing_files)}) — 자리표시 이미지로 렌더링돼요.")
    post_approved = c.d.get("status") in ("approved", "posted")
    not_ok, rejected, todo_prompts = [], [], []
    for k in used:
        spec = images[k] if isinstance(images[k], dict) else {}
        st = spec.get("status")
        if st not in IMAGE_STATUSES:
            c.warn("image.status", f"images.{k}.status", f"알 수 없는 사진 status {st!r} ({' | '.join(sorted(IMAGE_STATUSES))})")
        if st == "rejected":
            rejected.append(k)
        elif post_approved and st != "approved":
            not_ok.append(k)
        if spec.get("framing") and spec.get("framing") not in FRAMINGS:
            c.warn("image.framing", f"images.{k}.framing", f"알 수 없는 framing {spec.get('framing')!r}")
        if any("TODO" in str(spec.get(f) or "") for f in ("prompt", "outfit")):
            todo_prompts.append(k)
    if rejected:
        c.warn("image.rejected", "images", f"반려(rejected)된 사진을 쓰고 있어요: {', '.join(rejected)}")
    if not_ok:
        c.warn("image.not_approved", "images", f"게시물은 approved 인데 승인되지 않은 사진이 있어요: {', '.join(not_ok)}")
    if todo_prompts:
        c.warn("image.todo", "images", f"사진 프롬프트·의상 묘사에 TODO 가 남아 있어요: {', '.join(todo_prompts)}")


def _products(c: _Ctx) -> None:
    raw = c.d.get("products")
    if raw is not None and not isinstance(raw, list):
        c.error("product.fields", "products", "products 는 목록이어야 해요 (없으면 []).")
        return
    ref_date = c.post_date or date.today()
    for i, p in enumerate(_list(raw), 1):
        if not isinstance(p, dict):
            c.error("product.fields", f"products[{i}]", "상품 항목 형식이 맞지 않아요.")
            continue
        where = f"products[{p.get('id') or i}]"
        if _empty(p.get("id")):
            c.error("product.fields", where, "상품 id 가 없어요 (product 슬라이드에서 참조).")
        missing = [f for f in ("brand", "name") if _empty(p.get(f))]
        if missing:
            c.error("product.fields", where, f"상품 정보가 비어 있어요: {', '.join(missing)}")
        url = str(p.get("source_url") or "").strip()
        if not url:
            c.error("product.source", f"{where}.source_url", "상품 사실 정보의 출처(공식 페이지 source_url)가 없어요.")
        elif not url.startswith(("http://", "https://")):
            c.error("product.source", f"{where}.source_url", f"source_url 은 http(s) 주소여야 해요: {url}")
        checked_raw = p.get("checked_at")
        checked = as_date(checked_raw)
        if _empty(checked_raw):
            c.error("product.checked", f"{where}.checked_at", "가격·소재 확인일(checked_at)이 없어요.")
        elif checked is None:
            c.error("product.checked", f"{where}.checked_at", f"checked_at 형식이 YYYY-MM-DD 가 아니에요: {checked_raw!r}")
        else:
            age = (ref_date - checked).days
            warn_days, err_days = PRODUCT_STALE_DAYS
            if age > err_days:
                c.error("product.stale", f"{where}.checked_at",
                        f"상품 정보 확인일이 게시일보다 {age}일 전이에요 ({err_days}일 초과). 공식 페이지에서 다시 확인하세요.")
            elif age > warn_days:
                c.warn("product.stale", f"{where}.checked_at",
                       f"상품 정보 확인일이 게시일보다 {age}일 전이에요. 게시 직전에 가격·재고를 다시 확인하세요.")
            if checked > date.today():
                c.warn("product.checked", f"{where}.checked_at", f"확인일({checked})이 오늘보다 뒤예요.")
        price = p.get("price_krw")
        if price is not None and (not isinstance(price, int) or isinstance(price, bool) or price < 0):
            c.error("product.fields", f"{where}.price_krw", f"가격은 원 단위 정수로 적어주세요: {price!r}")
        if not isinstance(p.get("facts", []), list):
            c.error("product.fields", f"{where}.facts", "facts 는 목록이어야 해요.")


def _texts(c: _Ctx) -> None:
    items: list[tuple[str, str, bool]] = []

    def walk(where: str, v, product_ctx: bool) -> None:
        if isinstance(v, str):
            items.append((where, v, product_ctx))
        elif isinstance(v, list):
            for i, x in enumerate(v, 1):
                walk(f"{where}[{i}]", x, product_ctx)
        elif isinstance(v, dict):
            for k, x in v.items():
                if k not in _TEXT_SKIP_KEYS:
                    walk(f"{where}.{k}", x, product_ctx)

    walk("hook", c.d.get("hook"), c.sponsored)
    walk("caption", c.d.get("caption"), c.sponsored)
    walk("alt_text", c.d.get("alt_text"), False)
    if c.has_carousel:
        for i, s in enumerate(c.slides(), 1):
            walk(f"slides[{i:02d}]", s, c.sponsored or s.get("layout") == "product")
    if c.has_reel:
        for i, sc in enumerate(c.scenes(), 1):
            walk(f"reel.scenes[{i}]", sc, c.sponsored)
    for i, p in enumerate(c.products, 1):
        walk(f"products[{p.get('id') or i}]", {k: p.get(k) for k in ("brand", "name", "facts")}, True)

    todos: list[str] = []
    for where, text, product_ctx in items:
        if found := find_phrases(text, FABRICATED):
            c.error("text.experience", where,
                    f"체험을 지어낸 표현 '{', '.join(found)}' — 도하는 가상 인물이라 실제로 입거나 쓸 수 없어요. "
                    "스타일링 제안 문장으로 바꿔주세요 (예: '~하면 ~해 보여요').")
        if found := find_phrases(text, MEDICAL):
            c.error("text.medical", where, f"의학·효능 표현 '{', '.join(found)}' 은 쓰지 않아요 (근거가 있어도 제품 공식 문구를 그대로 인용하고 법률 확인).")
        if product_ctx and (found := find_phrases(text, EXAGGERATION)):
            c.warn("text.exaggeration", where, f"상품·협찬 맥락의 과장 표현 '{', '.join(found)}' — 근거 없는 최상급은 빼주세요.")
        if found := find_phrases(text, BODY_SHAMING):
            c.warn("text.body", where, f"체형·다이어트 표현 '{', '.join(found)}' — 페르소나 원칙(체형 비하 금지)과 맞는지 확인하세요.")
        if "TODO" in text:
            todos.append(where)
    if todos:  # 새 뼈대는 TODO 가 수십 곳이라 한 줄로 묶는다
        shown = ", ".join(todos[:6]) + (f" 외 {len(todos) - 6}곳" if len(todos) > 6 else "")
        c.error("text.todo", shown, f"아직 채우지 않은 TODO 가 {len(todos)}곳 남아 있어요.")
    if not any(c.flags.values()) and c.has_carousel:
        for i, s in enumerate(c.slides(), 1):
            blob = " ".join(str(v) for k, v in s.items() if k not in _TEXT_SKIP_KEYS and isinstance(v, str))
            if found := find_phrases(blob, SPONSOR_WORDS):
                c.warn("disclosure.mention", f"slides[{i:02d}]",
                       f"슬라이드에 '{', '.join(found)}' 이(가) 있는데 표시 플래그가 꺼져 있어요.")


def _misc(c: _Ctx) -> None:
    alt = c.d.get("alt_text")
    if _empty(alt):
        c.warn("alt_text.empty", "alt_text", "대체 텍스트(alt_text)가 비어 있어요. 앱의 고급 설정 → 접근성에 넣어요.")
    elif "AI" not in str(alt).upper() and "가상" not in str(alt):
        c.warn("alt_text.no_ai", "alt_text", "대체 텍스트에 AI 생성·가상 인물이라는 설명이 없어요.")
    if c.d.get("status") in ("approved", "posted"):
        review = _dict(c.d.get("review"))
        if _empty(review.get("approved_by")):
            c.warn("review.unsigned", "review.approved_by", "status 가 approved 인데 검수자(review.approved_by)가 비어 있어요.")


SECTIONS = (_meta, _disclosure, _caption, _slides, _reel, _images, _products, _texts, _misc)


def check_post(post: Post | str | Path, persona: dict | None = None, config: dict | None = None) -> list[Issue]:
    """게시물 하나를 검수해 Issue 목록을 돌려준다 (오류 먼저)."""
    if not isinstance(post, Post):
        post = resolve_post(post)
    if (post.data or {}).get("legacy"):
        return []  # 키트 이전 게시물: 성과 연결용 기록일 뿐 검수 대상이 아님
    config = config or load_config()
    persona = persona or load_persona(config)
    c = _Ctx(post, persona, config)
    for section in SECTIONS:
        if not c.d and section is not _meta:
            break
        try:
            section(c)
        except Exception as e:  # 형식이 크게 어긋난 post.yaml 이어도 나머지 검수는 계속한다
            c.error("check.crash", section.__name__.strip("_"),
                    f"검수 중 예외가 났어요 ({type(e).__name__}: {e}). post.yaml 형식을 확인하세요.")
    return sorted(c.issues, key=lambda x: 0 if x.level == "error" else 1)


def counts(issues: list[Issue]) -> tuple[int, int]:
    errors = sum(1 for i in issues if i.level == "error")
    return errors, len(issues) - errors


def format_report(post_id: str, issues: list[Issue]) -> str:
    errors, warns = counts(issues)
    lines = [f"검수: {post_id}"]
    for level, name in (("error", "오류"), ("warn", "주의")):
        group = [i for i in issues if i.level == level]
        if group:
            lines.append(f"  {name} {len(group)}")
            lines += [f"    - {i}" for i in group]
    verdict = "게시 불가 — 오류를 고친 뒤 다시 실행하세요" if errors else ("통과 (주의 항목은 직접 확인)" if warns else "통과")
    lines.append(f"  결과: 오류 {errors} · 주의 {warns} → {verdict}")
    return "\n".join(lines)


# ---------------------------------------------------------------- CLI

def add_arguments(parser) -> None:
    parser.add_argument("post", nargs="?", help="게시물 id 일부, 폴더 또는 post.yaml 경로")
    parser.add_argument("--all", action="store_true", help="content/posts 의 모든 게시물 검수")


def _load_for_check(folder: Path) -> tuple[Post | None, str | None]:
    try:
        return resolve_post(folder), None
    except yaml.YAMLError as e:
        return None, f"post.yaml 문법 오류: {e}"


def run(args) -> int:
    if not args.all and not args.post:
        print("검수할 게시물을 지정하세요: python doha.py check <게시물> 또는 --all")
        return 2
    config = load_config()
    persona = load_persona(config)
    if args.all:
        folders = sorted(d for d in posts_root(config).iterdir() if (d / "post.yaml").exists())
    else:
        try:
            folders = [resolve_post(args.post).dir]
        except yaml.YAMLError as e:
            print(f"post.yaml 문법 오류: {e}")
            return 1
    if not folders:
        print("검수할 게시물이 없어요.")
        return 0
    total_err = total_warn = 0
    for i, folder in enumerate(folders):
        if i:
            print()
        post, err = _load_for_check(folder)
        if post is None:
            print(f"검수: {folder.name}\n  오류 1\n    - [meta.yaml] post.yaml — {err}")
            total_err += 1
            continue
        issues = check_post(post, persona, config)
        e, w = counts(issues)
        total_err, total_warn = total_err + e, total_warn + w
        print(format_report(post.id, issues))
    if len(folders) > 1:
        print(f"\n전체 {len(folders)}개 게시물: 오류 {total_err} · 주의 {total_warn}")
    return 1 if total_err else 0
