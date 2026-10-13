"""이미지 프롬프트 내보내기(prompts)와 OpenAI 이미지 생성(generate).

- prompts : API 비용 없이 ChatGPT 앱에 붙여넣을 프롬프트를 <post>/out/prompts.md 로 만든다.
- generate: OpenAI Images API 호출(비용 발생). 호출 전에 예상 비용을 계산해 한도·확인을 거친다.

프롬프트 = 촬영 스타일 + 인물(identity) + 시그니처 소품 + 의상 + 장면 + 프레이밍 + 글자 자리 + 금지 조건.
인물·스타일은 brand/doha.yaml, 의상·장면은 post.yaml 의 images.<키> 에서 온다 (brand/prompt-guide.md).

테스트 전용 환경변수:
  DOHA_TRACKING_DIR  costs.csv 를 쓸 폴더를 바꾼다 (기본: config.paths.tracking). 운영에서는 비워 둔다.
"""
from __future__ import annotations

import base64
import copy
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

import yaml

from doha.core import ROOT, Post, append_csv, load_config, load_persona, resolve_post, skip_if_legacy

COST_FIELDS = ["date", "category", "provider", "description", "post_id",
               "amount_usd", "amount_krw", "quantity", "notes"]

# 기준 이미지 1장당 입력 토큰 여유분 (추정치). 실제 단가는 모델·이미지 크기마다 다르다.
REF_MARGIN_USD = 0.01

FRAMING = {
    "full-body": "full-body, head to shoes in frame with a little floor visible, head and shoes clear of the edges",
    "three-quarter": "three-quarter length shot from mid-thigh up",
    "waist-up": "waist-up shot, face and upper outfit clearly visible",
    "detail": "close-up detail shot of the outfit (fabric texture, buttons, accessories); the face may be cropped out",
    "flatlay": "top-down flat lay shot straight from above, no person and no hands in frame",
}

# 사진 위에 글자가 얹히는 레이아웃과 그 자리 (templates/ 기준). 나머지 슬라이드는 글자를 사진 밖 패널에 둔다.
# cover 는 슬라이드의 text_position(top|bottom)을 따르고, images.<키>.text_space 로 직접 정할 수도 있다.
OVERLAY_ZONE = {"cover": "upper", "reel-hook": "upper", "reel-look": "lower"}
# 사진을 가로로 넓게 잘라 쓰는 레이아웃의 대략적인 가로:세로 비율 (render.PHOTO_FRAC, reel.WINDOW 기준)
WIDE_CROP = {"look": 1.1, "reel-end": 1.2, "product": 1.4, "cta": 1.6, "checklist": 1.9}
# 좌우가 많이 잘리는 자리: 9:16 전면 릴스, 비교 슬라이드의 반쪽 칸
NARROW_CROP = {"reel-hook", "reel-look", "compare"}

REFERENCE_NOTE = ("Reference photos are attached: keep exactly the same face, hairstyle and skin tone as the "
                  "reference person; take the outfit, pose and setting only from this prompt.")

CHATGPT_LEAD = "Generate one photorealistic image in vertical 2:3 portrait format ({size})."

# 인물이 없는 사진에서는 손·피부 관련 금지어를 빼서 오히려 손이 그려지는 것을 막는다
PERSON_ONLY_NEGATIVE = re.compile(r"finger|hand|skin|makeup", re.I)


# ── 프롬프트 조합 ──────────────────────────────────────────────

def _clean(text: object) -> str:
    return " ".join(str(text or "").split()).strip().rstrip(".")


def has_person(spec: dict) -> bool:
    if "person" in spec:
        return bool(spec["person"])
    return spec.get("framing") != "flatlay"


def face_references(persona: dict) -> tuple[list[Path], list[str]]:
    """(존재하는 기준 이미지, 목록엔 있지만 파일이 없는 항목)."""
    found, missing = [], []
    for item in (persona.get("visual") or {}).get("face_reference") or []:
        p = Path(item) if Path(item).is_absolute() else ROOT / item
        if p.is_file():
            found.append(p)
        else:
            missing.append(str(item))
    return found, missing


def image_usage(post: Post, key: str) -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
    """이 이미지를 쓰는 (슬라이드 번호, 레이아웃), (릴스 장면 번호, 레이아웃)."""
    slides = []
    for i, s in enumerate(post.data.get("slides") or [], 1):
        sides = [(s.get(side) or {}).get("image") for side in ("left", "right")]
        if s.get("image") == key or key in sides:
            slides.append((i, s.get("layout", "")))
    scenes = [(i, s.get("layout", "")) for i, s in enumerate((post.data.get("reel") or {}).get("scenes") or [], 1)
              if s.get("image") == key]
    return slides, scenes


def text_zones(post: Post, key: str) -> list[str]:
    """사진 위에 글자가 얹히는 자리: [], ['upper'], ['lower'], ['upper', 'lower']."""
    override = post.image_spec(key).get("text_space")
    if override:
        return {"none": [], "both": ["upper", "lower"]}.get(override, [override])
    zones = set()
    for s in post.data.get("slides") or []:
        if s.get("image") == key and s.get("layout") == "cover":
            zones.add("lower" if s.get("text_position") == "bottom" else "upper")
    for s in (post.data.get("reel") or {}).get("scenes") or []:
        if s.get("image") == key and s.get("layout") in OVERLAY_ZONE:
            zones.add(OVERLAY_ZONE[s["layout"]])
    return [z for z in ("upper", "lower") if z in zones]


