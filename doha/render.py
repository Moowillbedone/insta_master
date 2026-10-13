"""카드뉴스 렌더러: post.yaml 의 slides → <post>/out/slides/01.png …

레이아웃마다 templates/carousel/<layout>.html 하나 (cover·look·tip·compare·checklist·product·cta).
사진 파일이 아직 없으면 자리표시 이미지를 그려서, 사진 없이도 배치를 검토할 수 있게 한다.
글자가 넘치면 템플릿 안의 스크립트가 글자 크기를 단계적으로 줄이고, 그래도 넘치면 경고를 낸다.

슬라이드에 쓸 수 있는 선택 필드 (SCHEMA 외):
  focus: "50% 30%"            사진 자르는 기준점 (object-position). 숫자 하나면 세로 위치
  tone: light | dark          사진 위 글자 색 강제 (기본은 사진 밝기로 자동)
  text_position: top | bottom cover 제목 위치 (기본 top — 사진 위쪽 1/3을 비워 두는 촬영 규칙)
  badge_position: left | center | right   'AI 가상인물' 배지 위치 — 인물이 한쪽에 치우친 사진이면 인물 쪽으로
                                          (compare 는 left/right 칸마다 따로 적을 수 있음)
  title (compare), note (checklist)

광고·협찬·제휴 게시물은 1번 슬라이드가 cover 가 아니어도 상단 바에 표시(예: '광고 · 브랜드')를 붙인다.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from doha.core import (
    Post,
    has_person,
    launch_browser,
    load_config,
    load_persona,
    resolve_post,
    short_disclosure_label,
    skip_if_legacy,
)

if TYPE_CHECKING:
    from markupsafe import Markup

LAYOUTS = ("cover", "look", "tip", "compare", "checklist", "product", "cta")
SIZES = {"3x4": "carousel", "4x5": "carousel_fallback"}

# 사진 영역이 캔버스 높이에서 차지하는 비율. 템플릿 CSS와 밝기 계산이 같은 값을 쓴다.
PHOTO_FRAC = {"look": 0.68, "checklist": 0.40, "product": 0.54, "cta": 0.46}
BADGE_POSITIONS = ("left", "center", "right")
# 프레이밍별 기본 자르기 기준점: 세로 2:3 원본을 가로로 넓은 칸에 넣을 때 얼굴·상체가 남도록
DEFAULT_FOCUS = {"full-body": "50% 38%", "three-quarter": "50% 22%", "waist-up": "50% 25%"}


# ---------------------------------------------------------------- 도우미

def _canvas(canvas, config: dict) -> dict:
    """canvas 인자: None | '3x4' | '4x5' | {'width','height'} | (w, h)."""
    if canvas is None:
        canvas = "3x4"
    if isinstance(canvas, str):
        if canvas not in SIZES:
            raise SystemExit(f"--size 는 {', '.join(SIZES)} 중 하나예요: {canvas}")
        canvas = config["canvas"][SIZES[canvas]]
    if isinstance(canvas, (tuple, list)):
        canvas = {"width": canvas[0], "height": canvas[1]}
    return {"width": int(canvas["width"]), "height": int(canvas["height"])}


def _parse_only(text: str | None, total: int) -> set[int] | None:
    if not text:
        return None
    picked: set[int] = set()
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        m = re.fullmatch(r"(\d+)\s*-\s*(\d+)", part)
        if m:
            picked.update(range(int(m.group(1)), int(m.group(2)) + 1))
        elif part.isdigit():
            picked.add(int(part))
        else:
            raise SystemExit(f"--only 형식이 잘못됐어요: '{part}' (예: 1,3 또는 2-4)")
    bad = sorted(n for n in picked if not 1 <= n <= total)
    if bad:
        raise SystemExit(f"슬라이드 번호 범위를 벗어났어요: {bad} (전체 {total}장)")
    return picked


def _focus(value, framing: str = "") -> str:
    if value is None or value == "":
        return DEFAULT_FOCUS.get(framing, "50% 50%")
    if isinstance(value, (int, float)):
        return f"50% {value}%"
    value = str(value).strip()
    if re.fullmatch(r"\d+(\.\d+)?%?", value):
        return f"50% {value.rstrip('%')}%"
    return value


def _focus_frac(pos: str) -> tuple[float, float]:
    nums = re.findall(r"(-?\d+(?:\.\d+)?)%", pos)
    if len(nums) >= 2:
        return float(nums[0]) / 100, float(nums[1]) / 100
    return 0.5, 0.5


def _excerpt(text: str, n: int = 60) -> str:
    text = " ".join(str(text or "").split())
    if len(text) <= n:
        return text
    cut = text[:n]
    if " " in cut[n // 2:]:   # 단어 중간에서 자르지 않는다
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip(" ,.;") + "…"


def _smart_quotes(text: str) -> str:
    out = []
    for i, ch in enumerate(text):
        if ch in "'\"":
            opening = i == 0 or text[i - 1].isspace() or text[i - 1] in "([{“‘·"
            ch = ("‘" if opening else "’") if ch == "'" else ("“" if opening else "”")
        out.append(ch)
    return "".join(out)


def rich(value) -> "Markup":
    """슬라이드 문구 → HTML: 곧은 따옴표를 둥근 따옴표로, 짧은 인용구는 줄바꿈 금지, \\n 은 <br>."""
    from markupsafe import Markup, escape

    text = _smart_quotes(str(value or ""))
    lines = []
    for line in text.split("\n"):
        html = str(escape(line))
        html = re.sub(r"([‘“][^’”<]{1,14}[’”]\S*)", r'<span class="nobr">\1</span>', html)
        lines.append(html)
    return Markup("<br>".join(lines))


def _photo(post: Post, key: str | None, focus=None) -> dict | None:
    if not key:
        return None
    from doha.htmlrender import file_uri

    spec = post.image_spec(key)
    if not spec:
        print(f"  ! images 에 '{key}' 가 없어요 — 자리표시로 그립니다", file=sys.stderr)
    path = post.image_path(key)
    framing = str(spec.get("framing") or "").strip()
    pos = _focus(focus, framing)
    return {
        "key": key,
        "path": path,
        "src": file_uri(path) if path else None,
        "framing": framing or "photo",
        # flatlay 가 아니면 인물로 간주 (detail 도 도하의 손·허리). 제품만 찍었으면 images.<키>.person: false
        "person": has_person(spec),
        "excerpt": _excerpt(spec.get("prompt")),
        "pos": pos,
    }


def _tone(photo: dict | None, box: tuple[float, float], regions: list[tuple[float, float, float, float]],
          forced: str | None = None) -> str:
    """사진 위 글자 자리의 밝기 → 'light'(밝은 배경 → 진한 글자) | 'dark'(어두운 배경 → 흰 글자).

    regions 는 사진 칸 안의 글자 상자들 (px). object-fit: cover 로 잘린 뒤 보이는 부분 기준.
    자리표시 이미지는 밝은 톤.
    """
    if forced in ("light", "dark"):
        return forced
    if not photo or not photo.get("path"):
        return "light"
    from PIL import Image, ImageStat

    bw, bh = box
    with Image.open(photo["path"]) as im:
        im = im.convert("L")
        iw, ih = im.size
        scale = max(bw / iw, bh / ih)
        fx, fy = _focus_frac(photo["pos"])
        ox, oy = (iw * scale - bw) * fx, (ih * scale - bh) * fy   # 잘려 나간 왼쪽·위 (화면 px)
        stats = []
        for x0, y0, x1, y1 in regions:
            crop = tuple(int(v) for v in ((x0 + ox) / scale, (y0 + oy) / scale, (x1 + ox) / scale, (y1 + oy) / scale))
            st = ImageStat.Stat(im.crop(crop).resize((64, 32)))
            stats.append((st.mean[0], st.stddev[0]))
    # 모든 글자 자리가 밝고 고를 때만 진한 글자. 애매하면 어두운 스크림 + 흰 글자가 더 안전하다.
    return "light" if all(m > 160 and sd < 64 for m, sd in stats) else "dark"


def _bar_regions(canvas: dict) -> list[tuple[float, float, float, float]]:
    """상단 바(워드마크·쪽번호)가 놓이는 자리 (px)."""
    w = canvas["width"]
    y0, y1 = 60, 128
    return [(70, y0, w * 0.42, y1), (w * 0.58, y0, w - 70, y1)]


def _label_parts(label: str) -> tuple[str, str]:
    """'LOOK 01 · 월요일' → ('LOOK 01', '월요일'). 영문 부분은 Cormorant, 한글은 Pretendard."""
    parts = [p.strip() for p in re.split(r"\s*[·|]\s*", str(label or ""), maxsplit=1)]
    return (parts[0], parts[1] if len(parts) > 1 else "")


def _split_label(body: str) -> tuple[str, str]:
    """'다음 편: 베이지 트렌치…' → ('다음 편', '베이지 트렌치…'). 시각('금요일 07:40')의 쌍점에서는 나누지 않는다."""
    m = re.match(r"^\s*([^:：]{1,8}?)\s*(?:(?<!\d)[:：]|[:：](?!\d))\s*(.+)$", str(body or ""), re.S)
    return (m.group(1), m.group(2).strip()) if m else ("", str(body or ""))


def _text_list(slide: dict, key: str) -> list[str]:
    """items · checks · bullets → 글자 목록. 목록이 아니면 멈춘다 (글자를 그대로 돌면 한 글자씩 항목이 된다)."""
    value = slide.get(key)
    if not value:
        return []
    if not isinstance(value, list):
        raise SystemExit(f"{slide.get('layout')} 슬라이드의 {key} 는 목록이어야 해요 (예: {key}: [\"…\", \"…\"]). "
                         f"지금: {str(value)[:30]!r} — python doha.py check 로 확인하세요")
    return [str(x) for x in value if x is not None]


def _is_latin(text: str) -> bool:
    return bool(text) and all(ord(ch) < 0x2000 for ch in str(text))


def _badge_pos(value) -> str:
    return value if value in BADGE_POSITIONS else "left"


def _short_footer(text: str, n: int = 44) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[:n].rstrip(" ,.") + "…"


# ---------------------------------------------------------------- 레이아웃별 문맥

def _ctx_cover(post, slide, canvas, persona):
    photo = _photo(post, slide.get("image"), slide.get("focus"))
    box = (canvas["width"], canvas["height"])
    position = slide.get("text_position") or "top"
    w, h = box
    text_region = (70, h * 0.12, w * 0.9, h * 0.46) if position == "top" else (70, h * 0.5, w * 0.9, h - 150)
    foot_region = (70, h - 150, w - 70, h - 60)
    forced = slide.get("tone")
    tone_text = _tone(photo, box, [text_region], forced)
    tone_top = tone_text if position == "top" else _tone(photo, box, _bar_regions(canvas), forced)
    tone_bottom = tone_text if position == "bottom" else _tone(photo, box, [foot_region], forced)
    return {
        "photo": photo,
        "position": position,
        "tone_text": tone_text,
        "tone_top": tone_top,
        "tone_bottom": tone_bottom,
        "pill": short_disclosure_label(post.data, persona),
        "kicker": slide.get("kicker") or post.data.get("series") or "",
        "title": slide.get("title") or post.data.get("hook") or "",
        "subtitle": slide.get("subtitle") or "",
    }


def _ctx_look(post, slide, canvas, persona):
    photo = _photo(post, slide.get("image"), slide.get("focus"))
    box = (canvas["width"], canvas["height"] * PHOTO_FRAC["look"])
    en, ko = _label_parts(slide.get("label") or "")
    return {
        "photo": photo,
        "tone_top": _tone(photo, box, _bar_regions(canvas), slide.get("tone")),
        "label_en": en,
        "label_ko": ko,
        "title": slide.get("title") or "",
        "items": _text_list(slide, "items"),
        "tip": slide.get("tip") or "",
    }


def _ctx_tip(post, slide, canvas, persona):
    number = str(slide.get("number") or "TIP")
    return {
        "photo": _photo(post, slide.get("image"), slide.get("focus")),
        "number": number,
        "number_latin": _is_latin(number),
        "title": slide.get("title") or "",
        "body": slide.get("body") or "",
        "bullets": _text_list(slide, "bullets"),
    }


def _ctx_compare(post, slide, canvas, persona):
    sides = []
    for name in ("left", "right"):
        side = slide.get(name) or {}
        if not isinstance(side, dict):
            raise SystemExit(f"compare 슬라이드의 {name} 는 {{image, label, caption}} 형식이어야 해요 "
                             f"(예: {name}: {{ image: s03, label: \"A\", caption: \"…\" }}). 지금: {side!r}")
        sides.append({
            "photo": _photo(post, side.get("image"), side.get("focus")),
            "label": side.get("label") or ("A" if name == "left" else "B"),
            "caption": side.get("caption") or "",
            # 칸마다 배지 위치 (없으면 슬라이드의 badge_position)
            "badge_pos": _badge_pos(side.get("badge_position") or slide.get("badge_position")),
        })
    return {"sides": sides, "title": slide.get("title") or "", "verdict": slide.get("verdict") or ""}


def _ctx_checklist(post, slide, canvas, persona):
    photo = _photo(post, slide.get("image"), slide.get("focus") or "50% 50%")
    box = (canvas["width"], canvas["height"] * PHOTO_FRAC["checklist"])
    return {
        "photo": photo,
        "tone_top": _tone(photo, box, _bar_regions(canvas), slide.get("tone")) if photo else "light",
        "title": slide.get("title") or "",
        "checks": _text_list(slide, "checks"),
        "note": slide.get("note") or "저장해두고 출근 전에 하나씩 확인하세요",
    }


def _ctx_product(post, slide, canvas, persona):
    pid = slide.get("product")
    products = {str(p.get("id")): p for p in post.data.get("products") or []}
    product = products.get(str(pid))
    if not product:
        raise SystemExit(f"product 슬라이드가 가리키는 상품 '{pid}' 가 products 에 없어요")
    photo = _photo(post, slide.get("image"), slide.get("focus") or "50% 50%")
    box = (canvas["width"], canvas["height"] * PHOTO_FRAC["product"])
    price = product.get("price_krw")
    checked = product.get("checked_at")
    if product.get("source_url") and checked:
        source = f"출처: 공식 상세페이지 ({checked} 확인)"
    else:
        source = "출처·확인일 미기재 — 게시 전 공식 페이지에서 확인하세요"
    return {
        "photo": photo,
        "tone_top": _tone(photo, box, _bar_regions(canvas), slide.get("tone")) if photo else "light",
        "pill": short_disclosure_label(post.data, persona),
        "brand": product.get("brand") or "",
        "name": product.get("name") or "",
        "price": f"{int(price):,}" if isinstance(price, (int, float)) else (str(price) if price else ""),
        "facts": [str(x) for x in product.get("facts") or []],
        "source": source,
        # 사진을 브랜드가 직접 준 경우(images.<키>.source: brand)만 AI 합성 안내를 뺀다
        "image_note": "" if photo and str(post.image_spec(photo["key"]).get("source", "")).lower() == "brand"
        else (persona.get("disclosure") or {}).get("product_image_note", ""),
    }


def _ctx_cta(post, slide, canvas, persona):
    photo = _photo(post, slide.get("image"), slide.get("focus"))
    box = (canvas["width"], canvas["height"] * PHOTO_FRAC["cta"])
    label, text = _split_label(slide.get("body") or "")
    return {
        "photo": photo,
        "tone_top": _tone(photo, box, _bar_regions(canvas), slide.get("tone")) if photo else "dark",
        "title": slide.get("title") or "",
        "next_label": label,
        "next_text": text,
        "follow": slide.get("follow") or None,
    }


# ---------------------------------------------------------------- 렌더링

def slide_html(post: Post, index: int, canvas=None, config: dict | None = None,
               persona: dict | None = None) -> str:
    """슬라이드 한 장(1부터)의 HTML. 미리보기·디버깅용으로도 쓴다."""
    from doha.htmlrender import jinja_env

    config = config or load_config()
    persona = persona or load_persona(config)
    canvas = _canvas(canvas, config)
    slides = post.data.get("slides") or []
    slide = slides[index - 1] or {}
    layout = slide.get("layout")
    if layout not in LAYOUTS:
        raise SystemExit(f"슬라이드 {index}: 알 수 없는 layout '{layout}' (가능: {', '.join(LAYOUTS)})")
    lay = persona.get("layout") or {}
    palette = (persona.get("visual") or {}).get("palette", {}).get("brand") or []
    handle = (config.get("account") or {}).get("handle") or persona.get("handle", "")
    disclosure = persona.get("disclosure") or {}
    ctx = {
        "layout": layout,
        "canvas": canvas,
        "colors": lay.get("colors") or {},
        "palette": palette,
        "photo_frac": PHOTO_FRAC,
        "c": {
            "num": f"{index:02d}",
            "total": f"{len(slides):02d}",
            "wordmark": (persona.get("typography") or {}).get("wordmark_text") or "DOHA DAILYFIT",
            "handle": f"@{handle}",
        },
        "ai_badge": disclosure.get("slide_badge") or "AI 가상 인물",
        "ai_footer": _short_footer(disclosure.get("caption_footer") or ""),
        "slide": slide,
        "badge_pos": _badge_pos(slide.get("badge_position")),
        "pill": "",
    }
    ctx.update(globals()[f"_ctx_{layout}"](post, slide, canvas, persona))
    if index == 1 and not ctx["pill"]:
        # 이미지 안 광고 표시는 첫 장에 반드시 (cover 가 아닌 레이아웃으로 시작해도)
        ctx["pill"] = short_disclosure_label(post.data, persona)
    env = jinja_env()
    env.filters["rich"] = rich
    return env.get_template(f"carousel/{layout}.html").render(ctx)


def _shoot(pages: list[tuple[str, Path]], width: int, height: int) -> dict[Path, list[str]]:
    """HTML → PNG. 템플릿의 글자 맞춤 스크립트가 끝난 뒤 찍고, 남은 넘침 경고를 돌려준다."""
    from playwright.sync_api import sync_playwright

    issues: dict[Path, list[str]] = {}
    with sync_playwright() as p:
        browser = launch_browser(p)
        page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
        for html, out in pages:
            out.parent.mkdir(parents=True, exist_ok=True)
            # file:// 폰트·사진을 읽으려면 파일로 열어야 한다
            tmp = out.with_name(f".{out.stem}.render.html")
            tmp.write_text(html, encoding="utf-8")
            try:
                page.goto(tmp.resolve().as_uri(), wait_until="load")
                page.wait_for_function("window.__fit && window.__fit.done", timeout=20000)
                found = page.evaluate("window.__fit.issues")
                page.screenshot(path=str(out), full_page=False)
            finally:
                tmp.unlink(missing_ok=True)
            if found:
                issues[out] = list(found)
        browser.close()
    return issues


def render_post(post, canvas=None, only: set[int] | None = None) -> list[Path]:
    """게시물의 카드뉴스를 PNG로. post 는 Post 또는 게시물 경로/id. 만든 파일 경로 목록을 돌려준다."""
    if not isinstance(post, Post):
        post = resolve_post(post)
    config = load_config()
    persona = load_persona(config)
    size = _canvas(canvas, config)
    slides = post.data.get("slides") or []
    if not slides:
        # 릴스 전용 게시물 등: build 가 포맷과 상관없이 불러도 멈추지 않게 빈 목록
        print(f"  · 카드뉴스 슬라이드가 없어요 (format: {post.data.get('format', '?')}) — 건너뜀", file=sys.stderr)
        return []
    out_dir = post.out_dir / "slides"
    pages = []
    for i in range(1, len(slides) + 1):
        if only and i not in only:
            continue
        pages.append((slide_html(post, i, size, config, persona), out_dir / f"{i:02d}.png"))

    issues = _shoot(pages, size["width"], size["height"])
    if not only:
        # 슬라이드 수가 줄었을 때 예전 PNG가 연락시트에 섞이지 않게 정리
        keep = {out for _, out in pages}
        for old in out_dir.glob("[0-9][0-9].png"):
            if old not in keep:
                old.unlink()
    for out, found in issues.items():
        for msg in found:
            print(f"  ! {out.name}: {msg}", file=sys.stderr)
    missing = sorted({k for k, spec in (post.data.get("images") or {}).items() if not post.image_path(k)})
    if missing:
        print(f"  · 사진 없음 → 자리표시로 렌더링: {', '.join(missing)}", file=sys.stderr)
    return [out for _, out in pages]


# ---------------------------------------------------------------- CLI

def add_arguments(parser) -> None:
    parser.add_argument("post", help="게시물 폴더 경로 또는 id 일부 (예: black-slacks)")
    parser.add_argument("--size", choices=sorted(SIZES), default="3x4",
                        help="3x4 = 1080x1440 (기본), 4x5 = 1080x1350 (앱에서 잘릴 때)")
    parser.add_argument("--only", help="일부 슬라이드만 (예: 1,3 또는 2-4)")


def run(args) -> int:
    post = resolve_post(args.post)
    if skip_if_legacy(post):
        return 0
    only = _parse_only(args.only, len(post.data.get("slides") or []))
    size = _canvas(args.size, load_config())
    print(f"카드뉴스 렌더링: {post.id} ({size['width']}x{size['height']})")
    outs = render_post(post, args.size, only=only)
    for out in outs:
        try:
            print(out.relative_to(Path.cwd()))
        except ValueError:
            print(out)
    return 0
