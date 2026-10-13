"""브랜드 제안용 미디어킷: out/media-kit/media-kit.html · media-kit.pdf · onepager.png

  python doha.py media-kit              # HTML + PDF(A4 6쪽) + DM용 한 장 요약(1080x1350)
  python doha.py media-kit --no-pdf     # PDF 생략

숫자는 tracking/metrics.csv · followers.csv 의 실제 기록에서만 계산한다.
게시 후 7일(7d) 지표가 3건 미만이면 성과 페이지는 '데이터 수집 중'으로 나가고 숫자를 싣지 않는다.

선택: config.yaml 의 account.contact_email / account.contact_note
  없으면 "문의: Instagram DM @핸들" 로 표시.

선택: brand/rates.yaml — 있으면 5쪽 협업 메뉴에 '시작가'를 싣는다. 없으면 가격 없이 견적 구성만.
  valid_until: 2026-12-31          # 선택. 지나면 가격을 싣지 않고 경고만 (오래된 단가가 나가지 않게)
  note: "부가세 별도"               # 선택. 견적 구성 아래 작은 글씨
  rates:                            # 키: feed | reel | story | production | license | partnership_ads
    feed:       { from_krw: 300000, unit: "카드뉴스 1건" }       # 숫자는 형식 예시일 뿐 — 실제 단가로
    production: { from_krw: 500000, unit: "AI 룩북 컷 5장" }
    license:    { text: "기본 단가의 +20~50%", unit: "3개월 · 자사몰" }
  항목마다 from_krw(정수, '~부터'로 표시) 또는 text 중 하나. unit · note 는 선택.
"""
from __future__ import annotations

import base64
import io
import re
import statistics
from datetime import date, datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

from doha.core import (
    ROOT,
    Post,
    disclosure_label,
    list_posts,
    load_config,
    load_persona,
    load_yaml,
    read_csv,
    short_disclosure_label,
)

CHECKPOINT = "7d"
MIN_POSTS = 3          # 이보다 적으면 비율·중앙값이 우연에 크게 흔들려서 싣지 않는다
CHART_MAX_BARS = 16
SAMPLE_COUNT = 6
NON_PERSON_FRAMINGS = {"flatlay", "detail"}
last_warnings: list[str] = []   # 마지막 build_media_kit 의 터미널 안내 (PDF에는 싣지 않음)
FORMAT_KO = {"carousel": "카드뉴스", "reel": "릴스"}

# HTML 파일에 넣을 글꼴 (CSS에서 실제로 쓰는 굵기만 — 전부 넣으면 10MB를 넘는다)
EMBED_FACES = {
    ("Pretendard", 400), ("Pretendard", 500), ("Pretendard", 600),
    ("Noto Serif KR", 500), ("Noto Serif KR", 700),
    ("Cormorant Garamond", 500), ("Cormorant Garamond", 600),
}

PILLAR_DESC = {
    "돌려입기": "한 벌을 여러 날·상황에 나눠 입는 조합",
    "컬러공식": "상·하의 색 조합을 공식으로 정리",
    "비율": "넣어 입기·기장으로 비율 정리",
    "상황별": "날씨·회의·일정에 맞춘 주간 출근룩",
    "아이템가이드": "아이템 하나를 고르고 쓰는 법",
}
NON_EDITORIAL_PILLARS = {"협찬", "제휴"}

