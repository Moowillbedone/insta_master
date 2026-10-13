"""공통 유틸리티: 설정·페르소나·게시물 로딩, 경로, Chromium 찾기, 표시 문구 계산.

모든 모듈은 여기 있는 함수만 통해 설정과 게시물을 읽습니다.
"""
from __future__ import annotations

import csv
import io
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_env(path: Path | None = None) -> None:
    """저장소 루트의 .env 를 읽어 os.environ 에 없는 값만 채운다 (python-dotenv 없이)."""
    path = path or ROOT / ".env"
    if not path.exists():
        return
    # 메모장의 'UTF-8(BOM)' 저장본은 BOM 을 떼고(안 그러면 첫 키 이름이 바뀐다), ANSI(CP949) 저장본도 읽는다
    text, _ = _decode_csv(path.read_bytes())
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value


def load_yaml(path: Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_config() -> dict:
    return load_yaml(ROOT / "config.yaml")


def load_persona(config: dict | None = None) -> dict:
    config = config or load_config()
    return load_yaml(ROOT / config["paths"]["persona"])


def repo_path(*parts: str) -> Path:
    return ROOT.joinpath(*parts)


@dataclass
class Post:
    dir: Path
    data: dict

    @property
    def id(self) -> str:
        return self.data.get("id") or self.dir.name

    @property
    def out_dir(self) -> Path:
        return self.dir / "out"

    def image_path(self, key: str | None) -> Path | None:
        """images 키 → 실제 파일 경로. 키가 없거나 파일이 없으면 None (렌더러는 자리표시 이미지 사용)."""
        if not key:
            return None
        spec = (self.data.get("images") or {}).get(key)
        if not spec:
            return None
        p = self.dir / spec.get("file", f"images/{key}.png")
        return p if p.exists() else None

    def image_spec(self, key: str) -> dict:
        return (self.data.get("images") or {}).get(key) or {}

    def save(self) -> None:
        """post.yaml 을 다시 쓴다. 주석이 사라지므로 상태 필드 갱신에만 쓴다."""
        with open(self.dir / "post.yaml", "w", encoding="utf-8") as f:
            yaml.safe_dump(self.data, f, allow_unicode=True, sort_keys=False, width=1000)


def posts_root(config: dict | None = None) -> Path:
    config = config or load_config()
    return ROOT / config["paths"]["posts"]


def resolve_post(ref: str | os.PathLike) -> Post:
    """게시물 폴더 경로, post.yaml 경로, 또는 id(폴더 이름 일부)로 게시물을 찾는다."""
    p = Path(ref)
    if p.is_file() and p.name == "post.yaml":
        p = p.parent
    if not p.is_dir():
        folders = sorted(d for d in posts_root().iterdir() if d.is_dir())
        # 폴더 이름과 똑같으면 그걸로 ('…-niteu' 가 '…-niteu-wonpiseu' 의 일부여도 하나로 정해진다)
        candidates = [d for d in folders if d.name == str(ref)] or [d for d in folders if str(ref) in d.name]
        if len(candidates) != 1:
            names = ", ".join(d.name for d in candidates) or "없음"
            raise SystemExit(f"게시물을 하나로 특정할 수 없어요: '{ref}' (후보: {names})")
        p = candidates[0]
    yaml_path = p / "post.yaml"
    if not yaml_path.exists():
        raise SystemExit(f"post.yaml 이 없어요: {yaml_path}")
    return Post(dir=p.resolve(), data=load_yaml(yaml_path) or {})


def skip_if_legacy(post: Post) -> bool:
    """키트 이전 게시물(legacy: true)이면 안내를 출력하고 True. 제작 명령은 이 게시물을 건너뛴다."""
    if (post.data or {}).get("legacy"):
        print(f"{post.id}: 키트 이전 게시물(legacy)이라 건너뜀 — 성과 기록 연결용입니다.")
        return True
    return False


def list_posts() -> list[Post]:
    root = posts_root()
    return [resolve_post(d) for d in sorted(root.iterdir()) if (d / "post.yaml").exists()]


SHORTCODE_RE = re.compile(r"/(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)")


def shortcode(url) -> str | None:
    """Instagram 게시물 주소의 숏코드 ('…/p/DeYxcWMEUx8/' → 'DeYxcWMEUx8'). metrics.csv 의 'ig:숏코드' 와 같은 값."""
    m = SHORTCODE_RE.search(str(url)) if url else None
    return m.group(1) if m else None


def has_person(spec: dict | None) -> bool:
    """사진에 도하(가상인물)가 나오는지. images.<키>.person 이 있으면 그 값, 없으면 flatlay 만 인물 없음.

    detail(손·허리·다리 클로즈업)도 도하의 몸이므로 인물로 본다. 제품만 찍은 클로즈업이면 person: false.
    """
    spec = spec or {}
    if "person" in spec:
        return bool(spec["person"])
    return spec.get("framing") != "flatlay"


def disclosure_label(post_data: dict, persona: dict | None = None) -> str:
    """경제적 이해관계 표시 문구 (캡션 첫 줄 [ ] 안). 해당 없으면 빈 문자열.

    예: '광고 · 브랜드A' / '협찬 · 브랜드A' / '광고 · 제휴 링크' / '광고 · 브랜드A | 제휴 링크'
    짧게 유지한다: 뒤에 가상인물 고지가 이어져야 '더 보기' 전에 둘 다 보인다.
    수수료 문장(disclosure.affiliate_notice)은 build_caption 이 둘째 줄에 넣는다.
    """
    persona = persona or load_persona()
    labels = persona["disclosure"]["labels"]
    d = post_data.get("disclosure") or {}
    brand = (d.get("brand") or "").strip()
    parts = []
    if d.get("paid"):
        parts.append(labels["paid"] + (f" · {brand}" if brand else ""))
    elif d.get("gifted"):
        parts.append(labels["gifted"] + (f" · {brand}" if brand else ""))
    if d.get("affiliate"):
        # 제휴만 있으면 소비자가 가장 잘 알아보는 '광고'를 앞에 (docs/04 §5 권장안)
        parts.append(labels["affiliate"] if parts else f"{labels['paid']} · {labels['affiliate']}")
    return " | ".join(parts)


def short_disclosure_label(post_data: dict, persona: dict | None = None) -> str:
    """이미지 위에 얹는 짧은 표시 (커버 배지용)."""
    persona = persona or load_persona()
    labels = persona["disclosure"]["labels"]
    d = post_data.get("disclosure") or {}
    brand = (d.get("brand") or "").strip()
    if d.get("paid"):
        return labels["paid"] + (f" · {brand}" if brand else "")
    if d.get("gifted"):
        return labels["gifted"] + (f" · {brand}" if brand else "")
    if d.get("affiliate"):
        return "광고 · 제휴 링크"
    return ""


def find_chromium() -> str | None:
    """Playwright 기본 브라우저가 없을 때 쓸 Chromium 실행 파일 경로. 없으면 None (Playwright 기본값 사용)."""
    env = os.environ.get("CHROMIUM_PATH")
    if env and Path(env).exists():
        return env
    for cand in ("/opt/pw-browsers/chromium",):
        if Path(cand).exists():
            return cand
    return None


def launch_browser(playwright):
    """Playwright Chromium 실행. 기본 설치가 없으면 CHROMIUM_PATH → 설치된 Chrome·Edge → 시스템 Chromium 순으로 재시도."""
    try:
        return playwright.chromium.launch()
    except Exception as first_error:  # 브라우저 미설치 등
        env = os.environ.get("CHROMIUM_PATH")
        if not (env and Path(env).exists()):
            # Windows·macOS 의 Chrome·Edge 는 PATH 에 없다. Playwright 가 표준 설치 위치에서 찾아 준다
            for channel in ("chrome", "msedge"):
                try:
                    return playwright.chromium.launch(channel=channel)
                except Exception:
                    pass
        exe = find_chromium() or shutil.which("chromium") or shutil.which("google-chrome")
        if not exe:
            raise SystemExit(
                "Chromium을 찾을 수 없어요. `python -m playwright install chromium` 을 실행하거나 Chrome·Edge 를 설치하거나 "
                ".env 에 CHROMIUM_PATH 를 지정하세요.\n" + str(first_error)
            )
        return playwright.chromium.launch(executable_path=exe)


def _decode_csv(raw: bytes) -> tuple[str, str]:
    """CSV 바이트 → (글자, 인코딩). 엑셀 'CSV UTF-8' 의 BOM 은 떼고, 엑셀 기본 CSV(CP949)도 읽는다."""
    try:
        return raw.decode("utf-8-sig"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("cp949", errors="replace"), "cp949"


def append_csv(path: Path, row: dict, fieldnames: list[str]) -> None:
    """CSV에 한 줄 추가. 파일이 없으면 헤더부터 만든다.

    손으로 고친 파일도 망가뜨리지 않게: 마지막 줄에 줄바꿈이 없으면 먼저 넣고(안 그러면 새 줄이 앞 줄 끝에 붙는다),
    열 순서는 파일 헤더를 따르고, 파일 인코딩(UTF-8 / 엑셀 기본 CP949)을 유지한다.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = path.read_bytes() if path.exists() else b""
    text, encoding = _decode_csv(raw)
    header = [h.strip() for h in next(csv.reader(io.StringIO(text)), [])]
    if header and set(fieldnames) <= set(header):
        fieldnames = header
    elif header:
        missing = ", ".join(c for c in fieldnames if c not in header)
        print(f"주의: {path.name} 헤더에 없는 열이 있어요 → {missing}. 열 이름은 바꾸지 마세요 (tracking/README.md).",
              file=sys.stderr)
    with open(path, "a", newline="", encoding=encoding, errors="replace") as f:
        if raw and not raw.endswith((b"\n", b"\r")):
            f.write("\n")
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if not raw:
            w.writeheader()
        w.writerow(row)


def read_csv(path: Path) -> list[dict]:
    """CSV → [{열: 값}]. 엑셀이 붙이는 BOM, CP949 저장본도 읽고 열 이름 앞뒤 공백은 지운다."""
    if not path.exists():
        return []
    text, _ = _decode_csv(path.read_bytes())
    return [{k.strip(): v for k, v in row.items() if k} for row in csv.DictReader(io.StringIO(text))]
