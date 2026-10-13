"""한 번에 만들기 (build): check → render → reel → preview.

  python doha.py build black-slacks
  python doha.py build black-slacks --skip-reel --size 4x5
  python doha.py build black-slacks --force     # 검수 오류가 있어도 시안만 만들어 보기 (게시 금지)

게시는 하지 않는다. 마지막에 인스타그램 앱에서 사람이 할 일을 출력한다.
"""
from __future__ import annotations

import time
from pathlib import Path

from doha.check import check_post, counts, format_report, post_format
from doha.core import ROOT, load_config, load_persona, resolve_post, skip_if_legacy


def add_arguments(parser) -> None:
    parser.add_argument("post", help="게시물 id 일부, 폴더 또는 post.yaml 경로")
    parser.add_argument("--skip-reel", action="store_true", help="릴스 MP4 만들기 건너뛰기 (있던 파일은 그대로 미리보기에 씀)")
    parser.add_argument("--size", choices=["3x4", "4x5"], default="3x4",
                        help="카드뉴스 비율: 3x4=1080x1440 (기본), 4x5=1080x1350")
    parser.add_argument("--force", action="store_true", help="검수 오류가 있어도 계속 (시안 확인용 — 게시 금지)")


def _rel(p: Path | None) -> str:
    if p is None:
        return "-"
    try:
        return Path(p).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(p)


def _step(title: str) -> float:
    print(f"\n== {title}")
    return time.monotonic()


def _call(module_name: str, func_name: str, *args, **kwargs):
    """다른 모듈을 늦게 불러 실행. 실패하면 (None, 이유)."""
    import importlib

    try:
        module = importlib.import_module(f"doha.{module_name}")
    except ImportError as e:
        return None, f"doha/{module_name}.py 를 불러올 수 없어요 ({e}). 모듈이 아직 없거나 의존성이 빠졌어요 (pip install -r requirements.txt)."
    func = getattr(module, func_name, None)
    if func is None:
        return None, f"doha/{module_name}.py 에 {func_name}() 이 없어요."
    try:
        return func(*args, **kwargs), None
    except SystemExit as e:  # 하위 모듈이 사용자용 메시지로 멈춘 경우
        return None, str(e.code) if e.code not in (None, 0, 1) else f"{module_name} 단계가 멈췄어요."
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def run(args) -> int:
    config = load_config()
    persona = load_persona(config)
    post = resolve_post(args.post)
    if skip_if_legacy(post):
        return 0
    has_c, has_r = post_format(post.data)
    failures: list[str] = []
    started = time.monotonic()

    t = _step("1/4 검수 (check)")
    issues = check_post(post, persona, config)
    print(format_report(post.id, issues))
    n_err, n_warn = counts(issues)
    if n_err and not args.force:
        print("\n오류가 있어 멈췄어요. post.yaml 을 고친 뒤 다시 실행하세요.")
        print("시안만 먼저 보려면 --force (오류가 남은 결과물은 게시하지 마세요).")
        return 1

    slides: list[Path] = []
    if has_c:
        t = _step(f"2/4 카드뉴스 렌더링 (render, {args.size})")
        out, err = _call("render", "render_post", post, canvas=args.size)
        if err:
            print(f"렌더링 실패: {err}")
            print("슬라이드 없이는 미리보기를 만들 수 없어 여기서 멈춰요.")
            return 1
        slides = [Path(p) for p in (out or [])]
        print(f"슬라이드 {len(slides)}장 ({time.monotonic() - t:.0f}초 걸림)")
    else:
        _step("2/4 카드뉴스 — format: reel 이라 건너뜀")

    reel_path: Path | None = None
    if has_r and not args.skip_reel:
        t = _step("3/4 릴스 만들기 (reel)")
        out, err = _call("reel", "make_reel", post)
        if err:
            failures.append("reel")
            print(f"릴스 실패: {err}")
            if not has_c:
                return 1
            print("카드뉴스 미리보기는 계속 만들어요.")
        else:
            reel_path = Path(out)
            print(f"릴스 완료 ({time.monotonic() - t:.0f}초 걸림)")
    elif has_r:
        _step("3/4 릴스 — --skip-reel 로 건너뜀 (기존 파일이 있으면 미리보기에 씀)")
    else:
        _step("3/4 릴스 — format: carousel 이라 건너뜀")

    t = _step("4/4 미리보기 (preview)")
    from doha.preview import build_preview, posting_checklist, print_result

    result = build_preview(post, persona, config, issues=issues)
    print_result(result)
    if not result["ok"]:
        print(result["message"])
        return 1

    d = post.data
    print(f"\n== 완료 ({time.monotonic() - started:.0f}초)")
    print(f"게시물     {post.id}  ·  {d.get('date')} {d.get('time') or ''} 게시 예정")
    print(f"검수       오류 {n_err} · 주의 {n_warn}")
    if slides:
        print(f"카드뉴스   {_rel(slides[0].parent)}/  01–{len(slides):02d}.png ({len(slides)}장, {args.size})")
    reel_file = reel_path or result.get("reel")
    if has_r:
        secs = result.get("reel_seconds")
        print(f"릴스       {_rel(reel_file)}" + (f" ({secs:.1f}초)" if reel_file and secs else "" if reel_file else " (없음)"))
        print(f"릴스 커버  {_rel(result.get('cover'))}")
    caption_len = len(result["caption"].read_text(encoding="utf-8").rstrip("\n"))
    print(f"캡션       {_rel(result['caption'])} ({caption_len:,}자)")
    print(f"연락시트   {_rel(result['contact_sheet'])}")
    print(f"미리보기   {_rel(result['preview'])}")

    print("\n앱에서 직접 게시할 때 체크리스트 (자동 게시·DM 자동화 없음, 사람이 확인 후 게시):")
    for item in posting_checklist(post, persona, len(slides) if has_c else None):
        print(f"  [ ] {item}")

    if n_err:
        print(f"\n!! 검수 오류 {n_err}개가 남아 있어요 (--force). 이 결과물은 게시하지 마세요.")
    if failures:
        print(f"\n일부 단계 실패: {', '.join(failures)}")
    return 1 if (n_err or failures) else 0
