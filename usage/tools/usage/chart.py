"""集計ごとの render.py が使う、SVG のグラフの配色と部品。"""

import math

# 色は役割で持ち、ライトとダークで別の段を当てる（GitHub は <img> の SVG にも配色の設定を渡す）。
# 系列の色は対象に固定し、並び順では塗り替えない
SERIES = [
    ("#2a78d6", "#3987e5"), ("#eb6834", "#d95926"), ("#1baf7a", "#199e70"), ("#eda100", "#c98500"),
    ("#e87ba4", "#d55181"), ("#008300", "#008300"), ("#6250d6", "#9085e9"), ("#e34948", "#e66767"),
]
STYLE = """<style>
svg { --surface: #fcfcfb; --text: #0b0b0b; --muted: #52514e; --grid: #e4e3df; --alert: #e34948;
      %(light)s
      font-family: -apple-system, 'Segoe UI', 'Hiragino Sans', 'Noto Sans JP', sans-serif; }
@media (prefers-color-scheme: dark) {
  svg { --surface: #1a1a19; --text: #ffffff; --muted: #c3c2b7; --grid: #3a3936; --alert: #e66767;
        %(dark)s }
}
.surface { fill: var(--surface); } .label { fill: var(--text); font-size: 13px; }
.muted { fill: var(--muted); font-size: 11px; } .grid { stroke: var(--grid); stroke-width: 1; }
.line { stroke-width: 2; fill: none; } .dash { stroke-dasharray: 6 4; }
.dot { stroke: var(--surface); stroke-width: 2; }
.other { stroke: var(--muted); fill: var(--muted); }
.avg { stroke: var(--text); stroke-width: 2.5; fill: none; stroke-dasharray: 7 4; } .avg-label { fill: var(--text); font-size: 13px; font-weight: 700; }
.limit { stroke: var(--alert); stroke-width: 1.5; stroke-dasharray: 4 3; } .limit-text { fill: var(--alert); font-size: 11px; }
%(series)s
</style>""" % {
    "light": " ".join(f"--s{i}: {light};" for i, (light, _) in enumerate(SERIES)),
    "dark": " ".join(f"--s{i}: {dark};" for i, (_, dark) in enumerate(SERIES)),
    "series": "\n".join(f".s{i} {{ stroke: var(--s{i}); fill: var(--s{i}); }}" for i in range(len(SERIES))),
}


def svg(width: int, height: int, body: list[str]) -> str:
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        STYLE,
        f'<rect class="surface" width="{width}" height="{height}" rx="8"/>',
        *body,
        "</svg>",
    ]) + "\n"


def spread(ys: list[float], gap: float, top: float, bottom: float) -> list[float]:
    """線の端の名前が重ならないよう、縦の位置を最小の間隔まで押し広げる。"""
    order = sorted(range(len(ys)), key=lambda i: ys[i])
    placed = list(ys)
    limit = top - gap
    for i in order:
        placed[i] = limit = max(placed[i], limit + gap)
    limit = bottom + gap
    for i in reversed(order):
        placed[i] = limit = min(placed[i], limit - gap)
    return placed


def nice_max(v: float) -> float:
    if v <= 0:
        return 1
    scale = 10 ** math.floor(math.log10(v))
    return next(s * scale for s in (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10) if s * scale >= v)
