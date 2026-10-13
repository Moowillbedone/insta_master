"""게시 전 미리보기 (preview): 붙여넣기용 캡션, 연락시트 PNG, 휴대폰 화면 미리보기 HTML.

  python doha.py preview black-slacks

만드는 파일 (게시물 폴더의 out/ 아래):
  caption.txt        앱에 그대로 붙여넣는 최종 캡션 (광고 표시 → 본문 → AI 안내 → 해시태그)
  contact-sheet.png  슬라이드·릴스 커버를 한 장에 모은 검수용 이미지
  preview.html       휴대폰 화면 모양 미리보기 (이미지는 data URI로 넣어 파일 하나로 열림)
"""
from __future__ import annotations

import base64
import os
import re
import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Callable

from doha.check import (
    CAPTION_LIMIT,
    FEED_LINE_UNITS,
    as_date,
    as_time,
    check_post,
    counts,
    format_report,
    post_format,
    reel_seconds,
    text_width,
)
from doha.core import (
    ROOT,
    Post,
    disclosure_label,
    load_config,
    load_persona,
    resolve_post,
    short_disclosure_label,
    skip_if_legacy,
)

FOLD_LINES = 2          # 피드에서 '더 보기' 전에 보이는 화면 줄 수
MORE_LABEL = "… 더 보기"
WEEKDAYS = "월화수목금토일"


# ---------------------------------------------------------------- caption

def normalize_hashtags(raw) -> list[str]:
    """'#출근룩', ' 출근룩 ' → '출근룩'. 빈 값·중복 제거, 순서 유지.

    None(YAML 의 '- #태그' 가 주석으로 읽힌 것)·true/false 는 버린다 — '#None' 이 게시되지 않게 (check 가 오류로 알림).
    """
    out: list[str] = []
    for t in raw or []:
        if t is None or isinstance(t, bool):
            continue
        t = str(t).strip().lstrip("#").strip()
        if t and t not in out:
            out.append(t)
    return out


def _warn_stderr(msg: str) -> None:
    print(f"주의: {msg}", file=sys.stderr)


def build_caption(post: Post | dict, persona: dict | None = None, config: dict | None = None,
                  *, warn: Callable[[str], None] | None = None) -> str:
    """앱에 붙여넣을 최종 캡션.

    [광고 · 브랜드] 가상인물 고지   ← 표시 대상일 때만, 반드시 첫 줄 (더 보기 전에 보여야 함)
    수수료 문장                     ← affiliate 일 때만 (persona.disclosure.affiliate_notice)
    캡션 본문
    (빈 줄) 제품 이미지 안내       ← products 가 있을 때 (AI 합성 이미지는 실물과 다를 수 있음)
    (빈 줄) AI 가상인물 안내
    (빈 줄) #해시태그 (최대 config.publishing.max_hashtags 개)

    가상인물 고지는 공정위 추천·보증 심사지침(2026-06-01 시행): 광고 글의 첫 부분에 표시.
    """
    data = post.data if isinstance(post, Post) else (post or {})
    config = config or load_config()
    persona = persona or load_persona(config)
    warn = warn or _warn_stderr

    label = disclosure_label(data, persona)
    body = str(data.get("caption") or "").strip()
    pdisc = persona.get("disclosure") or {}
    footer = str(pdisc.get("caption_footer") or "").strip()
    notice = str(pdisc.get("ad_virtual_notice") or "").strip()
    affiliate = (data.get("disclosure") or {}).get("affiliate") is True
    affiliate_notice = str(pdisc.get("affiliate_notice") or "").strip() if affiliate else ""
    products = data.get("products")
    has_products = isinstance(products, list) and any(isinstance(p, dict) for p in products)
    product_note = str(pdisc.get("product_image_note") or "").strip() if has_products else ""
    raw_tags = data.get("hashtags")
    tags = normalize_hashtags(raw_tags if isinstance(raw_tags, list) else [raw_tags] if raw_tags else [])
    max_tags = int((config.get("publishing") or {}).get("max_hashtags") or 5)
    if len(tags) > max_tags:
        warn(f"해시태그 {len(tags)}개 중 앞의 {max_tags}개만 캡션에 넣었어요 (빠진 것: {' '.join('#' + t for t in tags[max_tags:])})")
        tags = tags[:max_tags]

    first = (f"[{label}] {notice}" if notice else f"[{label}]") if label else ""
    head = "\n".join(x for x in (first, affiliate_notice, body) if x)
    parts = [p for p in (head, product_note, footer, " ".join("#" + t for t in tags)) if p]
    caption = "\n\n".join(parts)
    if len(caption) > CAPTION_LIMIT:
        warn(f"캡션이 {len(caption):,}자예요. 인스타그램 한도 {CAPTION_LIMIT:,}자를 넘어요.")
    return caption