DELIVERABLES = [
    {"key": "feed", "short": "피드 카드뉴스", "en": "Feed Carousel", "ko": "피드 카드뉴스",
     "items": ["도하 계정 게시 · 실사형 AI 화보와 코디 설명",
               "캡션·해시태그 작성, 광고 표시와 유료 파트너십 라벨",
               "장수와 구성은 브리프에서 확정"]},
    {"key": "reel", "short": "릴스", "en": "Reels", "ko": "릴스",
     "items": ["9:16 세로 영상, 장면 구성과 자막",
               "커버 이미지 포함 · 첫 장면에 광고 표시",
               "음원은 사용권이 확인된 것만 사용"]},
    {"key": "story", "short": "스토리", "en": "Stories", "ko": "스토리",
     "items": ["게시물 공유 또는 단독 스토리",
               "링크 스티커로 브랜드 페이지 연결",
               "하이라이트 보관 여부 협의"]},
    {"key": "production", "short": "브랜드 계정용 제작", "en": "Content Only", "ko": "제작 전용 (브랜드 계정 게시)",
     "items": ["도하 계정 게시 없이 브랜드 채널용으로 제작",
               "AI 룩북 컷 · 카드뉴스 · 릴스 원본 납품",
               "실물 사진·실측 기준 생성, 브랜드 승인 후 사용"]},
    {"key": "license", "short": "광고 소재 사용권", "en": "Usage Rights", "ko": "광고 소재 사용권",
     "items": ["자사몰 · 상세페이지 · SNS · 광고 중 매체 선택",
               "기간을 정한 이용 허락, 종료 후 게시 중단",
               "원본과 캐릭터 권리는 운영자 보유"]},
    {"key": "partnership_ads", "short": "파트너십 광고 권한", "en": "Partnership Ads", "ko": "파트너십 광고 권한",
     "items": ["메타 파트너십 광고 코드 또는 권한 부여",
               "집행 기간과 광고비 상한을 계약서에 명시",
               "계정 비밀번호는 공유하지 않음"]},
]

QUOTE_PARTS = [
    ("게시비", "도하 계정 노출", "게시물 1건 단위"),
    ("제작비", "기획 · 생성 · 편집 · 검수", "컷 수 · 장수 · 초"),
    ("사용권", "브랜드 채널 2차 활용", "기간 × 매체"),
    ("수정 횟수", "포함 횟수를 견적서에 명시", "초과 시 회당 추가"),
    ("독점", "동종 카테고리 협업 제한", "선택 · 기간 단위"),
]

PROCESS = [
    ("Brief", "브리프", "제품 정보·실물 사진·실측, 목표와 일정, 표시 의무를 확인해요"),
    ("Draft", "시안", "대표 컷 1장으로 제품 재현을 먼저 확인한 뒤 전체를 만들어요"),
    ("Revise", "수정", "합의한 범위 안에서 고치고, 표시 문구는 브랜드가 승인해요"),
    ("Publish", "게시", "광고 표시를 다시 확인하고 약속한 일정에 게시·납품해요"),
    ("Report", "리포트", "게시 24시간 · 7일 지표를 인사이트 화면 기준으로 전달해요"),
]

REPORT_METRICS = ["도달", "조회", "좋아요 · 댓글", "저장 · 공유", "프로필 방문 · 팔로우", "링크 클릭", "릴스 평균 시청 시간"]


# ---------------------------------------------------------------- 작은 도우미

def _num(value) -> float | None:
    s = str(value if value is not None else "").strip().replace(",", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _as_date(value) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value or "").strip()[:10])
    except ValueError:
        return None


def _fmt_int(n: float | None) -> str:
    return "—" if n is None else f"{round(n):,}"


def _fmt_pct(r: float | None) -> str:
    if r is None:
        return "—"
    pct = r * 100
    return f"{pct:.2f}%" if 0 < pct < 0.1 else f"{pct:.1f}%"


def _dot(d: date | None, year: bool = True) -> str:
    if not d:
        return ""
    return f"{d.year}.{d.month:02d}.{d.day:02d}" if year else f"{d.month:02d}.{d.day:02d}"


def _topic(name: str) -> str:
    """이름 + 은/는 (받침 여부)."""
    code = ord(name[-1]) - 0xAC00 if name else -1
    return name + ("은" if 0 <= code < 11172 and code % 28 else "는")


