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
  python doha.py ig-publish black-slacks --dry-run   # 4:5 JPEG 준비·검사 (승인 후 --dry-run 빼면 API 게시)
  python doha.py x-new 2026-10-20              # X 게시 대기열 뼈대 (content/x/2026-10-20.yaml)
  python doha.py x-check 2026-10-20            # X 글자 수·링크·멘션·참여 유도·중복·광고 표시 검수
  python doha.py x-digest 2026-10-20           # 휴대폰 미리보기 out/x/2026-10-20/digest.html + digest.md
  python doha.py x-approve 2026-10-20          # 하루 1번 승인 (--ids a,c 일부만)
  python doha.py x-publish --due               # cron: 게시 시각이 된 승인 글만 게시 (--dry-run 으로 미리 보기)
  python doha.py x-metrics                     # X 지표·팔로워 기록, 수익화 기준까지 남은 거리
  python doha.py x-targets                     # 댓글 초안 후보 모으기 (댓글은 사람이 앱에서 직접)
  python doha.py daily-new 2026-10-20          # 매일 정보형 카드뉴스 패키지 뼈대
  python doha.py daily-check 2026-10-20        # 출처·글자 길이·꼬리표·AI 표기 검수
  python doha.py daily-md 2026-10-20           # ChatGPT 프롬프트가 든 package.md 만들기

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
    "ig-publish": ("doha.igpublish", "승인된 게시물을 Instagram API로 게시 (R2 임시 업로드, --dry-run·--mock·--refresh-token)"),
    "x-new": ("doha.xqueue", "X 게시 대기열 뼈대 만들기 (content/x/<날짜>.yaml, 덮어쓰지 않음)"),
    "x-check": ("doha.xqueue", "X 대기열 검수: 가중 글자 수·링크·해시태그·멘션·참여 유도·체험 표현·중복·광고 표시"),
    "x-approve": ("doha.xqueue", "X 대기열 승인 (하루 1번, 검수 오류가 있으면 거부, --ids·--undo)"),
    "x-digest": ("doha.xqueue", "X 승인용 미리보기: 휴대폰 카드 HTML + 채팅용 Markdown + 댓글 초안 앱 링크"),
    "x-publish": ("doha.xpublish", "승인된 X 글을 게시 시각에 API로 게시 (--due·--dry-run, manual 모드는 앱 링크만)"),
    "x-metrics": ("doha.xpublish", "X 글 지표·팔로워 기록 + 수익화(OCR) 기준까지 남은 거리 (API 키 필요)"),
    "x-targets": ("doha.xpublish", "지켜보는 계정의 최근 글을 댓글 초안 후보로 추가 (댓글은 사람이 직접)"),
    "daily-new": ("doha.daily", "매일 정보형 카드뉴스 패키지 뼈대 (content/daily/<날짜>/package.yaml)"),
    "daily-check": ("doha.daily", "매일 패키지 검수: 출처·확인일, 이미지 글자 길이, 꼬리표, AI 표기, 해시태그"),
    "daily-md": ("doha.daily", "매일 패키지 → package.md (ChatGPT 공통 스타일·장별 프롬프트·캡션·체크리스트)"),
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