def caption_fold(caption: str, handle: str = "", line_units: float = FEED_LINE_UNITS,
                 max_lines: int = FOLD_LINES) -> str:
    """피드에서 '… 더 보기' 전에 보이는 캡션 앞부분 (근사치). 캡션 문자열의 앞부분을 그대로 돌려준다.

    줄바꿈 수가 아니라 화면 폭으로 센다: 첫 줄은 굵은 아이디 뒤에서 시작하고, 한 줄 폭(text_width 기준
    line_units)을 넘으면 단어 단위로 줄을 바꾼다. 다 보이지 않으면 마지막 줄 끝에서 '… 더 보기' 자리를 뺀다.
    """
    lines: list[tuple[int, int, float]] = []          # 화면 줄마다 (시작, 끝, 앞에 붙는 아이디 폭)
    lead = text_width(handle) + 0.5 if handle else 0.0
    start, width, space, i = 0, lead, None, 0         # space: 지금 줄에서 마지막 공백 위치 (단어 단위 줄바꿈)

    def wrap(end: int, nxt: int) -> None:
        nonlocal start, width, space, lead
        lines.append((start, end, lead))
        start, space, lead = nxt, None, 0.0
        width = text_width(caption[nxt:i])

    while i < len(caption) and len(lines) < max_lines:
        ch = caption[i]
        if ch == "\n":
            wrap(i, i + 1)
            i += 1
            continue
        w = text_width(ch)
        if width + w > line_units and i > start:
            if ch == " ":                             # 줄 끝 공백에서 바로 줄바꿈
                wrap(i, i + 1)
                i += 1
            elif space is not None:                   # 마지막 단어를 다음 줄로
                wrap(space, space + 1)
            else:                                     # 한 단어가 한 줄보다 길면 글자 단위로
                wrap(i, i)
            continue
        if ch == " ":
            space = i
        width += w
        i += 1
    if len(lines) < max_lines:
        lines.append((start, len(caption), lead))
        start = len(caption)
    if start >= len(caption.rstrip()):
        return caption                                # 전부 보임 ('더 보기' 없음)
    s, e, lead = lines[max_lines - 1]
    room = line_units - lead - text_width(" " + MORE_LABEL)
    while e > s and text_width(caption[s:e]) > room:
        e -= 1
    return caption[:e].rstrip()


# ---------------------------------------------------------------- checklist

def posting_checklist(post: Post, persona: dict | None = None, slide_count: int | None = None) -> list[str]:
    """인스타그램 앱에서 사람이 직접 할 일 (자동 게시는 하지 않음)."""
    d = post.data
    persona = persona or load_persona()
    has_c, has_r = post_format(d)
    disc = d.get("disclosure") or {}
    brand = str(disc.get("brand") or "").strip()
    label = disclosure_label(d, persona)
    items = ["캡션: out/caption.txt 전체를 복사해 붙여넣기" + (f" — 첫 줄 '[{label}] …가상인물…' 확인" if label else "")]
    if disc.get("paid") is True or disc.get("gifted") is True:
        items.append(f"고급 설정 → 브랜디드 콘텐츠: '유료 파트너십 레이블' 켜고 브랜드 파트너 '{brand or '브랜드'}' 추가")
    elif disc.get("affiliate") is True:
        items.append("고급 설정 → 브랜디드 콘텐츠: 제휴 수수료도 대상이에요. '유료 파트너십 레이블' 켜기")
    items.append("'AI 정보(AI 레이블)' 표시 토글 켜기 — 메뉴 위치는 앱 버전마다 달라요")
    if has_c:
        n = slide_count if slide_count is not None else len(d.get("slides") or [])
        items.append(f"카드뉴스 {n}장을 01 → {n:02d} 순서로 선택하고 {_slide_ratio_label(post)} 비율 그대로 잘림 없는지 확인")
    items.append("고급 설정 → 접근성 → 대체 텍스트: post.yaml 의 alt_text 붙여넣기")
    if has_r:
        if (d.get("reel") or {}).get("audio"):
            items.append("릴스 음원: 사용권 확인된 음원이 영상에 들어 있어요. 앱에서 음원을 추가하지 않기")
        else:
            items.append("릴스 음원: 무음 영상이에요. 앱에서 음원 추가 여부 결정 (협찬 게시물은 상업용 사용 가능한 음원만)")
        items.append("릴스 커버: out/reel/cover.png 선택 · '피드에도 공유' 여부 확인")
    items.append("위치 추가·사람 태그 여부 결정" + (" (협찬이면 브랜드 계정 태그)" if label else ""))
    items.append("게시 후 post.yaml 의 posted.url · posted_at 기록, 24시간·7일 뒤 tracking/metrics.csv 기록")
    return items