def _smart(text: str) -> str:
    """곧은 따옴표 → 둥근 따옴표 (인쇄물에서 곧은 따옴표는 덜 다듬어 보인다)."""
    text = re.sub(r'"([^"]+)"', "\u201c\\1\u201d", str(text or ""))
    return re.sub(r"'([^']+)'", "\u2018\\1\u2019", text)


def _title(text: str) -> str:
    """제목용: 둥근 따옴표 + '월~금' 같은 범위 표시가 줄 끝에서 갈라지지 않게."""
    return re.sub(r"(?<=\S)~(?=\S)", "\u2060~\u2060", _smart(text))


def _nice_ceil(x: float) -> float:
    if x <= 0:
        return 1
    mag = 10 ** (len(str(int(x))) - 1)
    for step in (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if step * mag >= x:
            return step * mag
    return 10 * mag


def _compact(n: float) -> str:
    """축 눈금: 1만 미만은 쉼표 숫자, 그 위는 '1.5만'."""
    if n >= 10000:
        return f"{n / 10000:.2f}".rstrip("0").rstrip(".") + "만"
    return f"{round(n):,}"


_thumb_cache: dict[tuple[Path, int], str] = {}


def _thumb(path: Path, width: int = 640) -> str:
    """미디어킷용으로 줄인 JPEG data URI. 원본 PNG를 그대로 넣으면 파일이 수십 MB가 된다."""
    from PIL import Image

    key = (path, width)
    if key not in _thumb_cache:
        with Image.open(path) as im:
            im = im.convert("RGB")
            if im.width > width:
                im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=86, optimize=True, progressive=True)
        _thumb_cache[key] = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    return _thumb_cache[key]


def _post_date(post: Post | None) -> date | None:
    if not post:
        return None
    posted = post.data.get("posted") or {}
    return _as_date(posted.get("posted_at")) or _as_date(post.data.get("date"))


def _is_posted(post: Post) -> bool:
    posted = post.data.get("posted") or {}
    return bool(posted.get("url") or posted.get("reel_url") or post.data.get("status") == "posted")


def _render_path(post: Post, fmt: str | None = None) -> Path | None:
    """대표 썸네일: 카드뉴스 첫 장, 릴스면 커버 우선."""
    slide = post.out_dir / "slides" / "01.png"
    cover = post.out_dir / "reel" / "cover.png"
    reel_first = fmt == "reel" or (fmt is None and post.data.get("format") == "reel")
    return next((p for p in ((cover, slide) if reel_first else (slide, cover)) if p.exists()), None)


def _cover_photo_missing(post: Post) -> bool:
    """렌더된 커버가 사진 없이 자리표시로 그려졌는지 (사진 파일 유무로 판단)."""
    slides = post.data.get("slides") or []
    key = slides[0].get("image") if slides else None
    if post.data.get("format") == "reel" or not key:
        scenes = (post.data.get("reel") or {}).get("scenes") or []
        key = key or (scenes[0].get("image") if scenes else None)
    return bool(key) and post.image_path(key) is None


def _tile(post: Post | None, fmt: str | None = None, title: str = "", width: int = 640) -> dict:
    """썸네일 칸 하나: 렌더 이미지가 있으면 그것, 없으면 타이포 자리표시."""
    path = _render_path(post, fmt) if post else None
    series = (post.data.get("series") if post else "") or ""
    return {
        "uri": _thumb(path, width) if path else None,
        "kind": "reel" if path and path.name == "cover.png" else "slide",
        "title": _title(title or (post.data.get("hook") if post else "") or (post.id if post else "")),
        "series": series,
        "draft": bool(post) and bool(path) and _cover_photo_missing(post),
    }


# ---------------------------------------------------------------- 데이터

