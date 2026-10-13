"""HTML → PNG/PDF 렌더링 공통 도구 (카드뉴스, 릴스 오버레이, 미디어킷이 함께 씀).

- 폰트는 assets/fonts 의 woff2 를 file:// 절대경로로 불러온다 (인터넷 없이 렌더링).
- 템플릿은 templates/ 아래 Jinja2 파일.
- 브라우저는 한 번만 띄우고 여러 장을 연속으로 찍는다.
"""
from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Iterable

from doha.core import ROOT, launch_browser, load_config

FONT_FACES = [
    # (family, weight, file)
    ("Pretendard", 400, "Pretendard-Regular.woff2"),
    ("Pretendard", 500, "Pretendard-Medium.woff2"),
    ("Pretendard", 600, "Pretendard-SemiBold.woff2"),
    ("Pretendard", 700, "Pretendard-Bold.woff2"),
    ("Pretendard", 800, "Pretendard-ExtraBold.woff2"),
    ("Noto Serif KR", 500, "NotoSerifKR-500.woff2"),
    ("Noto Serif KR", 700, "NotoSerifKR-700.woff2"),
    ("Cormorant Garamond", 500, "CormorantGaramond-Medium.woff2"),
    ("Cormorant Garamond", 600, "CormorantGaramond-SemiBold.woff2"),
]


def fonts_css() -> str:
    """@font-face 선언 (file:// 경로). 템플릿의 <style> 맨 앞에 넣는다."""
    font_dir = ROOT / load_config()["paths"]["fonts"]
    rules = []
    for family, weight, file in FONT_FACES:
        url = (font_dir / file).resolve().as_uri()
        rules.append(
            f"@font-face{{font-family:'{family}';font-weight:{weight};font-style:normal;"
            f"font-display:block;src:url('{url}') format('woff2');}}"
        )
    return "\n".join(rules)


def file_uri(path: Path | None) -> str | None:
    return path.resolve().as_uri() if path else None


def data_uri(path: Path) -> str:
    """이미지를 data URI로 (미리보기 HTML처럼 파일을 옮겨도 깨지지 않아야 할 때)."""
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def jinja_env():
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    env = Environment(
        loader=FileSystemLoader(str(ROOT / "templates")),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    # "\n" 으로 지정한 줄바꿈을 <br>로 (나머지는 이스케이프 유지)
    from markupsafe import Markup, escape

    env.filters["br"] = lambda s: Markup("<br>".join(escape(x) for x in str(s or "").split("\n")))
    env.globals["fonts_css"] = fonts_css
    return env


def render_template(name: str, **ctx) -> str:
    return jinja_env().get_template(name).render(**ctx)


def screenshot_pages(
    pages: Iterable[tuple[str, Path]],
    width: int,
    height: int,
    transparent: bool = False,
    device_scale_factor: float = 1,
) -> list[Path]:
    """(html, 출력경로) 목록을 같은 크기의 PNG로 찍는다. 폰트 로딩을 기다린 뒤 촬영."""
    from playwright.sync_api import sync_playwright

    outs: list[Path] = []
    with sync_playwright() as p:
        browser = launch_browser(p)
        page = browser.new_page(
            viewport={"width": width, "height": height}, device_scale_factor=device_scale_factor
        )
        for html, out in pages:
            out = Path(out)
            out.parent.mkdir(parents=True, exist_ok=True)
            # file:// 리소스(폰트·이미지)를 읽을 수 있도록 임시 파일로 연다
            tmp = out.with_suffix(".render.html")
            tmp.write_text(html, encoding="utf-8")
            page.goto(tmp.resolve().as_uri(), wait_until="load")
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(50)
            page.screenshot(path=str(out), omit_background=transparent, full_page=False)
            tmp.unlink(missing_ok=True)
            outs.append(out)
        browser.close()
    return outs


def html_to_pdf(html: str, out: Path, width: str = "210mm", height: str = "297mm") -> Path:
    """HTML 문서를 PDF로 (미디어킷용). 배경색·이미지를 그대로 인쇄."""
    from playwright.sync_api import sync_playwright

    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".render.html")
    tmp.write_text(html, encoding="utf-8")
    with sync_playwright() as p:
        browser = launch_browser(p)
        page = browser.new_page()
        page.goto(tmp.resolve().as_uri(), wait_until="load")
        page.evaluate("document.fonts.ready")
        page.pdf(path=str(out), width=width, height=height, print_background=True,
                 margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
        browser.close()
    tmp.unlink(missing_ok=True)
    return out