def composition_note(post: Post, key: str) -> str:
    """글자 자리와 크롭(릴스 9:16, 가로로 넓은 슬라이드 칸)을 알려 주는 한 줄."""
    zones = text_zones(post, key)
    person = has_person(post.image_spec(key))
    face = "her face" if person else "the main items"
    parts = []
    if zones == ["upper"]:
        parts.append(f"leave negative space for text in the upper third (plain, low-contrast background), {face} below it")
    elif zones == ["lower"]:
        # 아래쪽은 보통 옷이 있는 자리라 비우라고 하지 않고 단순하게만 (릴스 자막 카드가 얹힘)
        parts.append(f"keep the lower third low-contrast and uncluttered for a text overlay, {face} well above it")
    elif zones:
        parts.append(f"keep the upper and lower thirds plain and low-contrast for text, {face} clear of them")
    slides, scenes = image_usage(post, key)
    layouts = {lay for _, lay in slides} | {lay for _, lay in scenes}
    if layouts & NARROW_CROP:
        parts.append("subject horizontally centered with side margins (also cropped to 9:16)")
    wide = [WIDE_CROP[lay] for lay in layouts if lay in WIDE_CROP]
    if wide:
        what = "her face and the key outfit pieces" if person else "the key items"
        parts.append(f"keep {what} within the middle band (also cropped to about {max(wide):.1f}:1)")
    return "; ".join(parts)


def compose_prompt(post: Post, key: str, persona: dict, with_reference: bool | None = None) -> str:
    """이미지 한 장의 전체 영어 프롬프트. 같은 입력이면 항상 같은 문자열."""
    spec = post.image_spec(key)
    if not spec:
        raise KeyError(key)
    visual = persona.get("visual") or {}
    person = has_person(spec)
    if with_reference is None:
        with_reference = person and bool(face_references(persona)[0])

    lines = [f"Style: {_clean(visual.get('photography'))}."]
    if person:
        lines.append(f"Model (the same woman in every image): {_clean(visual.get('identity'))}.")
        sig = [_clean(s) for s in visual.get("signature_details") or []]
        if sig:
            lines.append("Signature details: " + "; ".join(sig) + ".")
        if with_reference:
            lines.append(REFERENCE_NOTE)
    if spec.get("outfit"):
        lines.append(f"{'Outfit' if person else 'Items'}: {_clean(spec['outfit'])}.")
    if spec.get("prompt"):
        lines.append(f"Scene: {_clean(spec['prompt'])}.")
    framing = FRAMING.get(spec.get("framing", ""), _clean(spec.get("framing")))
    if framing:
        lines.append(f"Framing: {framing}.")
    comp = composition_note(post, key)
    if comp:
        lines.append(f"Composition: {comp}.")

    negative = [_clean(n) for n in _clean(visual.get("negative")).split(",") if n.strip()]
    if person:
        negative += [_clean(a) for a in visual.get("avoid_identity") or []]
    else:
        negative = [n for n in negative if not PERSON_ONLY_NEGATIVE.search(n)]
    if negative:
        lines.append("Constraints: " + "; ".join(negative) + ".")
    return "\n".join(lines)


def compose_reference_prompts(persona: dict) -> list[tuple[str, str]]:
    """얼굴 기준 이미지(정면·3/4·상반신)용 프롬프트. (권장 파일 이름, 프롬프트)."""
    visual = persona.get("visual") or {}
    style = ("Style: photorealistic portrait photograph for a character reference, full-frame camera, "
             "85mm lens at f/4, soft even window daylight, true-to-life skin texture with visible pores, "
             "neutral color, plain warm light-gray seamless background, vertical 2:3 framing.")
    ident = f"Model: {_clean(visual.get('identity'))}."
    shots = [
        ("doha-face-01.png", "head-and-shoulders, facing the camera straight on, eyes to camera, "
                             "neutral relaxed expression with closed lips, hair down"),
        ("doha-face-02.png", "head-and-shoulders, head turned about 30 degrees to her left, eyes to camera, "
                             "soft natural smile, hair down, the mole under the left eye visible"),
        ("doha-face-03.png", "waist-up, standing with arms relaxed, plain ivory crew-neck knit, "
                             "showing hair length, shoulders and build"),
    ]
    negative = [_clean(n) for n in _clean(visual.get("negative")).split(",") if n.strip()]
    negative += [_clean(a) for a in visual.get("avoid_identity") or []]
    out = []
    for name, shot in shots:
        text = "\n".join([style, ident, f"Shot: {shot}; only small gold huggie earrings as jewelry.",
                          "Constraints: " + "; ".join(negative) + "."])
        out.append((name, text))
    return out


# ── 공통 ─────────────────────────────────────────────────────

def _selected_keys(post: Post, only: str | None) -> list[str]:
    keys = list((post.data.get("images") or {}).keys())
    if not only:
        return keys
    picked = list(dict.fromkeys(k.strip() for k in only.split(",") if k.strip()))
    unknown = [k for k in picked if k not in keys]
    if unknown:
        raise SystemExit(f"post.yaml images 에 없는 키: {', '.join(unknown)} (있는 키: {', '.join(keys) or '없음'})")
    return picked