def collect_performance(data_dir: Path, posts: list[Post], today: date | None = None) -> dict:
    """metrics.csv(7d) + followers.csv → 성과 페이지 데이터. 기록이 없으면 None/빈 값으로 둔다."""
    today = today or date.today()
    by_id = {p.id: p for p in posts}

    units: dict[tuple[str, str], dict] = {}
    for r in read_csv(data_dir / "metrics.csv"):
        if (r.get("checkpoint") or "").strip() != CHECKPOINT:
            continue
        reach = _num(r.get("reach"))
        post_id = (r.get("post_id") or "").strip()
        if not post_id or not reach or reach <= 0:
            continue
        fmt = (r.get("format") or "").strip() or "carousel"
        key = (post_id, fmt)
        recorded = (r.get("recorded_at") or "").strip()
        if key in units and units[key]["recorded_raw"] > recorded:
            continue  # 같은 게시물을 두 번 기록했으면 나중 기록을 쓴다
        post = by_id.get(post_id)
        posted = _post_date(post) or _as_date(post_id[:10])  # post_id 는 보통 'YYYY-MM-DD-슬러그'
        units[key] = {
            "post_id": post_id, "format": fmt, "format_ko": FORMAT_KO.get(fmt, fmt),
            "post": post, "recorded_raw": recorded, "recorded": _as_date(recorded),
            "posted": posted,
            "reach": reach, "saves": _num(r.get("saves")), "shares": _num(r.get("shares")),
            "follows": _num(r.get("follows")),
            "title": (post.data.get("hook") if post else None) or post_id,
        }
    items = sorted(units.values(), key=lambda u: (u["posted"] or u["recorded"] or date.min, u["format"]))
    n = len(items)

    def rate(field: str) -> dict:
        pairs = [(u[field], u["reach"]) for u in items if u[field] is not None]
        if not pairs:
            return {"value": None, "text": "—", "n": 0}
        v = sum(a for a, _ in pairs) / sum(b for _, b in pairs)
        return {"value": v, "text": _fmt_pct(v), "n": len(pairs)}

    reaches = [u["reach"] for u in items]
    perf: dict = {"n": n, "min_posts": MIN_POSTS, "ready": n >= MIN_POSTS, "items": items}
    if items:
        posted_days = [u["posted"] or u["recorded"] for u in items if u["posted"] or u["recorded"]]
        recorded_days = [u["recorded"] for u in items if u["recorded"]]
        perf.update({
            "reach_median": _fmt_int(statistics.median(reaches)),
            "reach_mean": _fmt_int(statistics.fmean(reaches)),
            "save": rate("saves"), "share": rate("shares"), "follow": rate("follows"),
            "range_from": _dot(min(posted_days)) if posted_days else "",
            "range_to": _dot(max(posted_days)) if posted_days else "",
            "recorded_to": _dot(max(recorded_days)) if recorded_days else "",
        })
    # 저장률 상위 3개
    ranked = sorted((u for u in items if u["saves"] is not None),
                    key=lambda u: (u["saves"] / u["reach"], u["reach"]), reverse=True)[:3]
    perf["best"] = [{
        **_tile(u["post"], u["format"], u["title"], width=520),
        "format_ko": u["format_ko"], "date": _dot(u["posted"] or u["recorded"], year=False),
        "rank": i + 1,
        "save_rate": _fmt_pct(u["saves"] / u["reach"]), "reach": _fmt_int(u["reach"]),
        "saves": _fmt_int(u["saves"]),
    } for i, u in enumerate(ranked)]
    # 7일 도달 막대 (시간순, 최근 N개)
    shown = items[-CHART_MAX_BARS:]
    if shown:
        top = _nice_ceil(max(u["reach"] for u in shown))
        hi = max(range(len(shown)), key=lambda i: shown[i]["reach"])
        perf["chart"] = {
            "ticks": [{"pct": p * 100, "label": _compact(top * p)} for p in (0, 0.5, 1)],
            # 기준선은 위 KPI와 같은 전체 중앙값 (막대를 잘라도 숫자가 어긋나지 않게)
            "median_pct": min(statistics.median(reaches) / top, 1) * 100,
            "median_label": _fmt_int(statistics.median(reaches)),
            "bars": [{
                "pct": u["reach"] / top * 100,
                "date": _dot(u["posted"] or u["recorded"], year=False),
                "fmt": "릴스" if u["format"] == "reel" else "카드",
                "label": _fmt_int(u["reach"]) if i in (hi, len(shown) - 1) else "",
            } for i, u in enumerate(shown)],
            "truncated": len(items) > len(shown),
        }

    # 팔로워
    fol = []
    for r in read_csv(data_dir / "followers.csv"):
        d, v = _as_date(r.get("date")), _num(r.get("followers"))
        if d and v is not None:
            fol.append((d, v))
    fol.sort()
    perf["followers"] = None
    if fol:
        d_last, v_last = fol[-1]
        f = {"value": _fmt_int(v_last), "date": _dot(d_last), "date_short": _dot(d_last, year=False), "delta": None}
        d_first, v_first = fol[0]
        if d_first < d_last:
            diff = v_last - v_first
            f["delta"] = f"{'+' if diff >= 0 else '−'}{abs(round(diff)):,}"
            f["delta_since"] = _dot(d_first, year=False)
        perf["followers"] = f
    perf["as_of"] = _dot(today)
    return perf


