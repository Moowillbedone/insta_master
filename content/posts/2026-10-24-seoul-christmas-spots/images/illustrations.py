"""서울 겨울 명소 카드뉴스용 야경 일러스트 (SVG → PNG, 1080x1440).

실사 사진이 생기기 전까지 쓰는 그림. 실존 캐릭터·로고·간판 글자는 그리지 않는다.
"""
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))  # 저장소 루트
from doha.htmlrender import screenshot_pages  # noqa: E402

W, H = 1080, 1440

DEFS = """
<defs>
  <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur stdDeviation="6" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="glow2" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur stdDeviation="14" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="22"/></filter>
  <filter id="bokeh" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3"/></filter>
  <filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="7"/>
    <feColorMatrix values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 0.06 0"/></filter>
  <radialGradient id="warm" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#FFE9B0" stop-opacity="0.95"/><stop offset="1" stop-color="#FFB547" stop-opacity="0"/></radialGradient>
  <radialGradient id="cool" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#CFE8FF" stop-opacity="0.9"/><stop offset="1" stop-color="#6FA8FF" stop-opacity="0"/></radialGradient>
  <radialGradient id="pinkg" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#FFD3E0" stop-opacity="0.95"/><stop offset="1" stop-color="#FF7FA8" stop-opacity="0"/></radialGradient>
</defs>
"""


def page(svg_body: str, bg: str) -> str:
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;padding:0;background:{bg}}} svg{{display:block}}</style></head><body>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{DEFS}{svg_body}
<rect width="{W}" height="{H}" filter="url(#grain)" opacity="1"/></svg></body></html>"""


def bokeh(rng, n, y0, y1, colors, rmin=8, rmax=46, op=(0.15, 0.55)):
    out = []
    for _ in range(n):
        x, y = rng.uniform(-40, W + 40), rng.uniform(y0, y1)
        r = rng.uniform(rmin, rmax)
        c = rng.choice(colors)
        out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.0f}" fill="{c}" opacity="{rng.uniform(*op):.2f}" filter="url(#bokeh)"/>')
    return "\n".join(out)


def snow(rng, n, op=0.7):
    return "\n".join(
        f'<circle cx="{rng.uniform(0, W):.0f}" cy="{rng.uniform(0, H):.0f}" r="{rng.uniform(1.2, 3.6):.1f}" fill="#fff" opacity="{rng.uniform(0.25, op):.2f}"/>'
        for _ in range(n)
    )


def string_lights(rng, x0, y0, x1, y1, sag, n, color="#FFD98A", r=4.2):
    """두 점 사이에 처진 조명 줄."""
    pts, dots = [], []
    for i in range(n + 1):
        t = i / n
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t + sag * 4 * t * (1 - t)
        pts.append(f"{x:.1f},{y:.1f}")
        if 0 < i < n:
            dots.append(f'<circle cx="{x:.1f}" cy="{y + 5:.1f}" r="{r * rng.uniform(0.8, 1.2):.1f}" fill="{color}" filter="url(#glow)"/>')
    return f'<polyline points="{" ".join(pts)}" fill="none" stroke="#3a2a1a" stroke-width="1.6" opacity="0.6"/>' + "".join(dots)


def light_tree(rng, cx, base, height, width, palette, density=520, star=True):
    """점 조명으로 만든 원뿔 트리 + 나선 조명."""
    out = [f'<ellipse cx="{cx}" cy="{base - height * 0.45}" rx="{width * 0.75}" ry="{height * 0.62}" fill="url(#warm)" opacity="0.35" filter="url(#soft)"/>']
    # 몸통 실루엣
    out.append(f'<path d="M{cx},{base - height} L{cx + width / 2},{base} L{cx - width / 2},{base} Z" fill="#0d2a22" opacity="0.85"/>')
    for _ in range(density):
        t = rng.random() ** 0.85  # 아래쪽에 더 많이
        y = base - height + height * t
        half = width / 2 * t
        x = cx + rng.uniform(-half, half)
        c = rng.choice(palette)
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rng.uniform(1.6, 4.2):.1f}" fill="{c}" opacity="{rng.uniform(0.6, 1):.2f}" filter="url(#glow)"/>')
    # 나선 갈랜드
    for k in range(5):
        pts = []
        for i in range(60):
            t = i / 59
            tt = (k + t) / 5
            y = base - height + height * tt
            half = width / 2 * tt
            x = cx + half * math.sin(t * math.pi * 2 + k)
            pts.append(f"{x:.1f},{y:.1f}")
        out.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="#FFE7A8" stroke-width="2.2" opacity="0.55" filter="url(#glow)"/>')
    if star:
        sx, sy = cx, base - height - 18
        star_pts = " ".join(
            f"{sx + (34 if i % 2 == 0 else 14) * math.sin(i * math.pi / 5):.1f},{sy - (34 if i % 2 == 0 else 14) * math.cos(i * math.pi / 5):.1f}"
            for i in range(10))
        out.append(f'<polygon points="{star_pts}" fill="#FFF3C4" filter="url(#glow2)"/>')
    return "\n".join(out)


def stall(x, y, w, h, roof="#B3262B"):
    """빨간 지붕 마켓 부스: 줄무늬 차양, 진열 조명, 리스."""
    stripes = "".join(
        f'<rect x="{x - 8 + i * (w + 16) / 8:.1f}" y="{y + 4}" width="{(w + 16) / 16:.1f}" height="22" fill="#F4E6D0"/>'
        for i in range(8))
    goods = "".join(
        f'<circle cx="{x + 22 + i * (w - 44) / 5:.1f}" cy="{y + h - 34}" r="7" fill="{c}" opacity="0.9"/>'
        for i, c in enumerate(["#D9343F", "#2E7D5B", "#F6D06B", "#E8758F", "#FFFFFF", "#D9343F"]))
    bulbs = "".join(
        f'<circle cx="{x - 4 + i * (w + 8) / 9:.1f}" cy="{y + 30 + 5 * math.sin(i):.1f}" r="3.2" fill="#FFE2A0" filter="url(#glow)"/>'
        for i in range(10))
    return f"""