def _image_target(post: Post, key: str) -> Path:
    return post.dir / post.image_spec(key).get("file", f"images/{key}.png")


def _rel(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def _today(config: dict) -> date:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo(config.get("publishing", {}).get("timezone", "Asia/Seoul"))).date()
    except Exception:  # tzdata 가 없는 환경
        return date.today()


def tracking_dir(config: dict) -> Path:
    env = os.environ.get("DOHA_TRACKING_DIR")
    return Path(env) if env else ROOT / config["paths"]["tracking"]


def _redact(text: str) -> str:
    return re.sub(r"sk-[A-Za-z0-9_\-*]{4,}", "sk-***", text)


# ── prompts 명령 ─────────────────────────────────────────────

def build_prompts_md(post: Post, keys: list[str], persona: dict, config: dict) -> tuple[str, list[dict]]:
    gen = config.get("image_generation") or {}
    size = gen.get("size", "1024x1536")
    refs, missing = face_references(persona)
    rows = []
    md = [
        f"# 이미지 프롬프트 · {post.id}",
        "",
        f"> 만든 날 {_today(config).isoformat()} · 권장 크기 {size} (2:3 세로) · {len(keys)}장  ",
        "> `python doha.py prompts` 가 다시 만드는 파일이에요. 고칠 내용은 post.yaml(의상·장면)이나 "
        "brand/doha.yaml(인물·스타일)에 쓰세요.",
        "",
        "## 비용 0원 경로 · ChatGPT 앱",
        "",
        "ChatGPT 유료 플랜에는 이미지 생성이 포함돼 있어 API 비용이 따로 들지 않아요 (플랜별 사용 한도는 있어요).",
        "",
        "1. ChatGPT 앱에서 **이미지마다 새 채팅**을 엽니다 (앞 이미지의 영향을 줄이기 위해).",
        "2. 항목의 '첨부'에 적힌 얼굴 기준 이미지를 먼저 첨부합니다. 없으면 첨부 없이 진행해요.",
        "3. 아래 `text` 블록 전체를 복사해 붙여넣고 보냅니다. 첫 줄이 비율(2:3 세로)을 지정해요.",
        "4. 결과를 [검수 체크리스트](../../../../brand/prompt-guide.md)로 확인합니다. 고칠 곳이 있으면 같은 채팅에서 "
        "\"얼굴과 옷은 그대로 두고 ○○만 바꿔 주세요\"처럼 한 가지씩 요청해요.",
        "5. 마음에 드는 이미지를 내려받아 항목의 **저장 위치**에 PNG로 저장합니다 (파일 이름 그대로).",
        f"6. `post.yaml` 의 `images.<키>.status` 를 `generated` 로 바꾸고, 렌더링으로 글자 배치를 확인해요: "
        f"`python doha.py render {post.id}`",
        "",
    ]
    if not refs:
        md += ["> 아직 승인된 얼굴 기준 이미지가 없어요. 처음 몇 장은 첨부 없이 만들고, 마음에 드는 얼굴을 "
               "`brand/reference/README.md` 순서대로 저장한 뒤 `brand/doha.yaml` 의 `face_reference` 에 적어 주세요.", ""]
    if missing:
        md += [f"> ⚠ face_reference 에 적혔지만 파일이 없어요: {', '.join(missing)}", ""]

    for key in keys:
        spec = post.image_spec(key)
        person = has_person(spec)
        prompt = compose_prompt(post, key, persona)
        target = _image_target(post, key)
        slides, scenes = image_usage(post, key)
        usage = [f"슬라이드 {i} ({lay})" for i, lay in slides] + [f"릴스 장면 {i} ({lay})" for i, lay in scenes]
        others = [k for k, s in (post.data.get("images") or {}).items()
                  if k != key and (s or {}).get("status") in ("generated", "approved") and post.image_path(k)
                  and has_person(s or {}) == person]
        md += [f"## {key} · {spec.get('framing', '-')} · 상태 `{spec.get('status', 'todo')}`", ""]
        md.append(f"- 저장 위치: `{_rel(target)}`" + (" (이미 있음 — 새로 저장하면 기존 파일은 다른 이름으로 보관하세요)"
                                                   if target.exists() else ""))
        md.append(f"- 쓰이는 곳: {', '.join(usage) or '아직 없음'}")
        md.append(f"- 권장 크기: {size} (2:3 세로)")
        if not person:
            md.append("- 첨부: 없음 (인물 없는 사진)")
        elif refs:
            md.append("- 첨부: " + ", ".join(f"`{_rel(r)}`" for r in refs))
        else:
            md.append("- 첨부: 없음 (얼굴 기준 이미지 미승인)")
        if others:
            md.append("- 선택 첨부 (옷·톤 일관성): " + ", ".join(f"`{_rel(post.image_path(k))}`" for k in others))
        md += [f"- 프롬프트 ({len(prompt):,}자):", "", "```text",
               CHATGPT_LEAD.format(size=size), prompt, "```", ""]
        rows.append({"key": key, "framing": spec.get("framing", "-"), "chars": len(prompt),
                     "refs": len(refs) if person else 0, "exists": target.exists()})
    return "\n".join(md), rows


