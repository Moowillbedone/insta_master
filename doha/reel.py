"""릴스 MP4 만들기 (9:16, 30fps).

장면마다 배경(사진, 없으면 자리표시) → 켄 번스 움직임 → 오버레이 2겹(고정 배지·스크림 / 등장하는 글자)
→ 장면 사이 크로스페이드 → 음원(없으면 무음 트랙) 을 ffmpeg 한 번으로 합성한다.

  python doha.py reel <게시물> [--keep-frames]
  from doha.reel import make_reel; make_reel(post) -> <post>/out/reel/reel.mp4
"""
from __future__ import annotations

import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from doha.core import Post, load_config, load_persona, resolve_post, short_disclosure_label, skip_if_legacy

LAYOUTS = ("reel-hook", "reel-look", "reel-text", "reel-end")
MOTIONS = ("zoom-in", "zoom-out", "pan-left", "pan-right", "still")
NO_PERSON_FRAMINGS = {"flatlay", "detail"}

MARGIN = 72                 # 왼쪽 여백 (안전 영역 60보다 안쪽)
TOP_Y = 268                 # 상단 표시 줄: 릴스 상단 UI(220) 아래이면서 그리드 3:4 크롭(위 240) 안쪽
HOOK_TOP = 400              # 훅 문구 시작 y — 커버 3:4 크롭(240~1680) 안에 들어가도록
XFADE_SEC = 0.3
ZOOM = 1.08                 # 켄 번스 최대 배율. 화보 느낌은 느리고 작게
SUPERSAMPLE = 3             # zoompan 은 정수 픽셀로 자르므로 3배로 키운 뒤 움직여 떨림을 1/3px 이하로
TO_YUV = "scale=out_color_matrix=bt709:out_range=tv"   # RGB→YUV 는 항상 BT.709 (기본값 601이면 색이 틀어짐)
WINDOW = {"x": 72, "y": 360, "w": 936, "h": 740}   # reel-end 사진 창
WINDOW_BLEED = 48           # 창 밖으로 여유 있게 깔아 움직여도 종이 바탕이 드러나지 않게
WINDOW_ZOOM = 1.05
TEXT_IN = (0.12, 0.45, 22)  # 글자 등장: 시작(초), 길이(초), 올라오는 거리(px). 첫 장면은 바로 보이게 둔다
CTA_DEFAULT = "저장하고 출근 전에 보기"
PLACEHOLDER_TONES = [       # 장면마다 조금씩 다른 따뜻한 무채색
    ("#ECE5DB", "#D9CDBE", "#C4B5A2"),
    ("#E8E2DA", "#D3C9BD", "#BDB1A3"),
    ("#EEE6DA", "#DDCFBC", "#C9B79F"),
    ("#E6E1DA", "#D0C8BE", "#B9AEA2"),
]


@dataclass
class Scene:
    i: int
    data: dict
    layout: str
    motion: str
    frames: int
    key: str | None
    photo: Path | None
    spec: dict
    mode: str            # bleed(전면 사진) | window(종이 위 사진 창) | paper(글자만)
    person: bool
    bg: Path | None = None
    chrome: Path | None = None
    text: Path | None = None
    tone_top: str = "light"
    tone_text: str = "light"


# ---------- 장면 계획 ----------