<g>
  <rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#3a2418"/>
  <rect x="{x + 8}" y="{y + 26}" width="{w - 16}" height="{h - 40}" fill="#FFC870" opacity="0.9" filter="url(#glow)"/>
  <rect x="{x + 8}" y="{y + h - 48}" width="{w - 16}" height="6" fill="#6b4126"/>
  {goods}
  <path d="M{x - 12},{y + 6} L{x + w / 2},{y - h * 0.42} L{x + w + 12},{y + 6} Z" fill="{roof}"/>
  <path d="M{x - 12},{y + 6} L{x + w / 2},{y - h * 0.42} L{x + w + 12},{y + 6}" fill="none" stroke="#FFE2A0" stroke-width="2.4" opacity="0.8" filter="url(#glow)"/>
  <rect x="{x - 8}" y="{y + 4}" width="{w + 16}" height="22" fill="{roof}"/>
  {stripes}
  {bulbs}
  <circle cx="{x + w / 2}" cy="{y - h * 0.12}" r="13" fill="none" stroke="#2E7D5B" stroke-width="6"/>
  <circle cx="{x + w / 2}" cy="{y - h * 0.12 + 12}" r="3" fill="#D9343F"/>
  <rect x="{x - 6}" y="{y + h - 12}" width="{w + 12}" height="12" fill="#1a0f0a"/>
