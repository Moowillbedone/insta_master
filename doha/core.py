"""공통 유틸리티: 설정·페르소나·게시물 로딩, 경로, Chromium 찾기, 표시 문구 계산.

모든 모듈은 여기 있는 함수만 통해 설정과 게시물을 읽습니다.
"""
from __future__ import annotations

import csv
import os
import shutil
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
    for line in path.read_text(encoding="utf-8").splitlines():
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
        candidates = sorted(d for d in posts_root().iterdir() if d.is_dir() and str(ref) in d.name)
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


def disclosure_label(post_data: dict, persona: dict | None = None) -> str:
    """경제적 이해관계 표시 문구. 해당 없으면 빈 문자열.

    예: '광고 · 브랜드A' / '협찬 · 브랜드A' / '광고 · 브랜드A | 제휴 링크 포함 · 링크로 구매하시면 수수료를 받습니다'
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
        parts.append(labels["affiliate"])
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
    """Playwright Chromium 실행. 기본 설치가 없으면 시스템/환경변수 Chromium으로 재시도."""
    try:
        return playwright.chromium.launch()
    except Exception as first_error:  # 브라우저 미설치 등
        exe = find_chromium() or shutil.which("chromium") or shutil.which("google-chrome")
        if not exe:
            raise SystemExit(
                "Chromium을 찾을 수 없어요. `python -m playwright install chromium` 을 실행하거나 "
                ".env 에 CHROMIUM_PATH 를 지정하세요.\n" + str(first_error)
            )
        return playwright.chromium.launch(executable_path=exe)


def append_csv(path: Path, row: dict, fieldnames: list[str]) -> None:
    """CSV에 한 줄 추가. 파일이 없으면 헤더부터 만든다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists() or path.stat().st_size == 0
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(row)


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))