def _slide_ratio_label(post: Post) -> str:
    """렌더된 슬라이드 비율 ('3:4' / '4:5'). 아직 없으면 기본 3:4."""
    slides = find_slides(post)
    if not slides:
        return "3:4"
    from PIL import Image

    with Image.open(slides[0]) as im:
        w, h = im.size
    return "4:5" if abs(h / w - 1.25) < abs(h / w - 4 / 3) else "3:4"


# ---------------------------------------------------------------- images

def find_slides(post: Post) -> list[Path]:
    d = post.out_dir / "slides"
    if not d.is_dir():
        return []
    return sorted(p for p in d.iterdir() if re.fullmatch(r"\d{2}\.png", p.name))


def _font(name: str, size: int, config: dict):
    from PIL import ImageFont

    try:
        return ImageFont.truetype(str(ROOT / config["paths"]["fonts"] / name), size)
    except OSError:  # woff2 를 못 읽는 FreeType 빌드면 기본 글꼴 (한글은 깨질 수 있음)
        return ImageFont.load_default(size)


def _fit_text(draw, text: str, font, max_w: int) -> str:
    if draw.textlength(text, font=font) <= max_w:
        return text
    while text and draw.textlength(text + "…", font=font) > max_w:
        text = text[:-1]
    return text + "…"