def collect_pillars(posts: list[Post]) -> list[dict]:
    seen: dict[str, dict] = {}
    for p in posts:
        name = (p.data.get("pillar") or "").strip()
        if not name or name in NON_EDITORIAL_PILLARS:
            continue
        entry = seen.setdefault(name, {"name": name, "desc": PILLAR_DESC.get(name, ""), "series": []})
        series = (p.data.get("series") or "").strip()
        if series and series not in entry["series"]:
            entry["series"].append(series)
    if not seen:  # 게시물이 아직 없으면 기본 기둥
        return [{"name": k, "desc": v, "series": []} for k, v in PILLAR_DESC.items()]
    return list(seen.values())[:5]


def collect_samples(posts: list[Post], today: date) -> list[dict]:
    """게시된 것 → 렌더된 것 → 최근 순으로 고르되, 기둥이 겹치지 않게 먼저 한 바퀴 돈다."""
    def rank(p: Post):
        return (_is_posted(p), _render_path(p) is not None, _post_date(p) or date.min)

    pool = sorted(posts, key=rank, reverse=True)
    picked: list[Post] = []
    used_pillars: set[str] = set()
    for p in pool:
        if len(picked) >= SAMPLE_COUNT:
            break
        pillar = p.data.get("pillar") or ""
        if pillar not in used_pillars and (_render_path(p) or not any(_render_path(q) for q in pool)):
            picked.append(p)
            used_pillars.add(pillar)
    for p in pool:
        if len(picked) >= SAMPLE_COUNT:
            break
        if p not in picked:
            picked.append(p)
    picked.sort(key=lambda p: _post_date(p) or date.min)

    out = []
    for p in picked:
        d = _post_date(p)
        if _is_posted(p):
            status = f"게시 {_dot(d, year=False)}"
        elif d and d >= today:
            status = f"공개 예정 {_dot(d, year=False)}"
        else:
            status = "미공개 시안"
        fmt = p.data.get("format", "carousel")
        out.append({**_tile(p), "pillar": p.data.get("pillar") or "", "status": status,
                    "format_ko": "카드뉴스 + 릴스" if fmt == "both" else FORMAT_KO.get(fmt, fmt)})
    return out


def find_hero(persona: dict, posts: list[Post]) -> Path | None:
    """표지 사진: 승인된 얼굴 기준 이미지 → 승인된 게시물 인물 사진. 없으면 None (표지는 썸네일 띠)."""
    for ref in (persona.get("visual") or {}).get("face_reference") or []:
        p = ROOT / ref
        if p.exists():
            return p
    for post in sorted(posts, key=lambda p: _post_date(p) or date.min, reverse=True):
        for key, spec in (post.data.get("images") or {}).items():
            if (spec or {}).get("status") == "approved" and spec.get("framing") not in NON_PERSON_FRAMINGS:
                if path := post.image_path(key):
                    return path
    return None


