"""매일 정보형 카드뉴스 패키지: content/daily/<날짜>/package.yaml → 검수 → package.md (ChatGPT 프롬프트 포함).

흐름 (docs/11-daily-cardnews.md):
  1) 트렌드 수집·선정·사실 확인은 Claude(매일 루틴)가 웹 검색으로 하고 package.yaml 을 채운다.
  2) python doha.py daily-check <날짜>  → 출처 없는 사실, 너무 긴 문구, 프롬프트 누락, 표기 누락을 잡는다.
  3) python doha.py daily-md <날짜>     → 사람이 그대로 복사해 ChatGPT에 붙여넣는 package.md 를 만든다.
사람은 package.md 의 프롬프트로 이미지를 받고, 캡션을 붙여 Instagram에 올리기만 한다.
"""
from __future__ import annotations

import re
from datetime import date as Date
from pathlib import Path

import yaml

from doha.core import ROOT, load_yaml

DAILY_DIR = ROOT / "content" / "daily"
STYLE_FILE = ROOT / "brand" / "infocard-style.yaml"

LIMITS = {"headline": 18, "sub": 32, "info": 24, "point": 40}
ROLES = {"cover", "item", "summary", "tip", "cta"}
FACT_STATUS = {"confirmed", "planned", "last_year", "unverified"}
# 확정이 아닌 사실이 슬라이드에 들어가면 붙어 있어야 하는 꼬리표
HEDGE_WORDS = ("예정", "작년", "미정", "발표 전", "추후", "변경", "기준", "2025년")
# 이미지 글자·그림 묘사·캡션에 넣지 않는 말 (사용자 운영 원칙: 사람이 만든 카드뉴스처럼).
# 예측 자료는 "○○ 발표 기준", "절정 시기"처럼 출처로 표현한다.
NO_WORDS = ("AI", "인공지능", "생성 이미지", "예측", "예상")
NO_WORDS_ALLOW = ("계절예측",)   # 실제 메뉴·고유명사는 그대로 써야 해서 예외


def _no_words(text: str) -> list[str]:
    for a in NO_WORDS_ALLOW:
        text = text.replace(a, "")
    return [w for w in NO_WORDS if w in text]


BANNED = ("무조건", "100%", "역대급", "최저가 보장", "완벽", "필수템", "인생템")
EXPERIENCE = ("다녀왔", "먹어보니", "가보니", "써보니", "입어보니", "내돈내산", "직접 가", "직접 찍")
# Meta가 노출을 줄이는 참여 유도(engagement bait) 문구 — 공유는 "보내기"로 유도한다
BAIT = ("태그", "댓글 달", "댓글로", "좋아요 누르", "팔로우하면", "리그램", "공유하면", "추첨")
# 사진 묘사 공식 (docs/11 §6): '실사'라는 말만으로는 평면 그림이 나와서(10/20),
# 실사 표현 + 구체적인 빛·질감 표현 + 글씨 차단 문구를 함께 요구한다
PHOTO_CUES = ("실사", "사진", "카메라로 찍은")
LIGHT_CUES = ("자연광", "햇살", "질감", "카메라", "CG", "보정")
NO_TEXT_CUES = ("글씨", "로고", "간판")
# 게시 후 스토리로 공유해 모으는 프로필 하이라이트 5개 (분야 → 하이라이트)
HIGHLIGHTS = {"축제": "축제", "전시": "축제", "팝업": "팝업", "핫플": "팝업", "신상": "팝업",
              "맛집": "맛집", "혜택": "혜택", "생활꿀팁": "혜택", "시즌": "시즌", "이슈": "시즌"}
# 계절 풍경이 주인공인 나들이는 분야가 '축제'여도 '시즌'에 모은다 (10/21 억새·한강 게시물을 사용자가 '시즌'에 넣음)
SEASON_WORDS = ("단풍", "억새", "벚꽃", "봄꽃", "첫눈", "눈꽃", "크리스마스", "연말", "가을", "겨울", "여름")
NUM_RE = re.compile(r"\d{1,2}\.\d{1,2}|\d{1,3}(?:,\d{3})+원?|\d+원|\d{1,2}:\d{2}|\d+%")


