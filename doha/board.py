"""운영 보드 데이터 (board).

  python doha.py board                         # board-data.js 갱신 → index.html 을 브라우저로 열기
  python doha.py board --data-dir /임시/폴더    # 테스트용 tracking 폴더 (metrics.csv 등). 안에 posts/,
                                               # prospects.csv, templates/ 가 있으면 그것도 거기서 읽음
  python doha.py board --out /경로/board-data.js

보드(index.html)는 board-data.js 의 window.DOHA_DATA 만 읽는다. 계정·API에 연결되지 않고,
보드에서 고친 값은 그 브라우저의 localStorage 에만 남는다 (CSV로 내보내 커밋해야 저장소에 반영).
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import yaml

from doha.core import ROOT, disclosure_label, load_config, load_persona, load_yaml

KST = timezone(timedelta(hours=9))
DEFAULT_OUT = ROOT / "board-data.js"

# 고정 스키마. 실제 파일 헤더가 있으면 그걸 그대로 쓰고(내보내기 헤더가 정확히 같도록), 없을 때만 이 값.
SCHEMAS = {
    "metrics": ["post_id", "checkpoint", "recorded_at", "format", "reach", "views", "likes", "comments",
                "saves", "shares", "profile_visits", "follows", "link_clicks", "avg_watch_sec",
                "completion_rate", "notes"],
    "followers": ["date", "followers", "notes"],
    "revenue": ["date", "type", "brand", "post_id", "gross_krw", "withholding_krw", "net_krw", "status", "notes"],
    "costs": ["date", "category", "provider", "description", "post_id", "amount_usd", "amount_krw",
              "quantity", "notes"],
    "prospects": ["brand", "category", "instagram", "website", "price_tier", "fit_reason", "contact_channel",
                  "priority", "status", "last_contact", "next_action", "notes", "source"],
}
PROSPECT_STATUSES = ["후보", "조사완료", "연락", "회신", "협의", "계약", "보류", "거절"]
POST_STATUSES = {"idea": "아이디어", "draft": "초안", "images": "이미지", "rendered": "렌더링",
                 "reviewed": "검수", "approved": "승인", "posted": "게시됨"}

# 게시 전 체크리스트. applies: all | ad(대가 있음) | products | reel. {label}{date}{time} 은 보드가 채움.
CHECKLIST = [
    {"id": "ai", "label": "AI 표시", "applies": "all",
     "detail": "도하가 나오는 모든 장·장면에 'AI 가상인물' 배지, 캡션 끝 AI 안내 문구, 앱 'AI 정보' 라벨(릴스 필수)."},
    {"id": "ad", "label": "광고 표시 — 캡션 첫 줄 + 유료 파트너십 레이블", "applies": "ad",
     "detail": "캡션 첫 줄 '[{label}]' + 가상인물 고지, 커버 상단 표시, 앱 '유료 파트너십' 레이블과 브랜드 태그.",
     "plain": "대가(돈·무상 제품·제휴 수수료)가 없는 일반 게시물이 맞는지 확인. 있으면 post.yaml disclosure를 바꿔요."},
    {"id": "experience", "label": "체험 표현 없음", "applies": "all",
     "detail": "'입어보니·써보니·제가 샀는데' 같은 지어낸 체험, 효능 표현이 없어요. check 오류 0."},
    {"id": "source", "label": "상품 정보 출처·확인일", "applies": "products",
     "detail": "가격·소재는 공식 페이지(source_url)와 확인일(checked_at)이 있는 정보만 썼어요.",
     "na": "소개하는 상품이 없어요."},
    {"id": "image_qa", "label": "이미지 QA (손·옷·로고·글자)", "applies": "all",
     "detail": "손가락·손 모양, 옷 솔기·단추·핏, 가짜 로고·깨진 글자, 얼굴이 기준 이미지와 같은 사람인지."},
    {"id": "phone", "label": "휴대폰 미리보기", "applies": "all",
     "detail": "out/preview.html 을 휴대폰에서 열어 3:4 그리드 잘림, 글자 크기, 배지 가림을 확인."},
    {"id": "alt", "label": "대체 텍스트", "applies": "all",
     "detail": "앱 고급 설정 → 접근성에 alt_text 붙여넣기 (AI 생성·가상인물 설명 포함)."},
    {"id": "audio", "label": "음원 사용권", "applies": "reel",
     "detail": "사용권을 확인한 음원이거나 무음. 협찬 게시물은 상업용으로 쓸 수 있는 음원만.",
     "na": "릴스가 없는 게시물이에요."},
    {"id": "time", "label": "게시 시간", "applies": "all",
     "detail": "{date} {time} (KST)에 직접 게시하고, 게시 후 posted.url 과 24시간·7일 지표를 기록."},
]


def _enums() -> dict:
    """수익·비용 분류는 metrics 리포트와 같은 값을 쓴다 (모듈이 없으면 같은 내용의 기본값)."""
    try:
        from doha import metrics as m

        rev_types, rev_status, cost_cats, aliases = m.REVENUE_TYPES, m.REVENUE_STATUS, m.COST_CATEGORIES, m.ALIASES
    except ImportError:
        rev_types = {"sponsorship": "협찬 게시비", "production": "제작비", "usage_rights": "사용권",
                     "affiliate": "제휴 수수료", "gifted": "현물 협찬", "other": "기타"}
        rev_status = {"contracted": "계약", "invoiced": "청구", "paid": "입금", "cancelled": "취소"}
        cost_cats = {"image_api": "이미지 API", "subscription": "구독·툴", "ads": "광고비",
                     "outsourcing": "외주", "props": "소품·샘플", "other": "기타"}
        aliases = {}
    return {
        "revenue_type": rev_types, "revenue_status": rev_status, "cost_category": cost_cats,
        "aliases": aliases, "prospect_status": PROSPECT_STATUSES, "post_status": POST_STATUSES,
        "checkpoints": ["24h", "7d", "30d"], "formats": {"carousel": "카드뉴스", "reel": "릴스"},
        "priorities": ["A", "B", "C"], "contact_channels": ["이메일", "폼", "DM"],
    }


# ── 읽기 ───────────────────────────────────────────────────

def read_table(path: Path, kind: str, warnings: list[str]) -> tuple[list[str], list[dict]]:
    """CSV → (헤더, 행). 값은 문자열 그대로 둔다: 보드가 내보낼 때 원래 값이 바뀌지 않게."""
    expected = SCHEMAS[kind]
    if not path.exists():
        warnings.append(f"{path.name}: 파일이 없어 기본 열 이름을 써요.")
        return expected, []
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        warnings.append(f"{path.name}: UTF-8 이 아니에요(엑셀 기본 CSV?). 'CSV UTF-8' 로 다시 저장하세요.")
        text = raw.decode("cp949", errors="replace")
    reader = csv.reader(io.StringIO(text))
    header = [h.strip() for h in next(reader, [])]
    if not header:
        return expected, []
    missing = [c for c in expected if c not in header]
    if missing:
        warnings.append(f"{path.name}: 열이 없어요 → {', '.join(missing)} (열 이름은 바꾸지 마세요).")
    rows = []
    for cells in reader:
        if not any(c.strip() for c in cells):
            continue
        rows.append({col: (cells[i].strip() if i < len(cells) else "") for i, col in enumerate(header) if col})
    return [h for h in header if h], rows


def _url(path: Path, base: Path) -> str:
    """board-data.js 위치 기준 상대 URL (index.html 이 같은 폴더에 있다는 전제)."""
    rel = Path(os.path.relpath(path, base)).as_posix()
    return quote(rel, safe="/._-~")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


def _time(value) -> str:
    # 따옴표 없이 쓴 07:40 은 YAML 1.1 에서 60진수 정수(460)가 된다
    if isinstance(value, int):
        return f"{value // 60:02d}:{value % 60:02d}"
    return str(value or "").strip()


def _has_reel(fmt: str) -> bool:
    return fmt in ("reel", "both")


def _dict(v) -> dict:
    return v if isinstance(v, dict) else {}


def post_entry(folder: Path, data: dict, persona: dict, base: Path, default_time: str) -> dict:
    disc = _dict(data.get("disclosure"))
    images = _dict(data.get("images"))
    products = [p for p in data.get("products") or [] if isinstance(p, dict)]
    fmt = str(data.get("format") or "").strip().lower()
    slides_dir = folder / "out" / "slides"
    rendered = sorted(p for p in slides_dir.glob("*.png") if re.fullmatch(r"\d{2}\.png", p.name)) \
        if slides_dir.is_dir() else []
    out = folder / "out"
    thumb = rendered[0] if rendered else (out / "reel" / "cover.png")
    links = {name: _url(p, base) for name, p in (
        ("preview", out / "preview.html"), ("contact_sheet", out / "contact-sheet.png"),
        ("caption", out / "caption.txt"), ("reel", out / "reel" / "reel.mp4")) if p.exists()}
    posted, review = _dict(data.get("posted")), _dict(data.get("review"))
    img_list = [{"key": str(k), "status": str(_dict(v).get("status") or "todo"),
                 "framing": str(_dict(v).get("framing") or "")} for k, v in images.items()]
    ad = bool(disc.get("paid") or disc.get("gifted") or disc.get("affiliate"))
    no_source = [str(p.get("name") or p.get("id") or "?") for p in products
                 if not (p.get("source_url") and p.get("checked_at"))]

    # 체크 항목 옆에 띄울 주의 (post.yaml 에서 바로 보이는 것만; 최종 판단은 check 와 사람)
    hints = {}
    if ad and not str(disc.get("brand") or "").strip():
        hints["ad"] = "disclosure.brand 가 비어 있어요."
    if no_source:
        hints["source"] = "출처·확인일 없는 상품: " + ", ".join(no_source)
    approved = sum(1 for i in img_list if i["status"] == "approved")
    if img_list and approved < len(img_list):
        hints["image_qa"] = f"승인된 이미지 {approved}/{len(img_list)}"
    if not str(data.get("alt_text") or "").strip():
        hints["alt"] = "post.yaml 의 alt_text 가 비어 있어요."
    if _has_reel(fmt) and not _dict(data.get("reel")).get("audio"):
        hints["audio"] = "무음 릴스예요. 앱에서 음원을 넣으면 사용권을 확인하세요."
    if not rendered and fmt in ("carousel", "both"):
        hints["phone"] = "아직 렌더링 전이에요 (python doha.py build)."

    return {
        "id": str(data.get("id") or folder.name),
        "dir": _rel(folder),
        "date": str(data.get("date") or ""),
        "time": _time(data.get("time")) or default_time,
        "status": str(data.get("status") or "idea").strip().lower(),
        "series": str(data.get("series") or ""),
        "pillar": str(data.get("pillar") or ""),
        "format": fmt,
        "goal": str(data.get("goal") or ""),
        "hook": " ".join(str(data.get("hook") or "").split()),
        "disclosure": {"ai_persona": disc.get("ai_persona") is not False, "paid": bool(disc.get("paid")),
                       "gifted": bool(disc.get("gifted")), "affiliate": bool(disc.get("affiliate")),
                       "brand": str(disc.get("brand") or "")},
        "disclosure_label": disclosure_label({**data, "disclosure": disc}, persona),
        "ad": ad,
        "slide_count": len(data.get("slides") or []),
        "scene_count": len(_dict(data.get("reel")).get("scenes") or []),
        "rendered_slides": len(rendered),
        "thumb": _url(thumb, base) if thumb.exists() else "",
        "links": links,
        "images": img_list,
        "products": len(products),
        "hints": hints,
        "review": {"approved_by": str(review.get("approved_by") or ""),
                   "approved_at": str(review.get("approved_at") or "")},
        "posted": {"url": str(posted.get("url") or ""), "reel_url": str(posted.get("reel_url") or ""),
                   "posted_at": str(posted.get("posted_at") or "")},
    }


def load_posts(folder: Path, persona: dict, base: Path, default_time: str, warnings: list[str]) -> list[dict]:
    posts = []
    for d in sorted(folder.iterdir()) if folder.is_dir() else []:
        path = d / "post.yaml"
        if not path.is_file():
            continue
        try:
            data = load_yaml(path) or {}
        except yaml.YAMLError as e:
            warnings.append(f"{d.name}/post.yaml 을 읽지 못했어요: {str(e).splitlines()[0]}")
            continue
        if not isinstance(data, dict):
            warnings.append(f"{d.name}/post.yaml 형식이 이상해요 (딕셔너리가 아님).")
            continue
        entry = post_entry(d, data, persona, base, default_time)
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry["date"]):
            warnings.append(f"{d.name}: date '{entry['date']}' 가 YYYY-MM-DD 가 아니라 캘린더에 안 보여요.")
        posts.append(entry)
    posts.sort(key=lambda p: (p["date"] or "9999", p["time"], p["id"]))
    return posts


def load_templates(folder: Path) -> list[dict]:
    """outreach/templates/*.md → 제목(첫 제목줄)과 조각 목록 [{type: md|code, text}]."""
    out = []
    for path in sorted(folder.glob("*.md")) if folder.is_dir() else []:
        text = path.read_text(encoding="utf-8")
        title = next((m.group(1).strip() for m in re.finditer(r"^#{1,6}\s+(.+)$", text, re.M)), path.stem)
        parts, pos = [], 0
        for m in re.finditer(r"^```[^\n]*\n(.*?)^```[ \t]*$", text, re.M | re.S):
            parts.append({"type": "md", "text": text[pos:m.start()]})
            parts.append({"type": "code", "text": m.group(1).rstrip("\n")})
            pos = m.end()
        parts.append({"type": "md", "text": text[pos:]})
        # 첫 제목줄은 title 로 따로 보여주므로 본문에서 뺀다
        if parts and parts[0]["type"] == "md":
            parts[0]["text"] = re.sub(r"^\s*#{1,6}\s+.+\n?", "", parts[0]["text"], count=1)
        out.append({"id": path.stem, "file": _rel(path), "title": title,
                    "parts": [p for p in parts if p["type"] == "code" or p["text"].strip()]})
    return out


def _pick(data_dir: Path | None, *names: str) -> Path | None:
    for name in names:
        if data_dir and (data_dir / name).exists():
            return data_dir / name
    return None


def collect(data_dir: Path | None = None, out_path: Path = DEFAULT_OUT) -> dict:
    config = load_config()
    persona = load_persona(config)
    paths = config["paths"]
    base = out_path.resolve().parent
    warnings: list[str] = []

    tracking = data_dir or ROOT / paths["tracking"]
    tables, schemas = {}, {}
    for kind in ("metrics", "followers", "revenue", "costs"):
        schemas[kind], tables[kind] = read_table(tracking / f"{kind}.csv", kind, warnings)
    prospects_path = _pick(data_dir, "prospects.csv", "outreach/prospects.csv") \
        or ROOT / paths["outreach"] / "prospects.csv"
    schemas["prospects"], tables["prospects"] = read_table(prospects_path, "prospects", warnings)
    for row in tables["prospects"]:
        if row.get("status") and row["status"] not in PROSPECT_STATUSES:
            warnings.append(f"prospects.csv: '{row.get('brand')}' 의 status '{row['status']}' 는 정해진 값이 아니에요.")

    posts_folder = _pick(data_dir, "posts") or ROOT / paths["posts"]
    templates_folder = _pick(data_dir, "templates") or ROOT / paths["outreach"] / "templates"
    account = config.get("account") or {}
    disc = persona.get("disclosure") or {}
    return {
        "version": 1,
        "generated_at": datetime.now(KST).isoformat(timespec="seconds"),
        "account": {k: account.get(k) for k in ("handle", "display_name", "url")},
        "goal": {"monthly_net_krw": int(account.get("goal_monthly_net_krw") or 0),
                 "note": "목표치이지 예상 수익이 아니에요."},
        "fx_usd_krw": float((config.get("fx") or {}).get("usd_krw") or 0),
        "disclosure": {k: disc.get(k) for k in ("slide_badge", "caption_footer", "ad_virtual_notice")},
        "posts": load_posts(posts_folder, persona, base,
                            str((config.get("publishing") or {}).get("default_time") or ""), warnings),
        "schemas": schemas,
        "prospects": tables["prospects"],
        "metrics": tables["metrics"],
        "followers": tables["followers"],
        "revenue": tables["revenue"],
        "costs": tables["costs"],
        "enums": _enums(),
        "checklist": CHECKLIST,
        "templates": load_templates(templates_folder),
        "warnings": warnings,
    }


def write_js(data: dict, path: Path) -> None:
    body = json.dumps(data, ensure_ascii=False, indent=1)
    # JS 문자열 안의 줄 구분 문자는 오래된 엔진에서 문법 오류가 된다
    body = body.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("/* 자동 생성 파일: python doha.py board — 직접 고치지 마세요. 원본은 content/, tracking/, outreach/ */\n"
                    f"window.DOHA_DATA = {body};\n", encoding="utf-8")


