#!/usr/bin/env python3
"""도하 운영 키트 명령줄 도구.

사용 예:
  python doha.py new "베이지 트렌치 날씨별 3가지" --date 2026-10-17
  python doha.py prompts black-slacks          # 이미지 프롬프트 내보내기 (ChatGPT 앱에 붙여넣기용)
  python doha.py generate black-slacks --only s01 --dry-run
  python doha.py check black-slacks            # 광고·AI 표시, 체험 표현, 상품 출처 검수
  python doha.py render black-slacks           # 카드뉴스 PNG
  python doha.py reel black-slacks             # 릴스 MP4
  python doha.py preview black-slacks          # 연락시트 + 휴대폰 미리보기 + caption.txt
  python doha.py build black-slacks            # check → render → reel → preview 한 번에
  python doha.py insights --followers          # Instagram API로 지표 자동 기록 (선택)
  python doha.py metrics                       # 성과 분석 리포트
  python doha.py media-kit                     # 브랜드 제안용 미디어킷 PDF
  python doha.py board                         # 운영 보드 데이터 갱신

각 하위 명령은 doha/<모듈>.py 의 add_arguments(parser), run(args) 로 구현됩니다.
"""
from __future__ import annotations

import argparse
import importlib
import inspect
import os
import sys

from doha.core import load_env

# 하위 명령 → (모듈, 설명)
COMMANDS: dict[str, tuple[str, str]] = {
    "new": ("doha.newpost", "새 게시물 폴더와 post.yaml 뼈대 만들기"),
    "prompts": ("doha.imagegen", "이미지 프롬프트 내보내기 (API 비용 없음)"),
    "generate": ("doha.imagegen", "OpenAI API로 이미지 생성 (비용 발생, 확인 후 실행)"),
    "check": ("doha.check", "게시 전 검수: 광고·AI 표시, 체험 표현, 상품 출처, 글자 수"),
    "render": ("doha.render", "카드뉴스 슬라이드 PNG 렌더링"),
    "reel": ("doha.reel", "릴스 MP4 만들기"),
    "preview": ("doha.preview", "연락시트·휴대폰 미리보기·붙여넣기용 캡션 만들기"),
    "build": ("doha.build", "check → render → reel → preview 한 번에"),
    "insights": ("doha.insights", "Instagram API로 게시물 지표 가져와 metrics.csv에 기록 (토큰 필요)"),
    "metrics": ("doha.metrics", "성과·수익·비용 분석 리포트"),
    "media-kit": ("doha.mediakit", "브랜드 제안용 미디어킷 HTML/PDF"),
    "board": ("doha.board", "운영 보드(index.html) 데이터 파일 갱신"),
}


def _load(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as e:
        # 선택 의존성(playwright, openai 등)이 없을 때 원인을 바로 보여준다
        raise SystemExit(f"'{module_name}' 을(를) 불러오지 못했어요: {e}. `pip install -r requirements.txt` 를 확인하세요.")


def _utf8_output() -> None:
    """Windows 에서 출력이 파이프·파일(Git Bash, `> log.txt`)이면 ANSI 코드 페이지(cp949)로 쓰여 '—'·'✓' 에서 멈춘다.

    UTF-8 로 바꾼다 (콘솔·macOS·Linux 는 이미 UTF-8 이라 그대로). PYTHONIOENCODING 을 직접 정했으면 그 인코딩은 두고
    못 쓰는 글자만 '?' 로 바꾼다.
    """
    for stream in (sys.stdout, sys.stderr):
        if not hasattr(stream, "reconfigure"):
            continue
        if (stream.encoding or "").lower().replace("-", "").replace("_", "") == "utf8":
            continue
        if os.environ.get("PYTHONIOENCODING"):
            stream.reconfigure(errors="replace")
        else:
            stream.reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    _utf8_output()
    load_env()
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(prog="doha", description="도하 콘텐츠·수익화 운영 키트")
    sub = parser.add_subparsers(dest="command", required=True)
    # 고른 명령의 모듈만 불러온다: 한 모듈의 의존성 문제가 다른 명령을 막지 않게
    chosen = next((a for a in argv if not a.startswith("-")), None)
    for name, (module_name, help_text) in COMMANDS.items():
        sp = sub.add_parser(name, help=help_text, description=help_text)
        sp.set_defaults(_module=module_name)
        if name == chosen:
            module = _load(module_name)
            # 같은 모듈이 여러 명령을 맡을 때 명령 이름을 넘겨 인자를 구분한다
            if len(inspect.signature(module.add_arguments).parameters) >= 2:
                module.add_arguments(sp, name)
            else:
                module.add_arguments(sp)
    args = parser.parse_args(argv)
    return int(_load(args._module).run(args) or 0)


if __name__ == "__main__":
    sys.exit(main())