def add_arguments(parser, command: str) -> None:
    parser.add_argument("date", nargs="?", default=None, help="날짜 YYYY-MM-DD (기본: 오늘)")
    if command == "daily-new":
        parser.add_argument("--style", default="info-warm", help="brand/infocard-style.yaml 프리셋")


def _date(arg: str | None) -> str:
    if not arg:
        from datetime import datetime, timedelta, timezone
        return datetime.now(timezone(timedelta(hours=9))).date().isoformat()
    Date.fromisoformat(arg)
    return arg


def package_path(day: str) -> Path:
    return DAILY_DIR / day / "package.yaml"


def load_package(day: str) -> dict:
    p = package_path(day)
    if not p.exists():
        raise SystemExit(f"패키지가 없어요: {p.relative_to(ROOT)} — python doha.py daily-new {day}")
    pkg = load_yaml(p) or {}
    # 장 번호는 적힌 값과 상관없이 순서로 매긴다 (YAML 1.1은 `no:` 키를 False 로 읽음)
    for i, s in enumerate(pkg.get("slides") or [], 1):
        if isinstance(s, dict):
            s.pop(False, None)
            s["_no"] = i
    return pkg


TEMPLATE = """# 매일 정보형 카드뉴스 패키지 — 형식은 docs/11-daily-cardnews.md
date: {day}
status: draft          # draft → ready(검수 통과) → posted
style: {style}         # brand/infocard-style.yaml 프리셋: info-warm | info-night | info-clean
highlight: ""          # 비우면 분야로 자동: 축제 | 팝업 | 맛집 | 혜택 | 시즌

topic:
  title: ""            # 카드뉴스 주제 (예: 이번 주 서울 단풍 명소 5곳)
  category: ""         # 핫플 | 팝업 | 축제 | 전시 | 맛집 | 신상 | 혜택 | 생활꿀팁 | 시즌 | 이슈
  why_now: ""          # 왜 오늘 올려야 하나 (기간 시작·마감, 검색량 급증 등)
  trend_evidence: []   # - {{source: naver_blog|instagram|news|official|other, url: "", note: "", seen_at: {day}}}
  score: {{timeliness: 0, save_share: 0, breadth: 0, visual: 0, verifiability: 0, risk: 0, total: 0}}

backups: []            # - {{title: "", category: "", why_now: "", score_total: 0}}
recent_topics_checked: []   # 최근 14일 주제와 겹치지 않는지 본 목록

facts: []
#  - id: f1
#    claim: "행사 기간"
#    value: "11.1~11.10"
#    source_url: "https://…"   # 공식 출처 우선
#    source_type: official     # official | press | blog
#    checked_at: {day}
#    status: confirmed         # confirmed | planned | last_year | unverified

slides: []
#  - role: cover               # 장 번호는 순서대로 자동               # cover | item | summary | tip | cta
#    headline: ""              # 이미지 큰 글자 (18자 이내, 줄바꿈은 \\n)
#    sub: ""                   # 작은 글자 (32자 이내)
#    info: []                  # 정보줄 (각 24자 이내) 예: ["11.1~11.10", "서울숲 일대", "무료"]
#    point: ""                 # 한 줄 포인트 (40자 이내, 선택)
#    visual: ""                # 그림 묘사 (실사풍 장면·구도·색감)
#    fact_ids: []

caption: |

hashtags: []           # 3~5개, # 없이
alt_text: ""
notes: ""
"""


def cmd_new(args) -> int:
    day = _date(args.date)
    p = package_path(day)
    if p.exists():
        print(f"이미 있어요: {p.relative_to(ROOT)} (덮어쓰지 않음)")
        return 1
    styles = (load_yaml(STYLE_FILE) or {}).get("presets", {})
    if args.style not in styles:
        print(f"스타일 프리셋이 없어요: {args.style} (가능: {', '.join(styles)})")
        return 1
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(TEMPLATE.format(day=day, style=args.style), encoding="utf-8")
    print(f"만들었어요: {p.relative_to(ROOT)}")
    return 0