def plan_scenes(post: Post, fps: int) -> list[Scene]:
    scenes_raw = ((post.data.get("reel") or {}).get("scenes")) or []
    if not scenes_raw:
        raise SystemExit(f"reel.scenes 가 비어 있어요: {post.dir / 'post.yaml'}")
    scenes = []
    for i, d in enumerate(scenes_raw):
        if not isinstance(d, dict):
            raise SystemExit(f"장면 {i + 1}: '- image: …' 형식의 항목이어야 해요 (지금: {d!r})")
        key = d.get("image") or None
        layout = d.get("layout") or ("reel-hook" if i == 0 else "reel-look" if key else "reel-text")
        if layout not in LAYOUTS:
            raise SystemExit(f"장면 {i + 1}: layout '{layout}' 을 모르겠어요 ({' | '.join(LAYOUTS)})")
        motion = d.get("motion") or ("zoom-in" if key else "still")
        if motion not in MOTIONS:
            raise SystemExit(f"장면 {i + 1}: motion '{motion}' 을 모르겠어요 ({' | '.join(MOTIONS)})")
        try:
            sec = float(d.get("seconds", 2.4))
        except (TypeError, ValueError):
            raise SystemExit(f"장면 {i + 1}: seconds 는 숫자여야 해요 (지금: {d.get('seconds')!r})")
        if sec <= 0:
            raise SystemExit(f"장면 {i + 1}: seconds 는 0보다 커야 해요")
        spec = post.image_spec(key) if key else {}
        if key and not spec:
            print(f"  ! 장면 {i + 1}: images 에 '{key}' 가 없어요. 자리표시로 그려요.")
        if layout == "reel-text" or not key:
            mode = "paper"
        elif layout == "reel-end":
            mode = "window"
        else:
            mode = "bleed"
        # 프레이밍을 모르면 인물로 본다 (표시를 빠뜨리는 쪽보다 붙이는 쪽이 안전)
        person = mode != "paper" and spec.get("framing") not in NO_PERSON_FRAMINGS
        scenes.append(Scene(
            i=i, data=d, layout=layout, motion=motion if mode != "paper" else "still",
            frames=max(2, round(sec * fps)), key=key, photo=post.image_path(key) if key else None,
            spec=spec, mode=mode, person=person,
        ))
    return scenes


def motion_params(scene: Scene) -> tuple[float, float, float, float, float]:
    """(z0, z1, px0, px1, py). x = px*(iw-iw/zoom) 이면 px 지점이 화면에서 고정된다."""
    if scene.mode == "window":
        # 창 중심을 기준으로 작게 움직여 창 가장자리에 종이가 드러나지 않게 한다
        z, fy = WINDOW_ZOOM, (WINDOW["y"] + WINDOW["h"] / 2) / 1920
        lo, hi = 0.25, 0.75
    else:
        z, fy = ZOOM, 0.42   # 얼굴·상체가 있는 위쪽을 조금 더 중심에
        lo, hi = 0.1, 0.9
    return {
        "zoom-in": (1.0, z, 0.5, 0.5, fy),
        "zoom-out": (z, 1.0, 0.5, 0.5, fy),
        "pan-right": (z, z, lo, hi, fy),
        "pan-left": (z, z, hi, lo, fy),
        "still": (1.0, 1.0, 0.5, 0.5, fy),
    }[scene.motion]


# ---------- 배경 ----------

def _cover_crop(img, w: int, h: int):
    """비율을 맞춰 가운데를 잘라낸다 (확대는 하지 않음 — 확대는 ffmpeg 에서 한 번만)."""
    sw, sh = img.size
    target = w / h
    if sw / sh > target:
        cw, ch = round(sh * target), sh
    else:
        cw, ch = sw, round(sw / target)
    left, top = (sw - cw) // 2, (sh - ch) // 2
    return img.crop((left, top, left + cw, top + ch))


def prepare_backgrounds(post: Post, scenes: list[Scene], work: Path, W: int, H: int, paper: str) -> None:
    from PIL import Image

    from doha.htmlrender import screenshot_pages

    pages = []
    for s in scenes:
        if s.mode == "paper":
            continue
        s.bg = work / f"bg_{s.i + 1:02d}.png"
        if s.photo is None:
            pages.append((_placeholder_html(s, W, H, paper), s.bg))
            continue
        img = Image.open(s.photo).convert("RGB")
        if s.mode == "bleed":
            # 원본 해상도 그대로 비율만 맞춘다 (확대는 ffmpeg 에서 한 번만)
            _cover_crop(img, W, H).save(s.bg, compress_level=1)
        else:
            b = WINDOW_BLEED
            canvas = Image.new("RGB", (W, H), paper)
            ww, wh = WINDOW["w"] + 2 * b, WINDOW["h"] + 2 * b
            canvas.paste(_cover_crop(img, ww, wh).resize((ww, wh), Image.LANCZOS),
                         (WINDOW["x"] - b, WINDOW["y"] - b))
            canvas.save(s.bg, compress_level=1)
    if pages:
        # 자리표시는 최대 1.08배까지만 확대되므로 1배 해상도로 충분
        screenshot_pages(pages, W, H)