def run_prompts(args) -> int:
    config, persona = load_config(), load_persona()
    if args.reference:
        print("# 얼굴 기준 이미지용 프롬프트 (ChatGPT 앱에 하나씩 붙여넣기 · brand/reference/README.md 참고)\n")
        for name, text in compose_reference_prompts(persona):
            print(f"## brand/reference/{name}\n")
            print(CHATGPT_LEAD.format(size=config["image_generation"].get("size", "1024x1536")))
            print(text + "\n")
        return 0
    if not args.post:
        raise SystemExit("게시물을 지정하세요: python doha.py prompts <게시물>  (또는 --reference)")
    post = resolve_post(args.post)
    if skip_if_legacy(post):
        return 0
    keys = _selected_keys(post, args.only)
    if not keys:
        raise SystemExit("post.yaml 에 images 항목이 없어요.")
    text, rows = build_prompts_md(post, keys, persona, config)
    out = post.out_dir / "prompts.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text + "\n", encoding="utf-8")

    refs = face_references(persona)[0]
    print(f"프롬프트 {len(rows)}개 → {_rel(out)}")
    for r in rows:
        print(f"  {r['key']:<5} {r['framing']:<13} {r['chars']:>5,}자  첨부 {r['refs']}장"
              + ("  (이미지 있음)" if r["exists"] else ""))
    print(f"얼굴 기준 이미지: {len(refs)}장" + ("" if refs else " — brand/reference/README.md 참고"))
    print("다음: ChatGPT 앱에 붙여넣기 → images/<키>.png 로 저장 → status: generated → render")
    return 0


# ── post.yaml 상태 한 줄만 고치기 ─────────────────────────────

def _replace_status_line(text: str, key: str, status: str) -> str | None:
    """images.<key>.status 줄만 바꾼 텍스트. 구조를 확신할 수 없으면 None."""
    lines = text.splitlines(keepends=True)
    bare = [ln.rstrip("\r\n") for ln in lines]
    start = next((i for i, ln in enumerate(bare) if re.match(r"^images:[ \t]*(#.*)?$", ln)), None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(bare)) if re.match(r"^[^\s#]", bare[i])), len(bare))
    key_re = re.compile(rf"^(?P<ind>[ ]+){re.escape(key)}:[ \t]*(#.*)?$")
    k = next((i for i in range(start + 1, end) if key_re.match(bare[i])), None)
    if k is None:
        return None  # 키가 없거나 {…} 한 줄 형식
    key_indent = len(key_re.match(bare[k]).group("ind"))
    child_indent, status_idx = None, None
    for i in range(k + 1, end):
        stripped = bare[i].lstrip(" ")
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(bare[i]) - len(stripped)
        if indent <= key_indent:
            break
        if child_indent is None:
            child_indent = indent
        # 같은 깊이의 status: 만 (프롬프트 본문처럼 더 깊은 줄은 무시)
        if indent == child_indent and re.match(r"status:(\s|$)", stripped):
            status_idx = i
            break
    eol = lines[k][len(bare[k]):] or "\n"
    if status_idx is None:
        lines.insert(k + 1, " " * (child_indent or key_indent + 2) + f"status: {status}{eol}")
        return "".join(lines)
    m = re.match(r"^(?P<pre>[ ]*status:)[ \t]*(?P<val>\"[^\"]*\"|'[^']*'|[^#]*?)(?P<post>[ \t]*(#.*)?)$",
                 bare[status_idx])
    if not m:
        return None
    lines[status_idx] = f"{m.group('pre')} {status}{m.group('post')}" + lines[status_idx][len(bare[status_idx]):]
    return "".join(lines)


def update_image_status(post: Post, key: str, status: str) -> bool:
    """post.yaml 의 images.<key>.status 한 줄만 바꾼다 (주석·순서 유지). 실패하면 False, 파일은 그대로."""
    path = post.dir / "post.yaml"
    text = path.read_text(encoding="utf-8")
    new_text = _replace_status_line(text, key, status)
    if new_text is None:
        return False
    # 바뀐 것이 그 필드 하나뿐인지 파싱해서 확인한 뒤에만 쓴다
    before = yaml.safe_load(text) or {}
    expected = copy.deepcopy(before)
    try:
        expected["images"][key]["status"] = status
    except (KeyError, TypeError):
        return False
    if yaml.safe_load(new_text) != expected:
        return False
    tmp = path.with_suffix(".yaml.tmp")
    tmp.write_text(new_text, encoding="utf-8")
    os.replace(tmp, path)
    post.data.setdefault("images", {}).setdefault(key, {})["status"] = status
    return True


# ── 파일 저장 ────────────────────────────────────────────────

def _next_version_path(target: Path) -> Path:
    pat = re.compile(re.escape(target.stem) + r"\.v(\d+)" + re.escape(target.suffix) + "$")
    nums = [int(m.group(1)) for p in target.parent.iterdir() if (m := pat.match(p.name))]
    return target.with_name(f"{target.stem}.v{max(nums, default=0) + 1}{target.suffix}")


def save_versioned(target: Path, data: bytes) -> Path | None:
    """target 에 쓴다. 이미 있으면 <이름>.vN.png 로 옮겨 보관하고, 보관한 경로를 돌려준다."""
    target.parent.mkdir(parents=True, exist_ok=True)
    archived = None
    if target.exists():
        archived = _next_version_path(target)
        target.rename(archived)
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, target)
    return archived