# ---------------------------------------------------------------- 검수

def _slide_texts(s: dict) -> list[tuple[str, str]]:
    out = [("headline", str(s.get("headline") or "")), ("sub", str(s.get("sub") or "")),
           ("point", str(s.get("point") or ""))]
    out += [("info", str(x)) for x in (s.get("info") or [])]
    return [(k, v) for k, v in out if v]


def check_package(pkg: dict) -> tuple[list[str], list[str]]:
    errors, warns = [], []
    styles = (load_yaml(STYLE_FILE) or {}).get("presets", {})
    if pkg.get("style") not in styles:
        errors.append(f"style '{pkg.get('style')}' 가 brand/infocard-style.yaml 에 없어요")
    topic = pkg.get("topic") or {}
    if not topic.get("title"):
        errors.append("topic.title 이 비어 있어요")
    if not topic.get("why_now"):
        warns.append("topic.why_now(왜 오늘인가)가 비어 있어요")
    if len(topic.get("trend_evidence") or []) < 2:
        warns.append("trend_evidence(트렌드 근거)가 2개 미만이에요 — 블로그·인스타·뉴스 신호를 함께 남기세요")

    facts = {f.get("id"): f for f in (pkg.get("facts") or []) if isinstance(f, dict)}
    if not facts:
        errors.append("facts 가 비어 있어요 — 날짜·장소·가격 같은 사실은 출처와 함께 적어야 해요")
    for fid, f in facts.items():
        if not f.get("source_url"):
            errors.append(f"facts.{fid}: source_url 없음")
        if not f.get("checked_at"):
            errors.append(f"facts.{fid}: checked_at 없음")
        if f.get("status") not in FACT_STATUS:
            errors.append(f"facts.{fid}: status 는 {'|'.join(sorted(FACT_STATUS))} 중 하나")
        if f.get("source_type") == "blog" and f.get("status") == "confirmed":
            warns.append(f"facts.{fid}: 블로그 출처를 confirmed 로 두었어요 — 공식 출처로 바꾸거나 unverified")
    fact_values = " ".join(str(f.get("value", "")) + " " + str(f.get("claim", "")) for f in facts.values())

    slides = pkg.get("slides") or []
    if not 5 <= len(slides) <= 8:
        errors.append(f"슬라이드는 5~8장이어야 해요 (지금 {len(slides)}장)")
    if slides and (slides[0].get("role") != "cover"):
        errors.append("1장은 role: cover 여야 해요")
    if slides and (slides[-1].get("role") != "cta"):
        warns.append("마지막 장이 cta 가 아니에요 (저장·공유 유도 + 기준일 안내 권장)")
    for i, s in enumerate(slides, 1):
        where = f"slides[{i}]"
        if s.get("role") not in ROLES:
            errors.append(f"{where}: role 은 {'|'.join(sorted(ROLES))}")
        if not s.get("headline"):
            errors.append(f"{where}: headline 이 비어 있어요")
        if not s.get("visual"):
            warns.append(f"{where}: visual(그림 묘사)이 비어 있어요")
        for w in _no_words(str(s.get("visual") or "")):
            errors.append(f"{where}.visual: '{w}' 는 그림 묘사에 넣지 않아요")
        visual = str(s.get("visual") or "")
        if visual and pkg.get("style") != "info-clean":
            if not (any(c in visual for c in PHOTO_CUES) and any(c in visual for c in LIGHT_CUES)):
                warns.append(f"{where}.visual: 실사 신호가 약해요 ('실사풍 사진 타일' + '실제 카메라로 찍은 듯한 자연광과 ○○의 질감, "
                             f"과한 보정·CG 느낌 없음' 같은 말)")
            if not any(c in visual for c in NO_TEXT_CUES):
                warns.append(f"{where}.visual: '간판·로고·글씨 없음'을 적어 주세요")
        for kind, text in _slide_texts(s):
            limit = LIMITS[kind]
            longest = max(len(line) for line in text.split("\n"))
            if longest > limit:
                errors.append(f"{where}.{kind}: '{text[:20]}…' 한 줄 {longest}자 > {limit}자 (이미지 글자는 짧게)")
            for w in BANNED:
                if w in text:
                    errors.append(f"{where}.{kind}: 과장 표현 '{w}'")
            for w in EXPERIENCE:
                if w in text:
                    errors.append(f"{where}.{kind}: 체험을 꾸며낸 표현 '{w}'")
            for w in _no_words(text):
                errors.append(f"{where}.{kind}: '{w}' 는 넣지 않아요 — '○○ 발표 기준'처럼 출처로 표현하세요")
            for w in BAIT:
                if w in text:
                    errors.append(f"{where}.{kind}: 참여 유도 문구 '{w}' — Meta가 노출을 줄여요. '저장'·'보내기'로 바꾸세요")
            for num in NUM_RE.findall(text):
                if num.replace("원", "") not in fact_values:
                    warns.append(f"{where}.{kind}: 숫자 '{num}' 이 facts 에서 안 보여요 — 출처 있는 값인지 확인")
        for fid in s.get("fact_ids") or []:
            if fid not in facts:
                errors.append(f"{where}: fact_ids '{fid}' 가 facts 에 없어요")
            elif facts[fid].get("status") != "confirmed":
                joined = " ".join(t for _, t in _slide_texts(s))
                if not any(h in joined for h in HEDGE_WORDS):
                    errors.append(f"{where}: 확정 아닌 사실({fid}: {facts[fid].get('status')})을 쓰면서 "
                                  f"'예정·작년·미정·발표 전' 같은 꼬리표가 없어요")

    caption = str(pkg.get("caption") or "").strip()
    if not caption:
        errors.append("caption 이 비어 있어요")
    else:
        if len(caption) > 2200:
            errors.append(f"캡션 {len(caption)}자 > 2,200자")
        for w in BANNED + EXPERIENCE + BAIT:
            if w in caption:
                errors.append(f"캡션에 '{w}'")
        for w in _no_words(caption):
            errors.append(f"캡션에 '{w}' — 사람이 만든 카드뉴스처럼, 출처로 표현하세요")
    tags = pkg.get("hashtags") or []
    if not 3 <= len(tags) <= 5:
        errors.append(f"해시태그는 3~5개 (지금 {len(tags)}개)")
    if any(str(t).startswith("#") for t in tags):
        warns.append("hashtags 는 # 없이 적어요 (출력할 때 붙여요)")
    if not pkg.get("alt_text"):
        warns.append("alt_text 가 비어 있어요")
    for w in _no_words(str(pkg.get("alt_text") or "")):
        errors.append(f"alt_text 에 '{w}'")
    if pkg.get("highlight") and pkg["highlight"] not in set(HIGHLIGHTS.values()):
        warns.append(f"highlight '{pkg['highlight']}' 는 프로필 하이라이트(축제·팝업·맛집·혜택·시즌)가 아니에요")
    return errors, warns