def _placeholder_html(s: Scene, W: int, H: int, paper: str) -> str:
    from doha.htmlrender import render_template

    if s.mode == "window":
        b = WINDOW_BLEED
        rect = {"x": WINDOW["x"] - b, "y": WINDOW["y"] - b, "w": WINDOW["w"] + 2 * b, "h": WINDOW["h"] + 2 * b}
        inset = b + 40
        label_y = WINDOW["y"] + WINDOW["h"] // 2
    else:
        rect = {"x": 0, "y": 0, "w": W, "h": H}
        inset = 110   # 켄 번스 이동 폭(최대 약 80px)보다 안쪽이라 움직여도 테두리가 잘리지 않음
        # 글자 오버레이와 겹치지 않는 자리에 라벨을 둔다
        label_y = 1240 if s.layout == "reel-hook" else 690
    prompt = " ".join(str(s.spec.get("prompt") or "").split())
    if len(prompt) > 60:
        prompt = prompt[:60].rsplit(" ", 1)[0].rstrip(",.;:") + "…"
    return render_template(
        "reel/placeholder.html", W=W, H=H, paper=paper, rect=rect, inset=inset, label_y=label_y,
        tone=PLACEHOLDER_TONES[s.i % len(PLACEHOLDER_TONES)],
        key=s.key or "", framing=s.spec.get("framing") or "photo", prompt=prompt,
    )