# ── CLI ────────────────────────────────────────────────────

def add_arguments(parser) -> None:
    parser.add_argument("--data-dir", help="(테스트용) metrics.csv 등이 든 폴더. posts/·prospects.csv·templates/ 가 있으면 함께 사용")
    parser.add_argument("--out", help=f"출력 파일 (기본: {DEFAULT_OUT.name}, index.html 과 같은 폴더)")


def run(args) -> int:
    data_dir = Path(args.data_dir).resolve() if args.data_dir else None
    if data_dir and not data_dir.is_dir():
        raise SystemExit(f"폴더가 없어요: {data_dir}")
    out = Path(args.out).resolve() if args.out else DEFAULT_OUT
    data = collect(data_dir, out)
    write_js(data, out)
    n = {k: len(data[k]) for k in ("posts", "prospects", "metrics", "followers", "revenue", "costs", "templates")}
    print(f"운영 보드 데이터를 갱신했어요: {_rel(out) if out.parent == ROOT else out}")
    print(f"  게시물 {n['posts']} · 브랜드 {n['prospects']} · 지표 {n['metrics']}줄 · 팔로워 {n['followers']}줄 · "
          f"수익 {n['revenue']}줄 · 비용 {n['costs']}줄 · 제안 문구 {n['templates']}개")
    for w in data["warnings"]:
        print(f"  주의: {w}")
    index = out.parent / "index.html"
    if index.exists():
        print(f"보드 열기: {index.as_uri()}")
    print("보드에서 고친 값은 그 브라우저에만 저장돼요. 'CSV 내보내기'로 저장소 파일을 바꾸고 커밋하세요.")
    return 0