def highlight_for(pkg: dict) -> str:
    """이 게시물을 모을 하이라이트. highlight 값이 없으면 분야(첫 번째로 맞는 것)로 정한다."""
    if pkg.get("highlight"):
        return str(pkg["highlight"])
    topic = pkg.get("topic") or {}
    if any(w in str(topic.get("title") or "") for w in SEASON_WORDS):
        return "시즌"
    cat = str(topic.get("category") or "")
    for part in re.split(r"[/·,|\s]+", cat):
        if part in HIGHLIGHTS:
            return HIGHLIGHTS[part]
    return ""


def cmd_check(args) -> int:
    day = _date(args.date)
    pkg = load_package(day)
    errors, warns = check_package(pkg)
    print(f"검수: 매일 카드뉴스 {day} — {(pkg.get('topic') or {}).get('title', '')}")
    for e in errors:
        print(f"  ✗ {e}")
    for w in warns:
        print(f"  ! {w}")
    print(f"  결과: 오류 {len(errors)} · 주의 {len(warns)} → {'통과' if not errors else '고친 뒤 다시 실행'}")
    return 1 if errors else 0


# ---------------------------------------------------------------- package.md

def style_block(style_key: str) -> str:
    st = load_yaml(STYLE_FILE) or {}
    preset = st["presets"][style_key]
    canvas = st.get("canvas") or {}
    rules = "\n".join(f"- {r}" for r in st.get("common_rules") or [])
    return (f"[공통 스타일 — 이 대화의 모든 이미지에 적용]\n"
            f"- 캔버스: {canvas.get('ratio')} ({canvas.get('size')}). {canvas.get('safe_margin')}.\n"
            f"- 디자인: {preset['style'].strip()}\n{rules}\n"
            f"이 스타일을 기억해 두고, 다음 메시지부터 '장별 요청'대로 한 장씩 만들어 주세요. 지금은 이미지를 만들지 말고 '준비됐어요'라고만 답해 주세요.")