def load_rates(config: dict, today: date) -> tuple[dict | None, list[str]]:
    path = (ROOT / config["paths"]["persona"]).parent / "rates.yaml"
    if not path.exists():
        return None, []
    data = load_yaml(path) or {}
    valid = _as_date(data.get("valid_until"))
    if data.get("valid_until") and not valid:
        return None, [f"{path.name}: valid_until 날짜 형식이 잘못돼 가격을 싣지 않았어요 (예: 2026-12-31)"]
    if valid and valid < today:
        return None, [f"{path.name}: 유효기간({valid})이 지나 가격을 싣지 않았어요. 단가를 확인하고 valid_until 을 고치세요"]
    keys = {d["key"] for d in DELIVERABLES}
    rates, warnings = {}, []
    for key, spec in (data.get("rates") or {}).items():
        if key not in keys:
            warnings.append(f"{path.name}: 알 수 없는 항목 '{key}' (가능: {', '.join(sorted(keys))})")
            continue
        spec = spec or {}
        amount = _num(spec.get("from_krw"))
        text = f"₩{round(amount):,}~" if amount else str(spec.get("text") or "").strip()
        if not text:
            warnings.append(f"{path.name}: '{key}' 에 from_krw 나 text 가 없어요")
            continue
        rates[key] = {"text": text, "unit": str(spec.get("unit") or "").strip(),
                      "note": str(spec.get("note") or "").strip()}
    if not rates:
        return None, warnings
    return {"items": rates, "note": str(data.get("note") or "").strip(),
            "valid_until": _dot(valid) if valid else ""}, warnings


# ---------------------------------------------------------------- 조립