</g>"""


def crowd(rng, y, n, color="#0b0d14"):
    out = []
    for _ in range(n):
        x = rng.uniform(-20, W + 20)
        s = rng.uniform(0.7, 1.3)
        out.append(f'<g transform="translate({x:.0f},{y + rng.uniform(-10, 30):.0f}) scale({s:.2f})">'
                   f'<circle cx="0" cy="-58" r="13" fill="{color}"/><path d="M-20,0 Q-22,-46 0,-46 Q22,-46 20,0 Z" fill="{color}"/></g>')
    return "\n".join(out)


def scene_cover(rng):
    body = [f'<rect width="{W}" height="{H}" fill="url(#skyCover)"/>',
            '<defs><linearGradient id="skyCover" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#070B1A"/>'
            '<stop offset="0.55" stop-color="#14213F"/><stop offset="1" stop-color="#2B1B1E"/></linearGradient></defs>']
    # 도시 실루엣
    x = 0
    sky = []
    while x < W:
        w = rng.uniform(40, 110)
        h = rng.uniform(120, 420)
        sky.append(f'<rect x="{x:.0f}" y="{H - 360 - h:.0f}" width="{w:.0f}" height="{h + 400:.0f}" fill="#0b1226"/>')
        for _ in range(int(h / 30)):
            if rng.random() < 0.45:
                sky.append(f'<rect x="{x + rng.uniform(6, w - 12):.0f}" y="{H - 360 - h + rng.uniform(10, h):.0f}" width="5" height="8" fill="#FFD27A" opacity="{rng.uniform(0.3, 0.9):.2f}"/>')
        x += w + rng.uniform(2, 10)
    body += sky
    body.append(bokeh(rng, 70, 650, 1300, ["#FFC66B", "#FF8F6B", "#FFE6A6", "#9EC5FF"], 10, 60, (0.18, 0.5)))
    body.append(light_tree(rng, W / 2, 1330, 620, 420, ["#FFF4C8", "#FFD27A", "#FFB04A", "#FF7A6B", "#FFFFFF"], density=900))
    for i in range(4):
        body.append(string_lights(rng, -20, 690 + i * 40, W + 20, 640 + i * 55, 90 + i * 20, 26, rng.choice(["#FFD98A", "#FFB7A0", "#CFE3FF"])))
    body.append(crowd(rng, H + 40, 26))
    body.append(snow(rng, 260))
    return page("\n".join(body), "#070B1A")


def scene_gwanghwamun(rng):
    body = ['<defs><linearGradient id="skyG" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0A0F24"/>'
            '<stop offset="0.6" stop-color="#1C2546"/><stop offset="1" stop-color="#3A1E1A"/></linearGradient></defs>',
            f'<rect width="{W}" height="{H}" fill="url(#skyG)"/>']
    # 산 능선(북악산 느낌)
    body.append(f'<path d="M0,560 C180,470 300,500 420,440 C520,395 640,430 760,470 C880,505 980,480 {W},520 L{W},{H} L0,{H} Z" fill="#0d1430" opacity="0.9"/>')
    # 광화문 문루 실루엣 (지붕 곡선 두 단)
    gx, gy = W / 2, 760
    body.append(f'''
<g opacity="0.92">
  <path d="M{gx - 330},{gy} Q{gx - 200},{gy - 40} {gx},{gy - 46} Q{gx + 200},{gy - 40} {gx + 330},{gy}
           L{gx + 300},{gy + 14} L{gx - 300},{gy + 14} Z" fill="#141018"/>
  <rect x="{gx - 250}" y="{gy + 14}" width="500" height="58" fill="#1d1620"/>
  <path d="M{gx - 380},{gy + 72} Q{gx - 220},{gy + 34} {gx},{gy + 28} Q{gx + 220},{gy + 34} {gx + 380},{gy + 72}
           L{gx + 350},{gy + 86} L{gx - 350},{gy + 86} Z" fill="#141018"/>
  <rect x="{gx - 300}" y="{gy + 86}" width="600" height="140" fill="#1a141c"/>
  <path d="M{gx - 75},{gy + 226} L{gx - 75},{gy + 140} Q{gx},{gy + 96} {gx + 75},{gy + 140} L{gx + 75},{gy + 226} Z" fill="#FFB866" opacity="0.55" filter="url(#glow)"/>
  <path d="M{gx - 215},{gy + 226} L{gx - 215},{gy + 160} Q{gx - 170},{gy + 130} {gx - 125},{gy + 160} L{gx - 125},{gy + 226} Z" fill="#FFB866" opacity="0.35"/>
  <path d="M{gx + 125},{gy + 226} L{gx + 125},{gy + 160} Q{gx + 170},{gy + 130} {gx + 215},{gy + 160} L{gx + 215},{gy + 226} Z" fill="#FFB866" opacity="0.35"/>
  <path d="M{gx - 330},{gy} Q{gx - 200},{gy - 40} {gx},{gy - 46} Q{gx + 200},{gy - 40} {gx + 330},{gy}" fill="none" stroke="#FFCF85" stroke-width="3" opacity="0.85" filter="url(#glow)"/>
  <path d="M{gx - 380},{gy + 72} Q{gx - 220},{gy + 34} {gx},{gy + 28} Q{gx + 220},{gy + 34} {gx + 380},{gy + 72}" fill="none" stroke="#FFCF85" stroke-width="3" opacity="0.75" filter="url(#glow)"/>
  <rect x="{gx - 300}" y="{gy + 86}" width="600" height="140" fill="none" stroke="#FFCF85" stroke-width="1.5" opacity="0.35"/>
</g>''')
    body.append(bokeh(rng, 60, 820, 1250, ["#FFC66B", "#FF8F6B", "#FFE6A6"], 10, 50, (0.2, 0.5)))
    body.append(light_tree(rng, W / 2, 1180, 560, 330, ["#FFFFFF", "#DDEBFF", "#BFD8FF", "#FFE7A6"], density=700))
    # 부스 줄
    for i, x in enumerate([20, 190, 360]):
        body.append(stall(x, 1150 + (i % 2) * 18, 150, 120))
    for i, x in enumerate([570, 740, 910]):
        body.append(stall(x, 1168 - (i % 2) * 18, 150, 120))
    for i in range(3):
        body.append(string_lights(rng, -20, 980 + i * 38, W + 20, 1000 + i * 30, 70, 30))
    body.append(crowd(rng, H + 30, 30))
    body.append(snow(rng, 200))
    return page("\n".join(body), "#0A0F24")


def scene_ddp(rng):
    body = ['<defs><linearGradient id="skyD" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#050812"/>'
            '<stop offset="1" stop-color="#14183A"/></linearGradient>'
            '<linearGradient id="facade" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3A3F55"/><stop offset="1" stop-color="#151827"/></linearGradient></defs>',
            f'<rect width="{W}" height="{H}" fill="url(#skyD)"/>']
    # 유선형 건물 덩어리
    body.append('<path d="M-60,620 C200,420 520,380 820,470 C980,520 1100,600 1160,700 L1160,1220 C900,1180 600,1200 300,1260 C120,1290 0,1300 -60,1320 Z" fill="url(#facade)"/>')
    # 패널 곡선 + 점 조명 (미디어 파사드 느낌)
    for k in range(18):
        off = k * 38
        pts = []
        for i in range(70):
            t = i / 69
            x = -60 + 1220 * t
            y = 640 + off + (-200 * math.sin(math.pi * t) + 80 * t) * (1 - k / 28)
            pts.append((x, y))
        path = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        body.append(f'<polyline points="{path}" fill="none" stroke="#6E7698" stroke-width="1.2" opacity="0.5"/>')
        for i, (x, y) in enumerate(pts):
            if i % 2 == 0:
                wave = 0.5 + 0.5 * math.sin(i / 6 + k / 2.2)
                col = "#FFD86B" if wave > 0.55 else "#7FC8FF"
                body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{1.8 + 2.6 * wave:.1f}" fill="{col}" opacity="{0.35 + 0.6 * wave:.2f}" filter="url(#glow)"/>')
    # 반사 광
    body.append('<ellipse cx="540" cy="1330" rx="620" ry="120" fill="url(#cool)" opacity="0.35" filter="url(#soft)"/>')
    body.append(bokeh(rng, 50, 1180, 1440, ["#FFD86B", "#7FC8FF", "#C9B8FF"], 8, 40, (0.2, 0.5)))
    body.append(crowd(rng, H + 50, 22, "#05060c"))
    body.append(snow(rng, 120, 0.5))
    return page("\n".join(body), "#050812")


def scene_rink(rng):
    body = ['<defs><linearGradient id="skyR" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#081022"/>'
            '<stop offset="1" stop-color="#101C3A"/></linearGradient>'
            '<linearGradient id="ice" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#BFE6FF"/><stop offset="0.5" stop-color="#E8F6FF"/>'
            '<stop offset="1" stop-color="#9FD0FF"/></linearGradient></defs>',
            f'<rect width="{W}" height="{H}" fill="url(#skyR)"/>']
    # 뒤편 유리 건물(시청 느낌의 곡면 유리)
    body.append('<path d="M80,560 C260,380 620,330 1000,470 L1000,700 L80,700 Z" fill="#16264a"/>')
    for i in range(14):
        x = 120 + i * 62
        body.append(f'<line x1="{x}" y1="{460 + abs(7 - i) * 12}" x2="{x}" y2="700" stroke="#3B5A92" stroke-width="2" opacity="0.6"/>')
    body.append(bokeh(rng, 40, 520, 720, ["#9EC5FF", "#FFE6A6"], 6, 26, (0.2, 0.5)))
    # 링크 (원근 사다리꼴 → 둥근 사각형)
    body.append('<path d="M150,800 Q150,760 200,760 L880,760 Q930,760 930,800 L1040,1250 Q1050,1300 990,1300 L90,1300 Q30,1300 40,1250 Z" fill="#20345e"/>')
    body.append('<path d="M175,812 Q175,780 215,780 L865,780 Q905,780 905,812 L1005,1238 Q1013,1278 965,1278 L115,1278 Q67,1278 75,1238 Z" fill="url(#ice)"/>')
    body.append('<ellipse cx="540" cy="1030" rx="300" ry="150" fill="#FFFFFF" opacity="0.25" filter="url(#soft)"/>')
    # 스케이트 자국
    for _ in range(26):
        x, y = rng.uniform(180, 900), rng.uniform(830, 1240)
        body.append(f'<path d="M{x:.0f},{y:.0f} q{rng.uniform(40, 120):.0f},{rng.uniform(-20, 20):.0f} {rng.uniform(80, 200):.0f},{rng.uniform(-10, 10):.0f}" fill="none" stroke="#8FB9E0" stroke-width="1.4" opacity="0.5"/>')
    # 스케이터 실루엣
    for _ in range(34):
        x, y = rng.uniform(190, 890), rng.uniform(830, 1230)
        s = 0.55 + (y - 800) / 900
        c = rng.choice(["#1C2A4A", "#B3262B", "#2E5E4E", "#E0B04A", "#3B3F7A", "#C9547A"])
        body.append(f'<g transform="translate({x:.0f},{y:.0f}) scale({s:.2f})"><ellipse cx="0" cy="6" rx="14" ry="4" fill="#5d84b3" opacity="0.4"/>'
                    f'<circle cx="0" cy="-46" r="8" fill="#1a1a22"/><path d="M-10,-36 Q0,-40 10,-36 L8,-12 L-8,-12 Z" fill="{c}"/>'
                    f'<path d="M-6,-12 L-10,4 M6,-12 L12,3" stroke="#1a1a22" stroke-width="4" stroke-linecap="round"/></g>')
    # 둘레 조명
    for i in range(3):
        body.append(string_lights(rng, -20, 720 + i * 26, W + 20, 735 + i * 22, 40, 30, rng.choice(["#FFD98A", "#CFE3FF", "#FFB7C8"])))
    body.append(snow(rng, 220))
    return page("\n".join(body), "#081022")


def scene_popup_market(rng):
    body = ['<defs><linearGradient id="bgP" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3A1424"/>'
            '<stop offset="1" stop-color="#5A1F2E"/></linearGradient></defs>',
            f'<rect width="{W}" height="{H}" fill="url(#bgP)"/>']
    # 실내 아치 조명
    for i in range(6):
        r = 520 - i * 40
        body.append(f'<path d="M{540 - r},{760} A{r},{r * 0.9} 0 0 1 {540 + r},{760}" fill="none" stroke="#FFC6D6" stroke-width="2" opacity="{0.12 + i * 0.05:.2f}" filter="url(#glow)"/>')
    body.append(bokeh(rng, 80, 120, 1100, ["#FFC6D6", "#FFE6A6", "#FF8FB0", "#FFFFFF"], 8, 50, (0.15, 0.5)))
    for i in range(4):
        body.append(string_lights(rng, -20, 160 + i * 60, W + 20, 140 + i * 70, 80, 28, rng.choice(["#FFE6A6", "#FFC6D6", "#FFFFFF"])))
    body.append(light_tree(rng, W / 2, 1150, 700, 470, ["#FFE6A6", "#FFD27A", "#FF6B6B", "#FFFFFF", "#FFB3C6"], density=820))
    # 선물 상자
    gifts = [(170, 1080, 170, 150, "#D9343F", "#F6D06B"), (330, 1120, 130, 110, "#2E7D5B", "#F3E3C2"),
             (620, 1110, 150, 120, "#F3E3C2", "#D9343F"), (770, 1060, 190, 170, "#E8758F", "#FFF1C9"),
             (60, 1140, 120, 100, "#F3E3C2", "#2E7D5B"), (900, 1140, 140, 110, "#D9343F", "#FFF1C9")]
    for x, y, w, h, c, rib in gifts:
        body.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{c}"/>'
                    f'<rect x="{x + w / 2 - 9}" y="{y}" width="18" height="{h}" fill="{rib}"/>'
                    f'<rect x="{x}" y="{y + h * 0.35}" width="{w}" height="16" fill="{rib}"/>'
                    f'<path d="M{x + w / 2},{y} q-34,-40 -40,-8 q0,22 40,8 q34,-40 40,-8 q0,22 -40,8" fill="{rib}"/>')
    body.append(f'<rect x="0" y="1250" width="{W}" height="190" fill="#2a0e18"/>')
    body.append('<ellipse cx="540" cy="1250" rx="560" ry="40" fill="#FFD2DE" opacity="0.25" filter="url(#soft)"/>')
    body.append(snow(rng, 160, 0.6))
    return page("\n".join(body), "#3A1424")


def main(out_dir: str):
    out = Path(out_dir)
    scenes = [("s01", scene_cover, 11), ("s02", scene_gwanghwamun, 22), ("s03", scene_ddp, 33),
              ("s04", scene_rink, 44), ("s05", scene_popup_market, 55)]
    pages = [(fn(random.Random(seed)), out / f"{key}.png") for key, fn, seed in scenes]
    for p in screenshot_pages(pages, W, H):
        print(p)


if __name__ == "__main__":
    # 사용: python content/posts/2026-10-24-seoul-christmas-spots/images/illustrations.py [출력 폴더]
    main(sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parent))