def slide_prompt(s: dict, total: int) -> str:
    lines = [f"[{s['_no']}/{total}장 — 공통 스타일 그대로, 이전 장과 같은 시리즈로]"]
    role = s.get("role")
    lines.append(f"- 역할: {'표지' if role == 'cover' else '마지막 장' if role == 'cta' else '본문'}")
    lines.append(f"- 그림: {str(s.get('visual') or '').strip()}")
    lines.append("- 들어갈 글자 (이 문구만, 정확히):")
    # 날짜의 '/'(10/23)와 헷갈리지 않게 줄마다 따로 적는다
    hl = [x.strip() for x in str(s.get("headline") or "").split("\n") if x.strip()]
    if len(hl) == 1:
        lines.append(f"  · 큰 제목 (한 줄): \"{hl[0]}\"")
    else:
        lines += [f"  · 큰 제목 {n}번째 줄: \"{x}\"" for n, x in enumerate(hl, 1)]
    if s.get("sub"):
        lines.append(f"  · 작은 글씨: \"{s['sub']}\"")
    for x in s.get("info") or []:
        lines.append(f"  · 정보줄: \"{x}\"")
    if s.get("point"):
        lines.append(f"  · 한 줄 포인트: \"{s['point']}\"")
    lines.append("- 글자가 틀리거나 잘리면 고쳐서 다시 그려 주세요.")
    return "\n".join(lines)