def measure_tones(scenes: list[Scene], W: int, H: int) -> None:
    """글자가 놓일 영역의 밝기로 글자색(먹/흰)과 스크림을 고른다."""
    from PIL import Image, ImageStat

    for s in scenes:
        if s.mode != "bleed" or s.bg is None:
            continue
        small = Image.open(s.bg).convert("L").resize((W // 4, H // 4))

        def lum(x0, y0, x1, y1):
            return ImageStat.Stat(small.crop((x0 // 4, y0 // 4, x1 // 4, y1 // 4))).mean[0]

        s.tone_top = "light" if lum(MARGIN, TOP_Y - 10, 760, TOP_Y + 80) > 150 else "dark"
        s.tone_text = "light" if lum(MARGIN, HOOK_TOP, W - 140, HOOK_TOP + 520) > 150 else "dark"


# ---------- 오버레이 ----------

def _text_html(text: str):
    """'\\n' 줄바꿈과 ' + ' 를 화보식으로 (+는 카멜색 얇은 기호)."""
    from markupsafe import Markup, escape

    lines = []
    for line in str(text or "").split("\n"):
        parts = [escape(p.strip()) for p in line.split("+")]
        lines.append(Markup(' <span class="plus">+</span> ').join(parts) if len(parts) > 1 else escape(line))
    return Markup("<br>").join(lines)


def _issue_date(value) -> str:
    """사진 창 아래 잡지식 날짜 (예: 2026 · 10 · 15)."""
    text = str(value or "").strip()
    parts = text.split("-")
    return " · ".join(parts) if len(parts) == 3 else text


def render_overlays(post: Post, scenes: list[Scene], work: Path, cfg: dict, persona: dict) -> None:
    from doha.htmlrender import render_template, screenshot_pages

    W, H = cfg["canvas"]["reel"]["width"], cfg["canvas"]["reel"]["height"]
    disc = short_disclosure_label(post.data, persona)
    looks = [s for s in scenes if s.layout == "reel-look"]
    look_labels = [str(s.data.get("label")).strip() for s in looks if s.data.get("label")]
    handle = "@" + str(cfg["account"]["handle"]).lstrip("@")
    base = {
        "W": W, "H": H, "safe": cfg["canvas"]["reel_safe"], "m": MARGIN, "top_y": TOP_Y,
        "c": persona["layout"]["colors"],
        "wordmark": persona.get("typography", {}).get("wordmark_text") or "DOHA DAILYFIT",
        "handle": handle, "series": post.data.get("series") or "",
    }
    pages = []
    for s in scenes:
        ctx = dict(base)
        ctx.update(
            mode=s.mode, tone_top=s.tone_top, tone_text=s.tone_text,
            text_html=_text_html(s.data.get("text") or (post.data.get("hook") if s.i == 0 else "")),
            label=s.data.get("label") or "",
            ai_badge=persona["disclosure"]["slide_badge"] if s.person else "",
            # 광고 표시는 끌 수 없다: 첫 장면은 크게, 나머지는 작게 계속
            disc_big=disc if s.i == 0 else "", disc_small=disc if s.i > 0 else "",
            hook_top=HOOK_TOP, hook_max_h=440,   # 헤드라인이 y≈920 안에서 끝나도록 (인물 얼굴·자리표시 라벨 위)
            sub_items=look_labels if len(look_labels) > 1 else [],
            look_no=next((k + 1 for k, x in enumerate(looks) if x is s), 0), look_total=len(looks),
            window=WINDOW if s.mode == "window" else None,
            caption_right=_issue_date(post.data.get("date")),
            cta=s.data.get("cta") or CTA_DEFAULT,
        )
        s.chrome = work / f"chrome_{s.i + 1:02d}.png"
        s.text = work / f"text_{s.i + 1:02d}.png"
        tpl = f"reel/{s.layout}.html"
        pages.append((render_template(tpl, layer="chrome", **ctx), s.chrome))
        pages.append((render_template(tpl, layer="text", **ctx), s.text))
    screenshot_pages(pages, W, H, transparent=True)


def compose_still(s: Scene, W: int, H: int, paper: str):
    """장면 첫 프레임 정지 이미지 (커버·검수용). 영상과 같은 시작 구도."""
    from PIL import Image

    if s.bg is None:
        img = Image.new("RGB", (W, H), paper)
    else:
        bg = Image.open(s.bg).convert("RGB")
        z0, _, px0, _, py = motion_params(s)
        bw, bh = bg.size
        cw, ch = bw / z0, bh / z0
        x, y = px0 * (bw - cw), py * (bh - ch)
        img = bg.resize((W, H), Image.LANCZOS, box=(x, y, x + cw, y + ch))
    img = img.convert("RGBA")
    for layer in (s.chrome, s.text):
        img.alpha_composite(Image.open(layer).convert("RGBA"))
    return img.convert("RGB")


# ---------- ffmpeg ----------

def build_ffmpeg_cmd(scenes: list[Scene], out: Path, fps: int, W: int, H: int, paper: str,
                     audio: Path | None) -> tuple[list[str], int]:
    inputs: list[str] = []
    graph: list[str] = []
    n_in = 0

    def add(*args: str) -> int:
        nonlocal n_in
        inputs.extend(args)
        n_in += 1
        return n_in - 1

    SW, SH = W * SUPERSAMPLE, H * SUPERSAMPLE
    st, dur, rise = TEXT_IN
    for s in scenes:
        n = s.frames
        # 합성은 yuv444p 에서 (RGB보다 빠르고 zoompan 색차 반올림도 없음). 알파 블렌딩은 색공간 변환과 순서를 바꿔도 같다
        if s.bg is None:
            bi = add("-f", "lavfi", "-i", f"color=c={paper}:s={W}x{H}:r={fps}:d={n / fps:.4f}")
            graph.append(f"[{bi}:v]trim=end_frame={n},format=rgb24,{TO_YUV},format=yuv444p,setsar=1[bg{s.i}]")
        else:
            bi = add("-i", str(s.bg))
            z0, z1, px0, px1, py = motion_params(s)
            p = f"on/{n - 1}"
            graph.append(
                f"[{bi}:v]scale={SW}:{SH}:flags=lanczos:out_color_matrix=bt709:out_range=tv,format=yuv444p,"
                f"zoompan=z='{z0}+({z1 - z0:.5f})*{p}':x='({px0}+({px1 - px0:.5f})*{p})*(iw-iw/zoom)'"
                f":y='{py:.5f}*(ih-ih/zoom)':d={n}:s={W}x{H}:fps={fps},setsar=1[bg{s.i}]"
            )
        ci = add("-i", str(s.chrome))
        ti = add("-framerate", str(fps), "-i", str(s.text))
        graph.append(f"[{ci}:v]{TO_YUV},format=yuva444p[ch{s.i}]")
        graph.append(f"[bg{s.i}][ch{s.i}]overlay=0:0:format=yuv444[c{s.i}]")
        if s.i == 0:
            # 첫 장면 글자는 첫 프레임부터 보여야 한다 (피드에서 멈춘 화면·자동 커버)
            graph.append(f"[{ti}:v]{TO_YUV},format=yuva444p[t{s.i}]")
            graph.append(f"[c{s.i}][t{s.i}]overlay=0:0:format=yuv444[v{s.i}]")
        else:
            graph.append(
                f"[{ti}:v]{TO_YUV},format=yuva444p,loop=loop={n - 1}:size=1:start=0,setpts=N/{fps}/TB,"
                f"fade=t=in:st={st}:d={dur}:alpha=1[t{s.i}]"
            )
            graph.append(
                f"[c{s.i}][t{s.i}]overlay=x=0:y='{rise}*pow(1-clip((t-{st})/{dur},0,1),3)'"
                f":format=yuv444:eval=frame[v{s.i}]"
            )

    # 크로스페이드: 장면 k 는 (앞 장면 프레임 합 - k*겹침) 에서 시작. 정수 프레임으로 계산해 누적 오차 없음
    xf = min(round(XFADE_SEC * fps), min(s.frames for s in scenes) // 3) if len(scenes) > 1 else 0
    cur, total = "v0", scenes[0].frames
    for s in scenes[1:]:
        offset = (total - xf) / fps
        graph.append(f"[{cur}][v{s.i}]xfade=transition=fade:duration={xf / fps:.6f}:offset={offset:.6f}[x{s.i}]")
        cur, total = f"x{s.i}", total + s.frames - xf
    graph.append(f"[{cur}]format=yuv420p[vout]")

    seconds = total / fps
    if audio:
        ai = add("-i", str(audio))
        graph.append(
            f"[{ai}:a]aformat=sample_rates=44100:channel_layouts=stereo,apad,atrim=0:{seconds:.4f},"
            f"afade=t=out:st={max(0.0, seconds - 0.5):.4f}:d=0.5,asetpts=PTS-STARTPTS[aout]"
        )
        amap = "[aout]"
    else:
        ai = add("-f", "lavfi", "-t", f"{seconds:.4f}", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100")
        amap = f"{ai}:a"

    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-stats" if sys.stderr.isatty() else "-nostats", "-y", *inputs,
        "-filter_complex", ";".join(graph),
        "-map", "[vout]", "-map", amap,
        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-r", str(fps), "-g", str(fps * 2), "-frames:v", str(total),
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2", "-t", f"{seconds:.4f}",
        "-movflags", "+faststart", str(out),
    ]
    return cmd, total


def _resolve_audio(post: Post) -> Path | None:
    ref = (post.data.get("reel") or {}).get("audio")
    if not ref:
        return None
    from doha.core import ROOT

    for cand in (post.dir / str(ref), ROOT / str(ref), Path(str(ref))):
        if cand.is_file():
            return cand
    print(f"  ! 음원 파일을 찾을 수 없어 무음으로 만들어요: {ref}")
    return None


# ---------- 공개 API ----------

def make_reel(post: Post | str, keep_frames: bool = False) -> Path:
    """post.reel.scenes 로 <post>/out/reel/reel.mp4 와 cover.png 를 만든다."""
    if not isinstance(post, Post):
        post = resolve_post(post)
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg 가 필요해요. (macOS: brew install ffmpeg / Ubuntu: sudo apt install ffmpeg)")
    started = time.monotonic()
    cfg = load_config()
    persona = load_persona(cfg)
    W, H = cfg["canvas"]["reel"]["width"], cfg["canvas"]["reel"]["height"]
    fps = int(cfg["canvas"]["reel"].get("fps", 30))
    paper = persona["layout"]["colors"]["paper"]

    out_dir = post.out_dir / "reel"
    work = out_dir / "frames"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    scenes = plan_scenes(post, fps)
    hook_text = str(scenes[0].data.get("text") or post.data.get("hook") or "")
    if len("".join(hook_text.split())) > 22:
        print("  ! 첫 장면 문구가 길어요. 릴스 첫 화면은 2줄·20자 안팎이 잘 읽혀요 (글자는 자동으로 줄여 맞춤).")
    missing = [s for s in scenes if s.mode != "paper" and s.photo is None]
    print(f"릴스: 장면 {len(scenes)}개 · 사진 {len(scenes) - len(missing) - sum(s.mode == 'paper' for s in scenes)}장"
          + (f" · 자리표시 {len(missing)}장" if missing else ""))

    prepare_backgrounds(post, scenes, work, W, H, paper)
    measure_tones(scenes, W, H)
    render_overlays(post, scenes, work, cfg, persona)

    cover = out_dir / "cover.png"
    compose_still(scenes[0], W, H, paper).save(cover)
    if keep_frames:
        for s in scenes:
            compose_still(s, W, H, paper).save(work / f"scene_{s.i + 1:02d}.png")

    out = out_dir / "reel.mp4"
    tmp = out_dir / "reel.tmp.mp4"
    cmd, total = build_ffmpeg_cmd(scenes, tmp, fps, W, H, paper, _resolve_audio(post))
    if keep_frames:
        (work / "ffmpeg-cmd.txt").write_text(shlex.join(cmd), encoding="utf-8")
    print(f"ffmpeg 합성 중… ({total / fps:.2f}초, {total}프레임)")
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        tmp.unlink(missing_ok=True)
        (work / "ffmpeg-cmd.txt").write_text(shlex.join(cmd), encoding="utf-8")
        raise SystemExit(f"ffmpeg 실패 (코드 {proc.returncode}). 중간 파일과 명령: {work}")
    tmp.replace(out)
    if not keep_frames:
        shutil.rmtree(work, ignore_errors=True)

    print(f"완료: {out}  ({total / fps:.2f}초 · {W}x{H} · {fps}fps · {time.monotonic() - started:.0f}초 걸림)")
    print(f"커버: {cover}  (그리드에서는 가운데 3:4만 보여요)")
    if missing:
        keys = ", ".join(s.key for s in missing if s.key)
        print(f"  자리표시로 그린 사진: {keys} → 사진을 만든 뒤 다시 실행하세요.")
    if keep_frames:
        print(f"중간 파일: {work}")
    return out


# ---------- CLI ----------

def add_arguments(parser) -> None:
    parser.add_argument("post", help="게시물 폴더 경로 또는 id 일부 (예: black-slacks)")
    parser.add_argument("--keep-frames", action="store_true",
                        help="배경·오버레이·장면 정지 이미지를 out/reel/frames 에 남기기 (검수·디버깅용)")


def run(args) -> int:
    post = resolve_post(args.post)
    if skip_if_legacy(post):
        return 0
    make_reel(post, keep_frames=args.keep_frames)
    return 0