def build_context(data_dir: Path | None = None, today: date | None = None) -> tuple[dict, list[str]]:
    config = load_config()
    persona = load_persona(config)
    today = today or date.today()
    data_dir = Path(data_dir) if data_dir else ROOT / config["paths"]["tracking"]
    posts = list_posts()
    warnings: list[str] = []

    account = config.get("account") or {}
    handle = account.get("handle") or persona.get("handle")
    email = (account.get("contact_email") or "").strip()
    contact = {
        "email": email,
        "note": (account.get("contact_note") or "").strip(),
        "line": f"문의 · {email}" if email else f"문의: Instagram DM @{handle}",
    }
    name = persona.get("name", "도하")
    disc = persona.get("disclosure") or {}
    labels = disc.get("labels") or {}
    wordmark = ((persona.get("typography") or {}).get("wordmark_text") or "DOHA DAILYFIT").split()
    positioning = persona.get("positioning") or {}
    voice = persona.get("voice") or {}

    perf = collect_performance(data_dir, posts, today)
    samples = collect_samples(posts, today)
    hero = find_hero(persona, posts)
    rates, rate_warnings = load_rates(config, today)
    warnings += rate_warnings

    # 광고 게시물 예시 표시 — 렌더러와 같은 함수로 만든다
    example = {"disclosure": {"paid": True, "brand": "브랜드명"}}
    compliance = {
        "pill": short_disclosure_label(example, persona),
        "caption_first": f"[{disclosure_label(example, persona)}] {disc.get('ad_virtual_notice', '')}".strip(),
        "badge": disc.get("slide_badge", "AI 가상인물"),
        "gifted": labels.get("gifted", "협찬"),
        "affiliate": labels.get("affiliate", ""),
        "product_note": disc.get("product_image_note", ""),
    }

    rules = [r for r in voice.get("rules") or []]
    ctx = {
        "today": _dot(today), "year_month": f"{today.year} · {today.month:02d}",
        "colors": (persona.get("layout") or {}).get("colors") or {},
        "palette": ((persona.get("visual") or {}).get("palette") or {}).get("brand") or [],
        "doha_name": name, "name_topic": _topic(name), "name_en": persona.get("name_en", "DOHA"),
        "role": persona.get("role", "AI 가상 스타일리스트"),
        "display_name": account.get("display_name") or f"{name} | AI 스타일리스트",
        "handle": handle, "url": (account.get("url") or "").replace("https://", "").replace("www.", "").rstrip("/"),
        "wordmark_main": wordmark[0], "wordmark_sub": " ".join(wordmark[1:]),
        "one_liner": _smart(positioning.get("one_liner", "")),
        "audience": _smart(positioning.get("audience", "")),
        "promise": [_smart(x) for x in positioning.get("promise") or []],
        # 후기형은 표현을 바꿔 맨 앞에, 나머지는 페르소나의 '하지 않는 것' 그대로
        "declines": ["사용 후기·체험단형 캠페인"] + [_smart(x) for x in positioning.get("not_this") or []
                                                if "후기" not in x and "체험" not in x],
        "voice_register": _smart(voice.get("register", "")), "voice_rules": [_smart(r) for r in rules[:5]],
        "pillars": collect_pillars(posts),
        "transparency": [
            ("AI 표시", f"인물이 나오는 모든 장·장면에 '{compliance['badge']}' 표시. 프로필 소개 첫 줄에도 가상인물임을 밝혀요."),
            ("광고 표시", "광고·협찬·제휴는 캡션 첫 줄과 이미지 상단에 표시하고, 유료 파트너십 라벨을 함께 써요."),
            ("체험 지어내지 않음", "가상인물이라 '입어보니·써보니' 같은 사용 후기를 쓰지 않아요. 색·비율·소재로만 설명해요."),
            ("제품 정보", "가격·소재는 브랜드 공식 자료를 기준으로, 확인한 날짜와 함께 적어요."),
        ],
        "contact": contact, "perf": perf, "samples": samples,
        "hero": _thumb(hero, 1400) if hero else None,
        "cover_tiles": samples[:3],
        "deliverables": [{**d, "rate": (rates or {}).get("items", {}).get(d["key"])} for d in DELIVERABLES],
        "quote_parts": QUOTE_PARTS, "rates": rates,
        "process": PROCESS, "compliance": compliance, "report_metrics": REPORT_METRICS,
        "canvas": config.get("canvas") or {},
    }

    # 터미널 안내 (PDF에는 싣지 않는 내부 메모)
    if not perf["followers"]:
        warnings.append(f"팔로워 수 기록이 없어요 → {data_dir.name}/followers.csv 에 날짜와 숫자를 적으면 실려요")
    if not perf["ready"]:
        warnings.append(f"7일 지표가 {perf['n']}건이에요 ({MIN_POSTS}건부터 성과 페이지가 숫자로 채워져요)")
    drafts = [s["title"] for s in samples if s["draft"]]
    if drafts:
        warnings.append(f"샘플 {len(drafts)}개는 사진 없이 렌더된 레이아웃 시안이에요 ('레이아웃 시안'으로 표시됨). 사진 생성·렌더 후 다시 만드세요")
    missing = [s["title"] for s in samples if not s["uri"]]
    if missing:
        warnings.append(f"렌더된 이미지가 없는 샘플 {len(missing)}개는 글자 표지로 대신했어요 → python doha.py render <게시물>")
    return ctx, warnings


def _embed_fonts(html: str) -> str:
    """file:// 글꼴을 data URI로 바꿔 HTML 파일 하나만 보내도 같은 모양이 나오게 한다. 안 쓰는 굵기는 뺀다."""
    pattern = re.compile(r"@font-face\{font-family:'([^']+)';font-weight:(\d+);[^}]*?url\('(file://[^']+)'\)[^}]*\}")

    def repl(m: re.Match) -> str:
        if (m.group(1), int(m.group(2))) not in EMBED_FACES:
            return ""
        path = Path(unquote(urlparse(m.group(3)).path))
        if not path.exists():
            return m.group(0)
        uri = "data:font/woff2;base64," + base64.b64encode(path.read_bytes()).decode()
        return m.group(0).replace(m.group(3), uri)

    return pattern.sub(repl, html)