def save_candidates(target: Path, images: list[bytes]) -> list[str]:
    """후보 여러 장 저장. 후보 1이 target 이 되도록 거꾸로 저장하고, 어디에 무엇이 있는지 설명을 돌려준다."""
    current = "이전 이미지" if target.exists() else None
    placed: list[tuple[str, Path]] = []
    for i in range(len(images), 0, -1):
        archived = save_versioned(target, images[i - 1])
        if archived and current:
            placed.append((current, archived))
        current = f"후보 {i}" if len(images) > 1 else "새 이미지"
    placed.append((current, target))
    return [f"{label} → {_rel(p)}" for label, p in reversed(placed)]


def _to_png(data: bytes) -> bytes:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return data
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.open(io.BytesIO(data)).save(buf, format="PNG")
    return buf.getvalue()


def _parse_size(size: str) -> tuple[int, int]:
    m = re.match(r"^(\d+)x(\d+)$", str(size))
    return (int(m.group(1)), int(m.group(2))) if m else (1024, 1536)


def mock_image(post: Post, key: str, size: str) -> bytes:
    """오프라인 테스트용 자리표시 PNG. 글자 자리·크롭 가이드를 그려 레이아웃 확인에도 쓴다."""
    import io

    from PIL import Image, ImageDraw, ImageFont

    w, h = _parse_size(size)
    img = Image.new("RGB", (w, h), "#D8D0C4")
    d = ImageDraw.Draw(img)
    font_dir = ROOT / load_config()["paths"]["fonts"]

    def font(px: int, bold: bool = True):
        try:
            return ImageFont.truetype(str(font_dir / ("Pretendard-Bold.woff2" if bold else "Pretendard-Regular.woff2")), px)
        except OSError:  # woff2 를 못 읽는 Pillow → 기본 글꼴 (한글은 깨져도 MOCK 은 보임)
            try:
                return ImageFont.load_default(size=px)
            except TypeError:
                return ImageFont.load_default()

    for zone in text_zones(post, key):
        y0 = 0 if zone == "upper" else h * 2 // 3
        d.rectangle([0, y0, w, y0 + h // 3], fill="#C9BFB1")
        for x in range(-h, w, 36):
            d.line([(x, y0), (x + h // 3, y0 + h // 3)], fill="#BFB4A5", width=2)
        d.text((w // 2, y0 + h // 6), f"TEXT AREA · {zone} third", fill="#6E655A", font=font(30), anchor="mm")
    # 3:4 카드뉴스 크롭(위아래), 9:16 릴스 크롭(좌우)
    crop_h = int(w * 4 / 3)
    top = (h - crop_h) // 2
    d.rectangle([2, top, w - 3, top + crop_h], outline="#8C7B66", width=3)
    crop_w = int(h * 9 / 16)
    left = (w - crop_w) // 2
    for x in (left, left + crop_w):
        d.line([(x, 0), (x, h)], fill="#5C6B80", width=3)
    d.text((12, top + 8), "3:4 crop", fill="#8C7B66", font=font(22, False))
    d.text((left + 8, h - 40), "9:16 crop", fill="#5C6B80", font=font(22, False))

    spec = post.image_spec(key)
    cy = h // 2
    d.rectangle([60, cy - 150, w - 60, cy + 150], fill="#F4EFE8", outline="#2B2B2B", width=4)
    d.text((w // 2, cy - 85), "MOCK · 테스트용 자리표시", fill="#B03A2E", font=font(52), anchor="mm")
    d.text((w // 2, cy - 10), f"{post.id[:34]}", fill="#2B2B2B", font=font(28, False), anchor="mm")
    d.text((w // 2, cy + 40), f"{key} · {spec.get('framing', '-')}", fill="#2B2B2B", font=font(40), anchor="mm")
    d.text((w // 2, cy + 105), "AI 생성 이미지 아님 · 게시 금지", fill="#B03A2E", font=font(30), anchor="mm")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ── 비용 ─────────────────────────────────────────────────────

def estimate_usd(gen: dict, quality: str, n: int, n_refs: int) -> float:
    return n * float(gen["est_cost_usd"][quality]) + n_refs * REF_MARGIN_USD


def _attr(obj, name: str):
    if obj is None:
        return None
    return obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)


def usage_cost(usage, gen: dict) -> tuple[float | None, str]:
    """응답 usage → (계산한 금액 또는 None, 토큰 요약). 단가는 config 에 있을 때만 계산."""
    if usage is None:
        return None, ""
    inp, out = _attr(usage, "input_tokens") or 0, _attr(usage, "output_tokens") or 0
    details = _attr(usage, "input_tokens_details")
    text_in, image_in = _attr(details, "text_tokens"), _attr(details, "image_tokens")
    summary = f"tokens in={inp}" + (f"(text {text_in}, image {image_in})" if details is not None else "") + f" out={out}"
    prices = gen.get("token_prices_usd_per_1m") or {}
    if not prices or "image_output" not in prices:
        return None, summary
    if details is None:
        text_in, image_in = inp, 0
    cost = ((text_in or 0) * float(prices.get("text_input", 0)) + (image_in or 0) * float(prices.get("image_input", 0))
            + out * float(prices["image_output"])) / 1_000_000
    return cost, summary


def log_cost(config: dict, post: Post, key: str, model: str, size: str, quality: str,
             amount_usd: float, quantity: int, notes: str) -> Path:
    path = tracking_dir(config) / "costs.csv"
    fx = float((config.get("fx") or {}).get("usd_krw", 0))
    append_csv(path, {
        "date": _today(config).isoformat(), "category": "image_api", "provider": "openai",
        "description": f"{model} {size} {quality} {post.id}/{key}", "post_id": post.id,
        "amount_usd": f"{amount_usd:.4f}", "amount_krw": round(amount_usd * fx),
        "quantity": quantity, "notes": notes,
    }, COST_FIELDS)
    return path


# ── OpenAI 호출 ──────────────────────────────────────────────

def _make_client():
    from openai import OpenAI

    # 고화질은 1~2분 걸릴 수 있다. 재시도는 1번만 (한도 초과 시 같은 요청 반복을 줄이려고)
    return OpenAI(timeout=300, max_retries=1)


def _call_api(client, mode: str, model: str, prompt: str, size: str, quality: str, n: int, refs: list[Path]):
    """(응답, input_fidelity 사용 여부)."""
    import openai

    kwargs = dict(model=model, prompt=prompt, size=size, quality=quality, n=n, output_format="png")
    if mode != "edit":
        return client.images.generate(**kwargs), False

    def edit(**extra):
        files = [open(p, "rb") for p in refs]
        try:
            return client.images.edit(image=files, **kwargs, **extra)
        finally:
            for f in files:
                f.close()

    try:
        return edit(input_fidelity="high"), True
    except openai.BadRequestError as e:
        if "input_fidelity" not in str(e):
            raise
        return edit(), False  # 이 모델은 input_fidelity 미지원 → 빼고 다시


def explain_error(e: Exception, model: str) -> tuple[str, bool]:
    """(한국어 설명, 나머지 이미지도 멈춰야 하는지)."""
    import openai

    body = getattr(e, "body", None)
    raw = body.get("message") if isinstance(body, dict) and body.get("message") else getattr(e, "message", None)
    raw = _redact(str(raw or e))
    code = str(getattr(e, "code", "") or "")
    param = str(getattr(e, "param", "") or "")
    low = (raw + " " + code).lower()
    model_hint = (f"config.yaml 의 image_generation.model 을 바꿔 보세요 (현재 '{model}' → 예: gpt-image-1.5, gpt-image-1).")

    if isinstance(e, openai.APIConnectionError):  # APITimeoutError 포함
        kind = "응답 시간 초과" if isinstance(e, openai.APITimeoutError) else "연결 실패"
        return (f"OpenAI 서버 {kind}: 인터넷·VPN·회사 방화벽/프록시를 확인하고 잠시 뒤 다시 실행하세요. "
                "보통 이 경우엔 비용이 청구되지 않지만, 시간 초과였다면 사용량 페이지에서 한 번 확인하세요.", True)
    if isinstance(e, openai.AuthenticationError):
        return ("API 키가 올바르지 않아요 (401). .env 의 OPENAI_API_KEY 를 다시 확인하세요. "
                "키는 채팅·문서에 붙여넣지 마세요.", True)
    if isinstance(e, openai.PermissionDeniedError):
        if "verif" in low:
            return ("조직 인증(Organization verification) 필요: gpt-image 모델은 OpenAI 플랫폼에서 조직 인증을 마쳐야 써요. "
                    "platform.openai.com → Settings → Organization → General → 'Verify Organization' 을 진행한 뒤 "
                    "반영까지 15분 정도 기다렸다가 다시 실행하세요. 기다리는 동안은 `python doha.py prompts` 로 "
                    "ChatGPT 앱에서 만들 수 있어요.", True)
        return (f"권한이 없어요 (403): 이 API 키의 프로젝트에서 '{model}' 사용이 막혀 있을 수 있어요. "
                f"플랫폼의 Project → Limits/Models 설정을 확인하세요. 원문: {raw}", True)
    if isinstance(e, openai.RateLimitError) or "billing_hard_limit" in low:
        if "quota" in low or "billing" in low:
            return ("크레딧·결제 한도 부족: platform.openai.com → Billing 에서 잔액과 월 한도를 확인하세요 "
                    "(ChatGPT 구독과 API 결제는 별개예요).", True)
        return ("요청 한도 초과 (429): 1~2분 기다린 뒤 `--only` 로 남은 이미지만 다시 실행하세요.", True)
    if isinstance(e, openai.NotFoundError) or code == "model_not_found" or param == "model" or (
            "model" in low and ("does not exist" in low or "not found" in low)):
        return f"모델 '{model}' 을(를) 쓸 수 없어요. {model_hint} 원문: {raw}", True
    if code in ("moderation_blocked", "content_policy_violation") or "safety" in low or "moderation" in low:
        return ("안전 정책에 걸려 생성이 거절됐어요. 장면·의상 묘사에서 신체를 강조하는 표현, 실존 인물·브랜드 이름을 "
                "빼고 다시 써 보세요 (brand/prompt-guide.md 참고). 비용은 청구되지 않을 수 있지만 사용량 페이지에서 "
                "확인하세요.", False)
    if isinstance(e, openai.BadRequestError):
        hint = {"size": "config.image_generation.size 를 1024x1536 으로 바꿔 보세요.",
                "quality": "--quality 를 low/medium/high 중 하나로 지정하세요.",
                "image": "기준 이미지 파일 형식(PNG/JPG/WebP, 50MB 이하)을 확인하세요."}.get(param, "")
        return f"요청이 거절됐어요 (400). {hint} 원문: {raw}", False
    if isinstance(e, openai.InternalServerError):
        return "OpenAI 서버 오류 (5xx). 잠시 뒤 다시 실행하세요.", True
    if isinstance(e, openai.APIStatusError):
        return f"API 오류 ({e.status_code}): {raw}", True
    return f"예상하지 못한 오류: {type(e).__name__}: {raw}", True


# ── generate 명령 ────────────────────────────────────────────

def _max_cost(args, gen: dict) -> tuple[float, str]:
    if args.max_cost is not None:
        return float(args.max_cost), "--max-cost"
    env = os.environ.get("DOHA_MAX_COST_USD", "").strip()
    if env:
        try:
            return float(env), "DOHA_MAX_COST_USD"
        except ValueError:
            print(f"DOHA_MAX_COST_USD 값이 숫자가 아니라 무시해요: {env!r}")
    return float(gen.get("max_cost_per_run_usd", 1.0)), "config"


def _confirm(question: str) -> bool:
    if not sys.stdin.isatty():
        print("터미널이 아니어서 비용 확인을 받을 수 없어요. 금액을 확인했다면 --yes 를 붙여 다시 실행하세요.")
        return False
    try:
        return input(f"{question} [y/N] ").strip().lower() in ("y", "yes")
    except EOFError:
        return False


def run_generate(args, config: dict | None = None, persona: dict | None = None) -> int:
    config = config or load_config()
    persona = persona or load_persona(config)
    gen = config.get("image_generation") or {}
    model, size = gen.get("model", "gpt-image-1"), gen.get("size", "1024x1536")
    quality = args.quality or gen.get("quality", "medium")
    if quality not in (gen.get("est_cost_usd") or {}):
        raise SystemExit(f"config.image_generation.est_cost_usd 에 '{quality}' 단가가 없어요.")
    if not 1 <= args.n <= 10:
        raise SystemExit("--n 은 1~10 사이여야 해요.")

    post = resolve_post(args.post)

    if skip_if_legacy(post):

        return 0
    keys = _selected_keys(post, args.only)
    if not args.only:  # 승인된 이미지는 --only 로 직접 지정할 때만 다시 만든다
        skipped = [k for k in keys if post.image_spec(k).get("status") == "approved"]
        keys = [k for k in keys if k not in skipped]
        if skipped:
            print(f"승인된 이미지는 건너뛰어요: {', '.join(skipped)} (다시 만들려면 --only)")
    if not keys:
        print("만들 이미지가 없어요.")
        return 0

    refs, missing = face_references(persona)
    if missing:
        print(f"⚠ face_reference 에 적혔지만 파일이 없어요: {', '.join(missing)}")
    plan = []
    for key in keys:
        person = has_person(post.image_spec(key))
        mode = "edit" if refs and person else "generate"
        n_refs = len(refs) if mode == "edit" else 0
        plan.append({"key": key, "mode": mode, "refs": refs if mode == "edit" else [],
                     "prompt": compose_prompt(post, key, persona, with_reference=mode == "edit"),
                     "est": estimate_usd(gen, quality, args.n, n_refs)})
    total = sum(p["est"] for p in plan)
    fx = float((config.get("fx") or {}).get("usd_krw", 0))
    limit, limit_src = _max_cost(args, gen)

    label = "미리보기(dry-run)" if args.dry_run else ("목업" if args.mock else "생성 계획")
    print(f"{label} · {post.id} · {model} {size} quality={quality} n={args.n}")
    for p in plan:
        how = f"edit + 기준 {len(p['refs'])}장" if p["mode"] == "edit" else "generate (기준 이미지 없음)"
        print(f"  {p['key']:<5} {post.image_spec(p['key']).get('framing', '-'):<13} 예상 ${p['est']:.3f}  {how}")
    print(f"  예상 합계 ${total:.2f} (약 ₩{round(total * fx):,}) · 한도 ${limit:.2f} ({limit_src})"
          + ("" if args.mock else "  ※ 추정치 — 실제 청구는 입력 토큰에 따라 달라질 수 있어요"))

    if args.dry_run:
        for p in plan:
            print(f"\n── {p['key']} ({len(p['prompt']):,}자) " + "─" * 30)
            print(p["prompt"])
        if total > limit and not args.mock:
            print("\n⚠ 예상 비용이 한도를 넘어서 실제 실행은 거절돼요. --only 로 나누거나 --max-cost 를 올리세요.")
        print("\n(dry-run: API를 호출하지 않았어요)")
        return 0

    if args.mock:
        for p in plan:
            target = _image_target(post, p["key"])
            for line in save_candidates(target, [mock_image(post, p["key"], size) for _ in range(args.n)]):
                print(f"  {p['key']}: {line}")
        print("목업 이미지만 만들었어요. API 호출·비용 기록·post.yaml 상태 변경은 하지 않았어요.")
        return 0

    if total > limit:
        print(f"예상 비용 ${total:.2f} 가 한도 ${limit:.2f} ({limit_src}) 를 넘어서 멈춰요. "
              "--only 로 나눠 실행하거나 --max-cost 로 한도를 명시하세요.")
        return 1
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        print("OPENAI_API_KEY 가 설정돼 있지 않아요.\n"
              "  1) .env.example 을 .env 로 복사하고 OPENAI_API_KEY= 뒤에 키를 넣으세요 (.env 는 git에 올라가지 않아요).\n"
              "  2) 키는 platform.openai.com → API keys 에서 만들고, Billing 에서 크레딧을 충전해야 해요 "
              "(ChatGPT 구독과 별도 · docs/00-master-plan.md '이미지 생성 API 비용과 준비 상태').\n"
              "  키를 채팅·문서에 붙여넣지 마세요. 비용 없이 만들려면: python doha.py prompts " + post.id)
        return 1
    if gen.get("require_confirmation", True) and not args.yes:
        if not _confirm(f"예상 ${total:.2f} (약 ₩{round(total * fx):,}) 비용이 발생해요. 진행할까요?"):
            print("취소했어요. API를 호출하지 않았어요.")
            return 1

    try:
        client = _make_client()
    except ImportError:
        print("openai 패키지가 없어요: pip install -r requirements.txt")
        return 1

    failed = 0
    for p in plan:
        key = p["key"]
        print(f"→ {key} 생성 중 ({p['mode']})…", flush=True)
        try:
            resp, used_fidelity = _call_api(client, p["mode"], model, p["prompt"], size, quality, args.n, p["refs"])
        except Exception as e:  # noqa: BLE001 — 사용자에게 원인을 설명하고 멈춤 여부를 정한다
            msg, fatal = explain_error(e, model)
            print(f"  ✗ {key}: {msg}")
            failed += 1
            if fatal:
                rest = [q["key"] for q in plan[plan.index(p) + 1:]]
                if rest:
                    print(f"  남은 이미지는 건너뛰어요: {', '.join(rest)}")
                failed += len(rest)
                break
            continue

        encoded = [d.b64_json for d in (resp.data or []) if getattr(d, "b64_json", None)]
        computed, tokens = usage_cost(getattr(resp, "usage", None), gen)
        amount = computed if computed is not None else p["est"]
        if computed is not None:
            basis = "usage-based (token_prices_usd_per_1m)"
        else:
            basis = "estimate (config est_cost_usd" + (
                f" + refs {len(p['refs'])}x${REF_MARGIN_USD:.2f})" if p["refs"] else ")")
        mode_note = p["mode"] + (f" refs={len(p['refs'])}" if p["refs"] else "") + (
            " input_fidelity=high" if used_fidelity else "")
        notes = "; ".join(x for x in (basis, mode_note, tokens) if x)
        # 응답을 받았으면 비용이 발생한 것이므로 저장 전에 먼저 기록한다
        log_path = log_cost(config, post, key, model, size, quality, amount, len(encoded) or args.n, notes)
        images = [_to_png(base64.b64decode(b64)) for b64 in encoded]
        if not images:
            print(f"  ✗ {key}: 응답에 이미지가 없어요 (비용은 {_rel(log_path)} 에 기록).")
            failed += 1
            continue
        for line in save_candidates(_image_target(post, key), images):
            print(f"  ✓ {key}: {line}")
        print(f"    비용 ${amount:.3f} ({'usage' if computed is not None else '추정'}) → {_rel(log_path)}")
        if update_image_status(post, key, "generated"):
            print(f"    post.yaml images.{key}.status → generated")
        else:
            print(f"    ⚠ post.yaml 을 자동으로 고치지 못했어요. images.{key}.status 를 직접 generated 로 바꿔 주세요.")

    if failed:
        print(f"완료: 성공 {len(plan) - failed} · 실패/건너뜀 {failed}")
        return 1
    print("완료. 사람이 검수(brand/prompt-guide.md 체크리스트)한 뒤에만 approved 로 바꾸세요.")
    return 0


# ── CLI ──────────────────────────────────────────────────────

def add_arguments(parser, command_name: str = "prompts") -> None:
    if command_name == "prompts":
        parser.add_argument("post", nargs="?", help="게시물 폴더·id 일부 (예: black-slacks)")
        parser.add_argument("--only", help="쉼표로 구분한 이미지 키 (예: s01,s02)")
        parser.add_argument("--reference", action="store_true", help="얼굴 기준 이미지용 프롬프트만 출력")
        return
    parser.add_argument("post", help="게시물 폴더·id 일부 (예: black-slacks)")
    parser.add_argument("--only", help="쉼표로 구분한 이미지 키 (예: s01). 승인된 이미지는 여기서 지정해야 다시 만듦")
    parser.add_argument("--quality", choices=["low", "medium", "high"], help="기본: config.image_generation.quality")
    parser.add_argument("--n", type=int, default=1, help="키마다 만들 후보 수 (기본 1)")
    parser.add_argument("--dry-run", action="store_true", help="프롬프트와 예상 비용만 보기 (API 호출 없음)")
    parser.add_argument("--yes", action="store_true", help="비용 확인 질문 건너뛰기")
    parser.add_argument("--max-cost", type=float, help="이번 실행 최대 금액 USD (기본: DOHA_MAX_COST_USD 또는 config)")
    parser.add_argument("--mock", action="store_true", help="API 없이 자리표시 PNG만 저장 (오프라인 테스트용, 비용 기록 없음)")


def run(args) -> int:
    if getattr(args, "command", "prompts") == "generate":
        return run_generate(args)
    return run_prompts(args)
