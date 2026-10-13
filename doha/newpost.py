"""새 게시물 만들기 (new): content/posts/<날짜>-<슬러그>/post.yaml 뼈대와 images/ 폴더.

  python doha.py new "베이지 트렌치 날씨별 3가지" --date 2026-10-17
  python doha.py new "베이지 트렌치 날씨별 3가지" --date 2026-10-17 --slug beige-trench-3ways --series "한 벌 3가지"

슬러그를 안 주면 제목을 로마자로 바꿔 만든다 (예: beiji-teurenchi-nalssibyeol-3gaji).
이미 있는 폴더는 덮어쓰지 않는다.
"""
from __future__ import annotations

import json
import re
from datetime import date

import yaml

from doha.check import as_time
from doha.core import ROOT, load_config, posts_root

TEMPLATE = "post-template.yaml"

# 국어의 로마자 표기법 (음절 단위 단순 변환 — 슬러그용이라 자음 동화는 생략)
_INITIAL = ["g", "kk", "n", "d", "tt", "r", "m", "b", "pp", "s", "ss", "", "j", "jj", "ch", "k", "t", "p", "h"]
_MEDIAL = ["a", "ae", "ya", "yae", "eo", "e", "yeo", "ye", "o", "wa", "wae", "oe", "yo", "u", "wo", "we", "wi",
           "yu", "eu", "ui", "i"]
_FINAL = ["", "k", "k", "k", "n", "n", "n", "t", "l", "k", "m", "l", "l", "l", "p", "l", "m", "p", "p", "t", "t",
          "ng", "t", "t", "k", "t", "p", "t"]


def romanize(text: str) -> str:
    out = []
    for ch in text:
        code = ord(ch) - 0xAC00
        if 0 <= code < 11172:
            i, rest = divmod(code, 588)
            m, f = divmod(rest, 28)
            out.append(_INITIAL[i] + _MEDIAL[m] + _FINAL[f])
        else:
            out.append(ch)
    return "".join(out)


def slugify(text: str, max_words: int = 4, max_len: int = 40) -> str:
    """ASCII 소문자·숫자·하이픈만 남긴 슬러그. 만들 수 없으면 빈 문자열."""
    words = re.findall(r"[a-z0-9]+", romanize(text).lower())
    slug = "-".join(words[:max_words])[:max_len].strip("-")
    return slug


def _yaml_str(s: str) -> str:
    # JSON 문자열은 YAML 큰따옴표 문자열로도 유효하다 (따옴표·역슬래시·콜론 안전)
    return json.dumps(s, ensure_ascii=False)


def add_arguments(parser) -> None:
    parser.add_argument("title", help="제목/hook (커버·릴스 첫 장면·캡션 첫 줄에 들어감)")
    parser.add_argument("--date", required=True, help="게시 예정일 YYYY-MM-DD")
    parser.add_argument("--slug", help="영어 슬러그 (예: beige-trench-3ways). 없으면 제목을 로마자로 변환")
    parser.add_argument("--series", default="", help="시리즈 이름 (예: '한 벌 3가지')")
    parser.add_argument("--format", choices=["carousel", "reel", "both"], default="both", help="기본 both")
    parser.add_argument("--time", help="게시 시각 HH:MM (기본: config.publishing.default_time)")


def _strip_section(text: str, name: str, replacement: str) -> str:
    """'# [name]' … '# [/name]' 사이를 replacement 로 바꾼다 (주석은 유지)."""
    pattern = re.compile(rf"^# \[{name}\]\n.*?^# \[/{name}\]\n", re.S | re.M)
    return pattern.sub(replacement, text)


def run(args) -> int:
    config = load_config()
    title = " ".join(str(args.title).split())  # 줄바꿈·연속 공백 정리 (hook 은 한 줄)
    if not title:
        print("제목(hook)을 입력하세요.")
        return 2
    try:
        day = date.fromisoformat(args.date)
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.date):
            raise ValueError
    except ValueError:
        print(f"--date 는 YYYY-MM-DD 형식이어야 해요: {args.date}")
        return 2
    post_time = as_time(args.time or (config.get("publishing") or {}).get("default_time") or "07:40")
    if not post_time:
        print(f"--time 은 HH:MM 형식이어야 해요: {args.time}")
        return 2

    root = posts_root(config)
    if args.slug:
        slug = slugify(args.slug, max_words=8, max_len=48)
        if not slug:
            print(f"슬러그는 영문 소문자·숫자·하이픈으로 적어주세요: {args.slug}")
            return 2
        derived = False
    else:
        slug, derived = slugify(title), True
        if not slug:  # 제목이 기호뿐이면 번호로
            n = 1
            while (root / f"{day.isoformat()}-post-{n}").exists():
                n += 1
            slug, derived = f"post-{n}", False
            print("제목에서 슬러그를 만들 수 없어 번호를 붙였어요. 영어 슬러그는 --slug 로 주세요.")
    post_id = f"{day.isoformat()}-{slug}"
    folder = root / post_id
    if folder.exists():
        print(f"이미 있는 게시물이에요 (덮어쓰지 않아요): {folder.relative_to(ROOT)}")
        print("다른 --slug 를 주거나 기존 폴더를 확인하세요.")
        return 1

    text = (ROOT / config["paths"]["templates"] / TEMPLATE).read_text(encoding="utf-8")
    if args.format == "reel":
        text = _strip_section(text, "carousel", "slides: []   # 릴스 전용 게시물\n")
    elif args.format == "carousel":
        text = _strip_section(text, "reel", "reel:\n  audio: null\n  scenes: []   # 카드뉴스 전용 게시물\n")
    text = text.replace("# [carousel]\n", "").replace("# [/carousel]\n", "")
    text = text.replace("# [reel]\n", "").replace("# [/reel]\n", "")
    for key, value in {
        "{{ID}}": post_id,
        "{{DATE}}": day.isoformat(),
        "{{TIME}}": post_time,
        "{{SERIES}}": _yaml_str(args.series),
        "{{FORMAT}}": args.format,
        "{{HOOK_LINE}}": title,
        "{{HOOK}}": _yaml_str(title),
    }.items():
        text = text.replace(key, value)

    data = yaml.safe_load(text)  # 템플릿이 깨졌으면 파일을 만들기 전에 멈춘다
    if data.get("id") != post_id or data.get("hook") != title:
        raise SystemExit("템플릿 치환 결과가 이상해요. templates/post-template.yaml 을 확인하세요.")

    (folder / "images").mkdir(parents=True)
    (folder / "images" / ".gitkeep").write_text("", encoding="utf-8")
    (folder / "post.yaml").write_text(text, encoding="utf-8")

    rel = folder.relative_to(ROOT).as_posix()
    print(f"새 게시물을 만들었어요: {rel}/post.yaml")
    if derived:
        print(f"슬러그 '{slug}' 는 제목을 로마자로 바꾼 거예요. 영어 슬러그가 좋으면 폴더를 지우고 --slug 로 다시 만드세요.")
    print("다음 순서:")
    print(f"  1. {rel}/post.yaml 의 TODO 채우기 (예시: content/posts/2026-10-15-black-slacks-3ways/post.yaml)")
    print(f"  2. python doha.py prompts {post_id}    # 이미지 프롬프트 (비용 없음)")
    print(f"  3. python doha.py check {post_id}")
    print(f"  4. python doha.py build {post_id}")
    return 0