def render_md(pkg: dict) -> str:
    day = str(pkg.get("date"))
    topic = pkg.get("topic") or {}
    slides = pkg.get("slides") or []
    facts = pkg.get("facts") or []
    out = [f"# {day} 오늘의 카드뉴스: {topic.get('title', '')}", ""]
    hl = highlight_for(pkg)
    out += [f"- 분야: {topic.get('category', '')} · 스타일: `{pkg.get('style')}` · {len(slides)}장"
            + (f" · 하이라이트: '{hl}'" if hl else ""),
            f"- 왜 오늘: {topic.get('why_now', '')}"]
    sc = topic.get("score") or {}
    if sc:
        out.append(f"- 선정 점수: {sc.get('total', '')} (시의성 {sc.get('timeliness')}, 저장·공유 {sc.get('save_share')}, "
                   f"대상 폭 {sc.get('breadth')}, 그림 {sc.get('visual')}, 확인 가능 {sc.get('verifiability')}, 위험 {sc.get('risk')})")
    if topic.get("trend_evidence"):
        out += ["", "## 트렌드 근거"]
        for ev in topic["trend_evidence"]:
            out.append(f"- [{ev.get('source', '')}] {ev.get('note', '')} — {ev.get('url', '')}")
    if pkg.get("backups"):
        out += ["", "## 예비 주제 (오늘 주제가 막히면)"]
        out += [f"- {b.get('title', '')} ({b.get('category', '')}) — {b.get('why_now', '')}" for b in pkg["backups"]]
    out += ["", "## 사실 확인표 (게시 전 한 번 눈으로 확인)", "",
            "| 항목 | 값 | 상태 | 출처 |", "|---|---|---|---|"]
    label = {"confirmed": "확정", "planned": "예정", "last_year": "작년 기준", "unverified": "미확인"}
    for f in facts:
        out.append(f"| {f.get('claim', '')} | {f.get('value', '')} | {label.get(f.get('status'), f.get('status'))} "
                   f"| [{f.get('source_type', '')}]({f.get('source_url', '')}) ({f.get('checked_at', '')}) |")
    out += ["", "## ChatGPT로 이미지 만들기", "",
            "1. ChatGPT에서 **새 대화**를 열고, 아래 '공통 스타일'을 먼저 붙여넣습니다 (이미지는 아직 안 만듦).",
            "2. '장별 요청'을 1장부터 **한 장씩** 붙여넣어 이미지를 받습니다. 같은 대화에서 해야 스타일이 이어져요.",
            "3. 받은 이미지마다 글자 오탈자·숫자·잘림을 확인하고, 틀리면 \"글자를 정확히 다시\"라고 요청합니다.",
            "4. 01, 02… 순서로 저장해 Instagram에 같은 순서로 올립니다.",
            "5. Instagram에서 첫 사진을 고르면 미리보기가 **정사각형으로 잘려** 있어요. 미리보기 왼쪽 아래 **⤢(크기) 버튼**을 "
            "눌러 세로로 길게 바꾼 **다음** 여러 장 선택을 누르세요. 게시 후에는 비율을 바꿀 수 없어요.", "",
            "### 공통 스타일 (1번만 붙여넣기)", "", "```text", style_block(pkg.get("style")), "```", "",
            "### 장별 요청"]
    for s in slides:
        out += ["", f"**{s['_no']}장 · {s.get('role')}**", "", "```text", slide_prompt(s, len(slides)), "```"]
    tags = " ".join("#" + str(t).lstrip("#") for t in pkg.get("hashtags") or [])
    out += ["", "## 캡션 (그대로 복사)", "", "```text", str(pkg.get("caption") or "").strip(), "", tags, "```", "",
            "## 대체 텍스트 (고급 설정 → 접근성)", "", "```text", str(pkg.get("alt_text") or ""), "```", "",
            "## 올리기 전 체크", "",
            "- [ ] 이미지 글자 오탈자·숫자가 사실 확인표와 같은지",
            "- [ ] 인스타 미리보기가 세로(⤢)이고, 1장 제목 첫 줄과 각 장 맨 아래 줄이 잘리지 않았는지",
            "- [ ] 로고·간판 글씨·실존 인물 얼굴·캐릭터가 그려지지 않았는지",
            "- [ ] 캡션 첫 줄이 '더 보기' 전에 보이는지",
            *([f"- [ ] 올린 게시물 → 공유(종이비행기) → 스토리에 추가 → 올린 스토리의 하이라이트 버튼 → '{hl}'에 추가"]
              if hl else []),
            "- [ ] 올린 뒤 이 파일의 status 를 posted 로 (또는 Claude에게 '올렸어'라고 알려 주기)"]
    if pkg.get("notes"):
        out += ["", "## 메모", "", str(pkg["notes"])]
    return "\n".join(out) + "\n"


def cmd_md(args) -> int:
    day = _date(args.date)
    pkg = load_package(day)
    errors, _ = check_package(pkg)
    if errors:
        print(f"검수 오류 {len(errors)}개가 있어 package.md 를 만들지 않았어요: python doha.py daily-check {day}")
        return 1
    out = package_path(day).with_name("package.md")
    out.write_text(render_md(pkg), encoding="utf-8")
    print(f"만들었어요: {out.relative_to(ROOT)}")
    return 0


def recent_topics(days: int = 14, before: str | None = None) -> list[dict]:
    """최근 패키지 주제 (중복 방지용)."""
    items = []
    if not DAILY_DIR.exists():
        return items
    for p in sorted(DAILY_DIR.glob("*/package.yaml"), reverse=True)[: days + 1]:
        if before and p.parent.name >= before:
            continue
        try:
            d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        items.append({"date": p.parent.name, "title": (d.get("topic") or {}).get("title", ""),
                      "category": (d.get("topic") or {}).get("category", "")})
    return items[:days]


def run(args) -> int:
    return {"daily-new": cmd_new, "daily-check": cmd_check, "daily-md": cmd_md}[args.command](args)