_OVERFLOW_JS = """() => [...document.querySelectorAll('.page')].map((page, i) => {
  const box = page.getBoundingClientRect();
  const limit = box.bottom - parseFloat(getComputedStyle(page).paddingBottom) + 1;
  const bottom = Math.max(...[...page.children].map(c => c.getBoundingClientRect().bottom));
  return bottom > limit ? [i + 1, Math.round(bottom - limit)] : null;
}).filter(Boolean)"""


def _layout_issues(html: str, out_dir: Path) -> list[str]:
    """인쇄 레이아웃에서 쪽 아래 여백을 넘친 쪽을 찾는다 (긴 페르소나 문구·단가 파일 등 데이터 탓)."""
    from playwright.sync_api import sync_playwright

    from doha.core import launch_browser

    tmp = out_dir / "media-kit.check.html"
    tmp.write_text(html, encoding="utf-8")
    try:
        with sync_playwright() as p:
            browser = launch_browser(p)
            page = browser.new_page(viewport={"width": 1000, "height": 1200})
            page.emulate_media(media="print")
            page.goto(tmp.resolve().as_uri(), wait_until="load")
            page.evaluate("document.fonts.ready")
            found = page.evaluate(_OVERFLOW_JS)
            browser.close()
    finally:
        tmp.unlink(missing_ok=True)
    return [f"{n}쪽 내용이 아래 여백을 {px}px 넘어요 — 해당 쪽 문구(페르소나·단가 파일)를 줄이세요" for n, px in found]


def build_media_kit(pdf: bool = True, data_dir: Path | str | None = None,
                    out_dir: Path | str | None = None) -> dict:
    """미디어킷 생성. 반환: {'html': Path, 'pdf': Path(pdf=True일 때), 'onepager': Path}.

    data_dir: 지표 CSV 폴더 (기본 config paths.tracking) — 테스트용 가짜 데이터를 가리킬 때 쓴다.
    out_dir: 출력 폴더 (기본 out/media-kit).
    """
    from doha.htmlrender import html_to_pdf, render_template, screenshot_pages

    ctx, warnings = build_context(Path(data_dir) if data_dir else None)
    out = Path(out_dir) if out_dir else ROOT / "out" / "media-kit"
    out.mkdir(parents=True, exist_ok=True)

    doc = render_template("media-kit/media-kit.html", **ctx)
    paths: dict = {}
    html_path = out / "media-kit.html"
    html_path.write_text(_embed_fonts(doc), encoding="utf-8")
    paths["html"] = html_path
    if pdf:
        paths["pdf"] = html_to_pdf(doc, out / "media-kit.pdf")
    warnings += _layout_issues(doc, out)
    one = render_template("media-kit/onepager.html", **ctx)
    paths["onepager"] = screenshot_pages([(one, out / "onepager.png")], 1080, 1350)[0]
    last_warnings[:] = warnings  # run()이 출력
    return paths


def add_arguments(parser) -> None:
    parser.add_argument("--no-pdf", action="store_true", help="PDF는 만들지 않기 (HTML·한 장 요약만)")
    parser.add_argument("--data-dir", help="지표 CSV 폴더 (기본 tracking/). 테스트 데이터 확인용")
    parser.add_argument("--out", help="출력 폴더 (기본 out/media-kit)")


def run(args) -> int:
    paths = build_media_kit(pdf=not args.no_pdf, data_dir=args.data_dir, out_dir=args.out)
    print("미디어킷을 만들었어요")
    for key in ("pdf", "html", "onepager"):
        if key in paths:
            p = paths[key]
            try:
                shown = p.relative_to(ROOT)
            except ValueError:
                shown = p
            print(f"  {key:<9}{shown}")
    for w in last_warnings:
        print(f"  · {w}")
    print("  보내기 전 확인: 숫자는 최신 인사이트와 같은지, 문의처가 맞는지 PDF를 열어 보세요")
    return 0