def make_contact_sheet(post: Post, slides: list[Path], cover: Path | None, out: Path,
                       persona: dict, config: dict, reel_secs: float | None = None) -> Path:
    """슬라이드(번호·레이아웃 표시)와 릴스 커버를 아이보리 바탕 격자 한 장으로."""
    from PIL import Image, ImageDraw, ImageOps

    colors = (persona.get("layout") or {}).get("colors") or {}
    paper = colors.get("paper", "#F4EFE8")
    ink = colors.get("ink", "#1F1F1F")
    muted = colors.get("muted", "#7A746C")
    accent = colors.get("accent", "#B08A61")
    layouts = [str((s or {}).get("layout", "")) for s in (post.data.get("slides") or [])]

    items: list[tuple[Path, str, str]] = [
        (p, p.stem, layouts[int(p.stem) - 1] if 0 < int(p.stem) <= len(layouts) else "") for p in slides
    ]
    if cover:
        items.append((cover, "REEL", "릴스 커버"))
    aspect = 4 / 3
    if slides:
        with Image.open(slides[0]) as im0:
            aspect = im0.height / im0.width

    cols = max(1, min(4, len(items)))   # 릴스 전용인데 커버가 없으면 그림 없이 머리말만
    rows = -(-len(items) // cols)
    thumb_w, gap, margin, header_h, label_h = 300, 28, 56, 176, 50
    thumb_h = round(thumb_w * aspect)
    # 장수가 적어도 제목·정보 줄이 잘리지 않게 최소 폭을 둔다
    width = max(980, margin * 2 + cols * thumb_w + (cols - 1) * gap)
    height = header_h + rows * (thumb_h + label_h) + max(rows - 1, 0) * gap + margin
    sheet = Image.new("RGB", (width, height), paper)
    draw = ImageDraw.Draw(sheet)

    f_word = _font("CormorantGaramond-SemiBold.woff2", 24, config)
    f_title = _font("Pretendard-Bold.woff2", 40, config)
    f_meta = _font("Pretendard-Medium.woff2", 20, config)
    f_badge = _font("Pretendard-Bold.woff2", 20, config)
    f_label = _font("Pretendard-Medium.woff2", 19, config)

    d = post.data
    wordmark = (persona.get("typography") or {}).get("wordmark_text", "DOHA DAILYFIT")
    draw.text((margin, 40), wordmark, font=f_word, fill=accent)
    draw.text((margin, 74), _fit_text(draw, str(d.get("hook") or post.id), f_title, width - margin * 2 - 260),
              font=f_title, fill=ink)
    meta = [post.id, f"{d.get('date', '')} {as_time(d.get('time')) or ''}".strip()]
    if slides:
        meta.append(f"카드뉴스 {len(slides)}장")
    planned = reel_seconds(d, config)
    if post_format(d)[1] and (reel_secs or planned):
        meta.append(f"릴스 {reel_secs:.1f}초" if reel_secs else f"릴스 {planned:.1f}초 예정")
    draw.text((margin, 128), _fit_text(draw, "  ·  ".join(meta), f_meta, width - margin * 2), font=f_meta, fill=muted)

    label = short_disclosure_label(d, persona)
    if label:  # 광고 표시가 붙는 게시물임을 시트에서도 바로 보이게
        tw = draw.textlength(label, font=f_badge)
        x1 = width - margin
        draw.rounded_rectangle((x1 - tw - 32, 78, x1, 118), radius=20, fill=ink)
        draw.text((x1 - tw - 16, 86), label, font=f_badge, fill="#FFFFFF")

    for idx, (path, num, layout) in enumerate(items):
        r, ccol = divmod(idx, cols)
        x = margin + ccol * (thumb_w + gap)
        y = header_h + r * (thumb_h + label_h + gap)
        with Image.open(path) as im:
            im = im.convert("RGB")
            if num == "REEL":  # 9:16 커버는 칸 안에 맞추고 남는 곳은 바탕색
                thumb = Image.new("RGB", (thumb_w, thumb_h), "#E9E2D8")
                fitted = ImageOps.contain(im, (thumb_w, thumb_h), Image.LANCZOS)
                thumb.paste(fitted, ((thumb_w - fitted.width) // 2, (thumb_h - fitted.height) // 2))
            else:
                thumb = ImageOps.fit(im, (thumb_w, thumb_h), Image.LANCZOS)
        draw.rectangle((x + 3, y + 5, x + thumb_w + 3, y + thumb_h + 5), fill="#E2D9CC")  # 그림자
        sheet.paste(thumb, (x, y))
        draw.rectangle((x, y, x + thumb_w - 1, y + thumb_h - 1), outline="#D6CCBE")
        # 번호는 썸네일 밖 아래에 (슬라이드 모서리의 표시·배지를 가리지 않게)
        ty = y + thumb_h + 12
        bw = draw.textlength(num, font=f_badge) + 18
        draw.rounded_rectangle((x, ty, x + bw, ty + 28), radius=7, fill=ink)
        draw.text((x + 9, ty + 3), num, font=f_badge, fill="#FFFFFF")
        if layout:
            draw.text((x + bw + 10, ty + 4), layout, font=f_label, fill=muted)

    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, optimize=True)
    return out


def media_seconds(path: Path | None) -> float | None:
    """실제 영상 길이 (ffprobe). 장면 사이 전환이 겹쳐 post.yaml 합계보다 짧을 수 있다."""
    import shutil
    import subprocess

    if not path or not Path(path).exists() or not shutil.which("ffprobe"):
        return None
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                             capture_output=True, text=True, timeout=30)
        return float(out.stdout.strip())
    except (subprocess.SubprocessError, ValueError):
        return None


def _jpeg_data_uri(path: Path, width: int = 780, quality: int = 86) -> str:
    """미리보기용으로 줄인 JPEG data URI (390pt 화면 x 2배). 원본 PNG를 그대로 넣으면 HTML이 수십 MB가 됨."""
    from PIL import Image

    with Image.open(path) as im:
        im = im.convert("RGB")
        if im.width > width:
            im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
        buf = BytesIO()
        im.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def _caption_html(text: str):
    from markupsafe import Markup, escape

    esc = str(escape(text))
    # '&#39;' 같은 엔티티 속 '#'는 건드리지 않는다
    return Markup(re.sub(r"(?<![&\w])(#[^\s#<&]+)", r'<span class="tag">\1</span>', esc))


def _date_label(d: dict) -> str:
    day = as_date(d.get("date"))
    t = as_time(d.get("time")) or ""
    if not day:
        return t
    return f"{day.month}월 {day.day}일 ({WEEKDAYS[day.weekday()]}) {t}".strip()


# ---------------------------------------------------------------- build

def build_preview(post: Post, persona: dict | None = None, config: dict | None = None,
                  issues=None) -> dict:
    """caption.txt · contact-sheet.png · preview.html 을 만든다.

    반환: {"ok", "message", "caption", "contact_sheet", "preview", "slides", "reel", "cover", "reel_seconds", "notes"}
    슬라이드(또는 릴스 전용이면 커버)가 없으면 caption.txt 만 쓰고 ok=False.
    """
    config = config or load_config()
    persona = persona or load_persona(config)
    d = post.data
    out = post.out_dir
    out.mkdir(parents=True, exist_ok=True)
    has_c, has_r = post_format(d)
    notes: list[str] = []

    caption = build_caption(post, persona, config, warn=notes.append)
    caption_path = out / "caption.txt"
    caption_path.write_text(caption + "\n", encoding="utf-8")

    slides = find_slides(post) if has_c else []
    reel_mp4 = out / "reel" / "reel.mp4"
    cover = out / "reel" / "cover.png"
    reel_path = reel_mp4 if reel_mp4.exists() else None
    cover_path = cover if cover.exists() else None
    result = {"ok": False, "message": "", "caption": caption_path, "contact_sheet": None, "preview": None,
              "slides": slides, "reel": reel_path, "cover": cover_path, "reel_seconds": None, "notes": notes}

    if has_c and not slides:
        result["message"] = f"슬라이드 PNG가 없어요. 먼저 렌더링하세요: python doha.py render {post.id}"
        return result
    if not has_c and not (reel_path or cover_path):
        result["message"] = f"릴스 파일이 없어요. 먼저 만드세요: python doha.py reel {post.id}"
        return result
    if has_r and not reel_path:
        notes.append(f"릴스 영상이 아직 없어요 (python doha.py reel {post.id}).")
    elif has_r and not cover_path:
        notes.append(f"릴스 커버(cover.png)가 없어요. 다시 만드세요: python doha.py reel {post.id}")

    yaml_mtime = (post.dir / "post.yaml").stat().st_mtime
    rendered = slides + [p for p in (reel_path, cover_path) if p]
    if rendered and min(p.stat().st_mtime for p in rendered) < yaml_mtime:
        notes.append("post.yaml 이 렌더링 뒤에 수정됐어요. 다시 render/reel 하거나 build 를 실행하세요.")
    expected = len(d.get("slides") or [])
    if has_c and len(slides) != expected:
        notes.append(f"슬라이드 파일 {len(slides)}장 ≠ post.yaml slides {expected}장. 다시 렌더링하세요.")

    if issues is None:
        issues = check_post(post, persona, config)
    n_err, n_warn = counts(issues)

    reel_secs = media_seconds(reel_path)
    result["reel_seconds"] = reel_secs
    sheet = make_contact_sheet(post, slides, cover_path, out / "contact-sheet.png", persona, config, reel_secs)
    result["contact_sheet"] = sheet

    slide_ratio = "3 / 4"
    if slides:
        from PIL import Image

        with Image.open(slides[0]) as im:
            slide_ratio = f"{im.width} / {im.height}"
    layouts = [str((s or {}).get("layout", "")) for s in (d.get("slides") or [])]
    canvas = config.get("canvas") or {}
    reel_canvas = canvas.get("reel") or {"width": 1080, "height": 1920}
    safe = canvas.get("reel_safe") or {}
    label = disclosure_label(d, persona)
    handle = persona.get("handle") or (config.get("account") or {}).get("handle", "")
    fold = caption_fold(caption, handle)
    disc = d.get("disclosure") or {}
    brand = str(disc.get("brand") or "").strip()
    font_dir = ROOT / config["paths"]["fonts"]

    def rel(p: Path) -> str:
        return Path(os.path.relpath(p, out)).as_posix()

    ctx = {
        "post_id": post.id,
        "title": str(d.get("hook") or post.id),
        "date_label": _date_label(d),
        "status": d.get("status") or "",
        "handle": handle,
        "display_name": (config.get("account") or {}).get("display_name", ""),
        "has_carousel": has_c,
        "has_reel": has_r,
        "slides": [{"uri": _jpeg_data_uri(p), "num": p.stem,
                    "layout": layouts[int(p.stem) - 1] if 0 < int(p.stem) <= len(layouts) else ""} for p in slides],
        "slide_ratio": slide_ratio,
        "reel": {
            "src": rel(reel_path) if reel_path else None,
            "poster": _jpeg_data_uri(cover_path, width=780) if cover_path else None,
            "seconds": reel_secs or reel_seconds(d, config),
            "audio": bool((d.get("reel") or {}).get("audio")),
        },
        "safe": {k: round(100 * float(safe.get(k, 0)) / float(reel_canvas[dim]), 2)
                 for k, dim in (("top", "height"), ("bottom", "height"), ("left", "width"), ("right", "width"))},
        "caption_text": caption,
        "caption_html": _caption_html(caption),
        "fold": fold,
        "label": label,
        "label_visible": (not label) or (f"[{label}]" in fold),
        "partnership": (brand or "브랜드") if (disc.get("paid") is True or disc.get("gifted") is True) else
                       ("제휴" if disc.get("affiliate") is True else ""),
        "char_count": len(caption),
        "char_limit": CAPTION_LIMIT,
        "tag_count": len(normalize_hashtags(d.get("hashtags") if isinstance(d.get("hashtags"), list) else [])),
        "tag_max": int((config.get("publishing") or {}).get("max_hashtags") or 5),
        "errors": [i for i in issues if i.level == "error"],
        "warns": [i for i in issues if i.level == "warn"],
        "n_err": n_err,
        "n_warn": n_warn,
        "checklist": posting_checklist(post, persona, len(slides) if has_c else None),
        "notes": notes,
        "alt_text": str(d.get("alt_text") or ""),
        "ai_badge": (persona.get("disclosure") or {}).get("slide_badge", "AI 가상 인물"),
        "font_regular": rel(font_dir / "Pretendard-Regular.woff2"),
        "font_semibold": rel(font_dir / "Pretendard-SemiBold.woff2"),
        "font_bold": rel(font_dir / "Pretendard-Bold.woff2"),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    from doha.htmlrender import render_template

    html = render_template("preview/preview.html", **ctx)
    preview_path = out / "preview.html"
    preview_path.write_text(html, encoding="utf-8")
    result.update(ok=True, preview=preview_path)
    return result


# ---------------------------------------------------------------- CLI

def add_arguments(parser) -> None:
    parser.add_argument("post", help="게시물 id 일부, 폴더 또는 post.yaml 경로")


def print_result(result: dict) -> None:
    def show(p):
        try:
            return p.relative_to(ROOT).as_posix()
        except ValueError:
            return str(p)

    print(f"캡션        {show(result['caption'])}")
    if result["contact_sheet"]:
        print(f"연락시트    {show(result['contact_sheet'])}")
    if result["preview"]:
        print(f"휴대폰 미리보기 {show(result['preview'])}  (브라우저로 열기)")
    for n in result["notes"]:
        print(f"주의: {n}")


def run(args) -> int:
    post = resolve_post(args.post)
    if skip_if_legacy(post):
        return 0
    config = load_config()
    persona = load_persona(config)
    issues = check_post(post, persona, config)
    result = build_preview(post, persona, config, issues=issues)
    print_result(result)
    if not result["ok"]:
        print(result["message"])
        return 1
    n_err, _ = counts(issues)
    if n_err:
        # render → preview 로 따로 만든 경우에도 터미널에서 멈추게 (build 는 검수 단계에서 이미 멈춤)
        print()
        print(format_report(post.id, issues))
        print(f"\n!! 검수 오류 {n_err}개 — 이 caption.txt·이미지는 게시하지 마세요. post.yaml 을 고친 뒤 다시 만드세요.")
        return 1
    return 0
