"""解説に添える図（インラインSVG）を生成するモジュール

questions.py の問題に "figure" キー（辞書）を付けると、
app.py の解説表示のときに render() がSVG文字列に変換して表示する。
外部ライブラリは使わず、曲線の座標は math だけで計算する。
"""

import html
import math

# 色（アプリの青 #1c83e1 に合わせる。強調は赤、参考はグレー）
_COLORS = {
    "blue": ("#1c83e1", "rgba(28, 131, 225, 0.18)"),
    "red": ("#e34948", "rgba(227, 73, 72, 0.30)"),
    "gray": ("#8a8a8a", "rgba(150, 150, 150, 0.25)"),
}
_INK = "#666666"  # 文字（ラベル）の色
_AXIS = "#bbbbbb"  # 軸の色

# 図のサイズ（viewBox）と余白
_W, _H = 460, 260
_ML, _MR, _MT, _MB = 14, 14, 34, 48
_ZMIN, _ZMAX = -4.0, 4.0  # 横軸（z）の範囲
_YMAX = 0.44  # 縦軸（確率密度）の上限


def _pdf(z):
    """標準正規分布の確率密度関数。"""
    return math.exp(-z * z / 2) / math.sqrt(2 * math.pi)


def _x(z):
    """z の値 → SVG の横座標。"""
    return _ML + (z - _ZMIN) / (_ZMAX - _ZMIN) * (_W - _ML - _MR)


def _y(d):
    """確率密度 → SVG の縦座標。"""
    return _MT + (_H - _MT - _MB) * (1 - d / _YMAX)


def _pts(f, a, b, n=120):
    """区間 [a, b] の曲線 y=f(z) を n 分割した点列（SVG座標の文字列）を返す。"""
    return [
        f"{_x(z):.1f},{_y(f(z)):.1f}"
        for z in (a + (b - a) * i / n for i in range(n + 1))
    ]


def _area_path(f, a, b):
    """区間 [a, b] の曲線の下を塗るためのパス文字列を返す。"""
    pts = _pts(f, a, b)
    return (
        f"M{_x(a):.1f},{_y(0):.1f} L" + " L".join(pts) + f" L{_x(b):.1f},{_y(0):.1f} Z"
    )


def _text(s, x, y, size=13, color=_INK, weight="normal", anchor="middle"):
    """SVGのテキスト要素を返す（フォントはアプリの丸ゴシックを継承する）。"""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{color}" '
        f'font-weight="{weight}" text-anchor="{anchor}" '
        f'font-family="inherit">{html.escape(str(s))}</text>'
    )


def _fmt(v):
    """目盛りの数値を見やすく整形する（2.0 → 2、1.96 はそのまま）。"""
    return str(int(v)) if float(v) == int(v) else str(v)


def _wrap(body):
    """SVG本体を、スマホでも幅に収まる div で包んで返す。"""
    return (
        f'<div style="max-width:{_W}px;margin:0.2rem auto 0.8rem;">'
        f'<svg viewBox="0 0 {_W} {_H}" width="100%" role="img">{body}</svg></div>'
    )


def _clip(v, side):
    """ラベル位置の計算用に、無限大（None）を図の端の少し内側に置き換える。
    side=-1 は区間の左端（from側→左端へ）、side=+1 は右端（to側→右端へ）。"""
    if v is None:
        return -3.3 if side < 0 else 3.3
    return max(-3.3, min(3.3, v))


def _normal_area(spec):
    """標準正規分布の曲線と、領域の塗り分け（面積のラベルつき）を描く。

    spec の例:
        {"type": "normal_area",
         "regions": [
             {"from": 1.96, "to": None, "label": "2.5%", "color": "red"},
         ],
         "xlabel": "z",                # 省略時は "z"
         "note": "ここから右が上位2.5%",  # 省略可（図の上に出る一言）
         "xnotes": {1: "X=60"}}        # 省略可（目盛りの下の補足）
    """
    parts = []
    stat = spec.get("stat")  # 検定統計量マーカーの位置（ラベルの重なり回避にも使う）

    # 領域の塗り分けと面積ラベル
    marks = {}  # 境界のz → 強調するか（赤い領域に接する境界は赤で強調）
    for r in spec.get("regions", []):
        a, b = r.get("from"), r.get("to")
        color_name = r.get("color", "blue")
        line, fill = _COLORS[color_name]
        za, zb = a if a is not None else _ZMIN, b if b is not None else _ZMAX
        parts.append(f'<path d="{_area_path(_pdf, za, zb)}" fill="{fill}"/>')
        for v in (a, b):
            if v is not None:
                marks[v] = marks.get(v, False) or color_name == "red"
        # ラベルは領域の真ん中あたりに。曲線が低い（裾）なら曲線の上に出す
        if r.get("label"):
            zm = (_clip(a, -1) + _clip(b, +1)) / 2
            # 統計量マーカーと重なりそうなら、外側へ少しずらす
            if stat is not None and abs(zm - stat) < 0.55:
                zm += -0.6 if zm <= 0 else 0.6
            # 裾のラベルは境界の破線と重ならないよう、境界から一定以上離す
            if a is None and b is not None:  # 左裾
                zm = max(-3.15, min(zm, _clip(b, +1) - 0.55))
            elif b is None and a is not None:  # 右裾
                zm = min(3.15, max(zm, _clip(a, -1) + 0.55))
            d = _pdf(zm)
            if d < 0.075:  # 裾：曲線の上に置く
                lx, ly = _x(zm), _y(d) - 10
            else:  # 山の中：塗りの内側に置く
                lx, ly = _x(zm), _y(d * 0.45)
            parts.append(_text(r["label"], lx, ly, size=15, color=line, weight="bold"))

    # 境界の破線（塗りが赤の境界は赤で強調する）
    for v, emphasized in marks.items():
        color = _COLORS["red"][0] if emphasized else _COLORS["gray"][0]
        parts.append(
            f'<line x1="{_x(v):.1f}" y1="{_y(_pdf(v)) - 20:.1f}" '
            f'x2="{_x(v):.1f}" y2="{_y(0):.1f}" stroke="{color}" '
            f'stroke-width="1.5" stroke-dasharray="5 4"/>'
        )

    # 曲線本体とベースライン（横軸）
    parts.append(
        f'<polyline points="{" ".join(_pts(_pdf, _ZMIN, _ZMAX))}" fill="none" '
        f'stroke="{_COLORS["blue"][0]}" stroke-width="2" stroke-linejoin="round"/>'
    )
    parts.append(
        f'<line x1="{_ML}" y1="{_y(0):.1f}" x2="{_W - _MR}" y2="{_y(0):.1f}" '
        f'stroke="{_AXIS}" stroke-width="1.5"/>'
    )

    # 目盛り：整数（境界と重なるところは省く）＋ 境界の値（太字）
    for t in range(-3, 4):
        if any(abs(t - v) < 0.6 for v in marks):
            continue
        parts.append(
            f'<line x1="{_x(t):.1f}" y1="{_y(0):.1f}" x2="{_x(t):.1f}" '
            f'y2="{_y(0) + 5:.1f}" stroke="{_AXIS}" stroke-width="1"/>'
        )
        parts.append(_text(_fmt(t), _x(t), _y(0) + 20, size=12))
    for v, emphasized in marks.items():
        color = _COLORS["red"][0] if emphasized else _INK
        parts.append(_text(_fmt(v), _x(v), _y(0) + 20, size=12.5, color=color, weight="bold"))

    # 目盛りの下の補足（例：z=1 の下に X=60）と横軸の名前
    for v, note in (spec.get("xnotes") or {}).items():
        parts.append(_text(note, _x(float(v)), _y(0) + 36, size=11))
    parts.append(
        _text(spec.get("xlabel", "z"), _W - _MR, _y(0) + 20, size=12, anchor="end")
    )

    # 検定統計量などの位置マーカー（実線＋太字ラベル、省略可）
    if stat is not None:
        label = spec.get("stat_label", f"{spec.get('xlabel', 'z')}={_fmt(stat)}")
        top = _y(_pdf(stat)) - 14
        parts.append(
            f'<line x1="{_x(stat):.1f}" y1="{top:.1f}" x2="{_x(stat):.1f}" '
            f'y2="{_y(0):.1f}" stroke="#444444" stroke-width="2"/>'
        )
        parts.append(_text(label, _x(stat), top - 8, size=12.5, color="#444444", weight="bold"))

    # 図の上の一言（省略可）
    if spec.get("note"):
        parts.append(_text(spec["note"], _W / 2, 18, size=12.5, color=_INK))

    return _wrap("".join(parts))


def _ci(spec):
    """信頼区間の図：中心◯%（青）と両裾（グレー）の塗り分け。

    spec の例:
        {"type": "ci", "level": 95, "z": 1.96,
         "xnotes": {-1.96: "198.04", 0: "x̄=200", 1.96: "201.96"},
         "note": "標本平均±1.96×標準誤差 が95%信頼区間"}
    """
    level = spec.get("level", 95)
    z = spec["z"]
    tail = f"{(100 - level) / 2:g}%"
    return _normal_area(
        {
            "regions": [
                {"from": None, "to": -z, "label": tail, "color": "gray"},
                {"from": -z, "to": z, "label": f"{level}%", "color": "blue"},
                {"from": z, "to": None, "label": tail, "color": "gray"},
            ],
            "xlabel": spec.get("xlabel", "z"),
            "note": spec.get("note"),
            "xnotes": spec.get("xnotes"),
        }
    )


def _rejection(spec):
    """仮説検定の棄却域の図（棄却域は赤、棄却しない領域は青）。

    spec の例:
        {"type": "rejection", "crit": 1.96, "side": "two",  # two / right / left
         "stat": 2.5, "stat_label": "z=2.5",  # 検定統計量の位置（省略可）
         "tail_label": "2.5%", "xlabel": "z", "note": "..."}
    側が left のときも crit は正の値で指定する（境界は −crit になる）。
    """
    crit = spec["crit"]
    side = spec.get("side", "two")
    tail = spec.get("tail_label", "2.5%" if side == "two" else "5%")
    center = spec.get("center_label", "棄却しない")
    if side == "two":
        regions = [
            {"from": None, "to": -crit, "label": tail, "color": "red"},
            {"from": -crit, "to": crit, "label": center, "color": "blue"},
            {"from": crit, "to": None, "label": tail, "color": "red"},
        ]
    elif side == "right":
        regions = [
            {"from": None, "to": crit, "label": center, "color": "blue"},
            {"from": crit, "to": None, "label": tail, "color": "red"},
        ]
    else:  # left（左片側）
        regions = [
            {"from": None, "to": -crit, "label": tail, "color": "red"},
            {"from": -crit, "to": None, "label": center, "color": "blue"},
        ]
    return _normal_area(
        {
            "regions": regions,
            "xlabel": spec.get("xlabel", "z"),
            "note": spec.get("note"),
            "xnotes": spec.get("xnotes"),
            "stat": spec.get("stat"),
            "stat_label": spec.get("stat_label"),
        }
    )


# 信頼区間を20回作り直したときの中心のずれ（標準誤差単位・固定値）。
# |ずれ| > 1.96 の1本（★）だけが母平均を外す → 20回中19回＝約95%が的中
_CI_OFFSETS = [
    0.3, -1.1, 0.8, -0.4, 1.5, 0.1, -0.9, 2.3, -1.7, 0.6,
    1.0, -0.2, -1.4, 0.9, 1.8, -0.7, 0.2, -1.2, 0.5, -0.6,
]


def _ci_repeat(spec):
    """『同じ方法で何度も区間を作ると約95%が母平均を含む』を表す図。

    spec の例: {"type": "ci_repeat", "note": "..."}
    """
    parts = []
    half = 1.96  # 95%信頼区間の半幅（標準誤差単位）
    xmin, xmax = -4.5, 4.5

    def x(v):
        return _ML + (v - xmin) / (xmax - xmin) * (_W - _ML - _MR)

    top, bottom = 44, _H - 34
    step = (bottom - top) / (len(_CI_OFFSETS) - 1)

    # 母平均μの位置（縦の破線）
    parts.append(
        f'<line x1="{x(0):.1f}" y1="28" x2="{x(0):.1f}" y2="{bottom + 10:.1f}" '
        f'stroke="{_COLORS["gray"][0]}" stroke-width="1.5" stroke-dasharray="5 4"/>'
    )
    parts.append(_text("母平均μ（未知・固定）", x(0), 18, size=12.5, weight="bold"))

    # 20本の信頼区間（μを含む=青、外した=赤に★）
    for i, off in enumerate(_CI_OFFSETS):
        y = top + step * i
        miss = abs(off) > half
        color = _COLORS["red" if miss else "blue"][0]
        parts.append(
            f'<line x1="{x(off - half):.1f}" y1="{y:.1f}" x2="{x(off + half):.1f}" '
            f'y2="{y:.1f}" stroke="{color}" stroke-width="3" stroke-linecap="round"/>'
        )
        parts.append(
            f'<circle cx="{x(off):.1f}" cy="{y:.1f}" r="2.5" fill="{color}"/>'
        )
        if miss:
            # 右端が図からはみ出しそうなら、区間の左側にラベルを置く
            if x(off + half) + 56 > _W:
                parts.append(
                    _text("★ 外れ", x(off - half) - 8, y + 4, size=11.5,
                          color=color, weight="bold", anchor="end")
                )
            else:
                parts.append(
                    _text("★ 外れ", x(off + half) + 8, y + 4, size=11.5,
                          color=color, weight="bold", anchor="start")
                )

    note = spec.get("note", "20回のうち19回（約95%）の区間が母平均μを含む")
    parts.append(_text(note, _W / 2, _H - 8, size=12.5))
    return _wrap("".join(parts))


def _interval(spec):
    """数直線の上に信頼区間を描く図（0が区間に入るかを見る問題などに使う）。

    spec の例:
        {"type": "interval", "low": -0.2, "high": 3.4,
         "mark": 0, "mark_label": "0（効果なし）", "note": "..."}
    """
    lo, hi = spec["low"], spec["high"]
    mark = spec.get("mark")
    span = hi - lo
    xmin = min(lo, mark if mark is not None else lo) - span * 0.3
    xmax = max(hi, mark if mark is not None else hi) + span * 0.3

    def x(v):
        return _ML + (v - xmin) / (xmax - xmin) * (_W - _ML - _MR)

    parts = []
    axis_y, bar_y = 180, 120
    blue = _COLORS["blue"][0]

    # 数直線（横軸）と目盛り
    parts.append(
        f'<line x1="{_ML}" y1="{axis_y}" x2="{_W - _MR}" y2="{axis_y}" '
        f'stroke="{_AXIS}" stroke-width="1.5"/>'
    )
    for v in (lo, hi):
        parts.append(
            f'<line x1="{x(v):.1f}" y1="{axis_y}" x2="{x(v):.1f}" '
            f'y2="{axis_y + 5}" stroke="{_AXIS}" stroke-width="1"/>'
        )
        # 注目する値（mark）のラベルと近すぎるときは外側へ寄せて重なりを防ぐ
        anchor, dx = "middle", 0
        if mark is not None and abs(x(v) - x(mark)) < 30:
            anchor = "end" if x(v) <= x(mark) else "start"
            dx = -5 if anchor == "end" else 5
        parts.append(_text(_fmt(v), x(v) + dx, axis_y + 22, size=12.5, weight="bold", anchor=anchor))

    # 信頼区間の帯（両端は縦棒つき）
    parts.append(
        f'<line x1="{x(lo):.1f}" y1="{bar_y}" x2="{x(hi):.1f}" y2="{bar_y}" '
        f'stroke="{blue}" stroke-width="5" stroke-linecap="round"/>'
    )
    for v in (lo, hi):
        parts.append(
            f'<line x1="{x(v):.1f}" y1="{bar_y - 9}" x2="{x(v):.1f}" '
            f'y2="{bar_y + 9}" stroke="{blue}" stroke-width="3"/>'
        )
    parts.append(_text("95%信頼区間", (x(lo) + x(hi)) / 2, bar_y - 20, size=13, color=blue, weight="bold"))

    # 注目する値（例：0）の破線と点
    if mark is not None:
        red = _COLORS["red"][0]
        parts.append(
            f'<line x1="{x(mark):.1f}" y1="{bar_y - 42}" x2="{x(mark):.1f}" '
            f'y2="{axis_y}" stroke="{red}" stroke-width="1.5" stroke-dasharray="5 4"/>'
        )
        parts.append(
            f'<circle cx="{x(mark):.1f}" cy="{bar_y}" r="4.5" fill="{red}"/>'
        )
        parts.append(
            _text(spec.get("mark_label", _fmt(mark)), x(mark), bar_y - 50,
                  size=12.5, color=red, weight="bold")
        )
        anchor, dx = "middle", 0
        near = [v for v in (lo, hi) if abs(x(v) - x(mark)) < 30]
        if near:
            anchor = "start" if x(mark) >= x(near[0]) else "end"
            dx = 5 if anchor == "start" else -5
        parts.append(_text(_fmt(mark), x(mark) + dx, axis_y + 22, size=12.5, color=red, weight="bold", anchor=anchor))

    if spec.get("note"):
        parts.append(_text(spec["note"], _W / 2, _H - 12, size=12.5))
    return _wrap("".join(parts))


def _boxplot(spec):
    """箱ひげ図（横向き）。部位の名前・IQRのブラケット・外れ値の境界も描ける。

    spec の例:
        {"type": "boxplot", "lo": 8, "q1": 30, "med": 40, "q3": 50, "hi": 72,
         "fence": 80, "fence_label": "Q3＋1.5×IQR＝80", "outlier": 88,
         "iqr_label": "IQR＝20", "labels": False, "ticks": [30, 50, 80],
         "note": "..."}
    """
    lo, q1, q3, hi = spec["lo"], spec["q1"], spec["q3"], spec["hi"]
    med = spec.get("med", (q1 + q3) / 2)
    fence, outlier = spec.get("fence"), spec.get("outlier")
    blue, blue_fill = _COLORS["blue"]
    red = _COLORS["red"][0]

    vals = [v for v in (lo, hi, fence, outlier) if v is not None]
    vmin, vmax = min(vals), max(vals)
    pad = (vmax - vmin) * 0.12

    def x(v):
        return _ML + (v - (vmin - pad)) / (vmax - vmin + 2 * pad) * (_W - _ML - _MR)

    parts = []
    box_t, box_b, mid_y, axis_y = 90, 150, 120, 200

    # ひげ（箱から最小値・最大値まで）と端のキャップ
    for a, b in ((lo, q1), (q3, hi)):
        parts.append(
            f'<line x1="{x(a):.1f}" y1="{mid_y}" x2="{x(b):.1f}" y2="{mid_y}" '
            f'stroke="{blue}" stroke-width="2"/>'
        )
    for v in (lo, hi):
        parts.append(
            f'<line x1="{x(v):.1f}" y1="{mid_y - 12}" x2="{x(v):.1f}" '
            f'y2="{mid_y + 12}" stroke="{blue}" stroke-width="2"/>'
        )

    # 箱（Q1〜Q3）と中央値の線
    parts.append(
        f'<rect x="{x(q1):.1f}" y="{box_t}" width="{x(q3) - x(q1):.1f}" '
        f'height="{box_b - box_t}" fill="{blue_fill}" stroke="{blue}" stroke-width="2"/>'
    )
    med_color = red if spec.get("labels") else blue
    parts.append(
        f'<line x1="{x(med):.1f}" y1="{box_t}" x2="{x(med):.1f}" y2="{box_b}" '
        f'stroke="{med_color}" stroke-width="3"/>'
    )

    # IQR のブラケット（箱の上）
    if spec.get("iqr_label"):
        y = box_t - 18
        parts.append(
            f'<path d="M{x(q1):.1f},{y + 6} L{x(q1):.1f},{y} L{x(q3):.1f},{y} '
            f'L{x(q3):.1f},{y + 6}" fill="none" stroke="{_INK}" stroke-width="1.5"/>'
        )
        parts.append(_text(spec["iqr_label"], (x(q1) + x(q3)) / 2, y - 8, size=12.5, weight="bold"))

    # 外れ値の境界（赤い破線）とラベル
    if fence is not None:
        parts.append(
            f'<line x1="{x(fence):.1f}" y1="56" x2="{x(fence):.1f}" y2="{axis_y}" '
            f'stroke="{red}" stroke-width="1.5" stroke-dasharray="5 4"/>'
        )
        if spec.get("fence_label"):
            parts.append(_text(spec["fence_label"], x(fence), 46, size=12.5, color=red, weight="bold"))

    # 外れ値の点
    if outlier is not None:
        parts.append(f'<circle cx="{x(outlier):.1f}" cy="{mid_y}" r="4.5" fill="{red}"/>')
        parts.append(_text("外れ値", x(outlier), mid_y - 14, size=12, color=red, weight="bold"))

    # 横軸と目盛り
    parts.append(
        f'<line x1="{_ML}" y1="{axis_y}" x2="{_W - _MR}" y2="{axis_y}" '
        f'stroke="{_AXIS}" stroke-width="1.5"/>'
    )
    for v in spec.get("ticks") or []:
        parts.append(
            f'<line x1="{x(v):.1f}" y1="{axis_y}" x2="{x(v):.1f}" y2="{axis_y + 5}" '
            f'stroke="{_AXIS}" stroke-width="1"/>'
        )
        parts.append(_text(_fmt(v), x(v), axis_y + 20, size=12.5, weight="bold"))

    # 部位の名前（最小値・Q1・中央値・Q3・最大値）
    if spec.get("labels"):
        for v, name in ((lo, "最小値"), (q1, "Q1"), (q3, "Q3"), (hi, "最大値")):
            parts.append(_text(name, x(v), 172, size=12.5))
        parts.append(_text("中央値", x(med), box_t - 10, size=13, color=red, weight="bold"))

    if spec.get("note"):
        parts.append(_text(spec["note"], _W / 2, 18, size=12.5))
    return _wrap("".join(parts))


def _skew(spec):
    """右（または左）に裾を引く分布と、最頻値・中央値・平均値の位置関係の図。

    spec の例:
        {"type": "skew", "direction": "right",
         "show_stats": True,   # 最頻値・中央値・平均値の線を描く
         "tail_arrow": False,  # 裾の方向の矢印を描く
         "note": "..."}
    """
    right = spec.get("direction", "right") == "right"
    parts = []
    y0, top = 200, 50
    xmax = 8.0

    def f(v):  # ガンマ分布（k=2.5）の形。最頻値1.5・中央値≈2.17・平均2.5
        return v**1.5 * math.exp(-v)

    fmax = f(1.5)

    def x(v):
        v = v if right else xmax - v  # 左に歪んだ分布は左右を反転する
        return _ML + v / xmax * (_W - _ML - _MR)

    def y(v):
        return y0 - f(v) / fmax * (y0 - top)

    pts = " ".join(
        f"{x(v):.1f},{y(v):.1f}" for v in (i * xmax / 160 for i in range(161))
    )
    parts.append(
        f'<polyline points="{pts}" fill="none" stroke="{_COLORS["blue"][0]}" '
        f'stroke-width="2" stroke-linejoin="round"/>'
    )
    parts.append(
        f'<line x1="{_ML}" y1="{y0}" x2="{_W - _MR}" y2="{y0}" '
        f'stroke="{_AXIS}" stroke-width="1.5"/>'
    )

    # 最頻値・中央値・平均値の線とラベル（高さをずらして重なりを防ぐ）
    if spec.get("show_stats", True):
        stats = [
            (1.5, "最頻値", _COLORS["blue"][0], 44),
            (2.17, "中央値", "#444444", 60),
            (2.5, "平均値", _COLORS["red"][0], 76),
        ]
        for v, name, color, label_y in stats:
            parts.append(
                f'<line x1="{x(v):.1f}" y1="{label_y + 6:.1f}" x2="{x(v):.1f}" '
                f'y2="{y0}" stroke="{color}" stroke-width="1.5" stroke-dasharray="5 4"/>'
            )
            anchor = "start" if right else "end"
            dx = 5 if right else -5
            parts.append(
                _text(name, x(v) + dx, label_y, size=12.5, color=color,
                      weight="bold", anchor=anchor)
            )

    # 裾の方向の矢印
    if spec.get("tail_arrow"):
        red = _COLORS["red"][0]
        a, b = x(4.2), x(7.2)
        ay = 168
        parts.append(
            f'<line x1="{a:.1f}" y1="{ay}" x2="{b:.1f}" y2="{ay}" '
            f'stroke="{red}" stroke-width="2"/>'
        )
        tip = 8 if right else -8
        parts.append(
            f'<path d="M{b:.1f},{ay} l{-tip},-5 l0,10 Z" fill="{red}"/>'
        )
        parts.append(
            _text("裾がこちらに長い", (a + b) / 2, ay - 10, size=12.5, color=red, weight="bold")
        )

    if spec.get("note"):
        parts.append(_text(spec["note"], _W / 2, 18, size=12.5))
    return _wrap("".join(parts))


# 散布図のダミー点（固定値）。t は 0→1 の並び、noise は直線からの小さなずれ
_SC_T = [0.05, 0.13, 0.22, 0.30, 0.38, 0.47, 0.55, 0.63, 0.72, 0.80, 0.88, 0.95]
_SC_NOISE = [0.05, -0.12, 0.09, -0.04, 0.11, -0.08, 0.02, -0.10, 0.07, -0.02, 0.04, -0.06]
_SC_R0 = [
    (0.10, 0.30), (0.20, 0.75), (0.30, 0.15), (0.35, 0.55), (0.45, 0.90),
    (0.50, 0.35), (0.60, 0.65), (0.65, 0.10), (0.75, 0.80), (0.80, 0.45),
    (0.90, 0.25), (0.95, 0.70),
]


def _scatter(spec):
    """散布図。mode="correlation" は r≒+1 / 0 / −1 の3パネル、
    mode="regression" は回帰直線 y=ax+b と予測の図。

    spec の例:
        {"type": "scatter", "mode": "correlation"}
        {"type": "scatter", "mode": "regression", "slope": 5, "intercept": 20,
         "predict_x": 10, "xlabel": "広告費x（万円）", "ylabel": "売上y（万円）",
         "note": "..."}
    """
    blue = _COLORS["blue"][0]
    red = _COLORS["red"][0]
    parts = []

    if spec.get("mode") == "regression":
        a, b = spec["slope"], spec["intercept"]
        px = spec.get("predict_x")
        xmax, ymax = 14.0, 100.0
        ml = 44  # 縦軸ラベルのぶん左の余白を広くとる

        def x(v):
            return ml + v / xmax * (_W - ml - _MR)

        def y(v):
            return 210 - v / ymax * 170

        # 軸
        parts.append(f'<line x1="{ml}" y1="210" x2="{_W - _MR}" y2="210" stroke="{_AXIS}" stroke-width="1.5"/>')
        parts.append(f'<line x1="{ml}" y1="210" x2="{ml}" y2="34" stroke="{_AXIS}" stroke-width="1.5"/>')
        parts.append(_text(spec.get("xlabel", "x"), _W - _MR, 232, size=12, anchor="end"))
        parts.append(_text(spec.get("ylabel", "y"), ml, 24, size=12, anchor="start"))

        # データ点（直線のまわりに固定のずれで散らす）
        for t, nz in zip(_SC_T, _SC_NOISE):
            vx = t * 13
            vy = a * vx + b + nz * 55
            parts.append(f'<circle cx="{x(vx):.1f}" cy="{y(vy):.1f}" r="3" fill="{blue}" opacity="0.75"/>')

        # 回帰直線と切片
        parts.append(
            f'<line x1="{x(0):.1f}" y1="{y(b):.1f}" x2="{x(13.5):.1f}" y2="{y(a * 13.5 + b):.1f}" '
            f'stroke="{blue}" stroke-width="2.5"/>'
        )
        parts.append(_text(f"切片{_fmt(b)}", ml + 6, y(b) + 4, size=11.5, anchor="start"))

        # 予測：x=px を代入 → 破線で軸まで結ぶ
        if px is not None:
            py = a * px + b
            parts.append(
                f'<line x1="{x(px):.1f}" y1="210" x2="{x(px):.1f}" y2="{y(py):.1f}" '
                f'stroke="{red}" stroke-width="1.5" stroke-dasharray="5 4"/>'
            )
            parts.append(
                f'<line x1="{x(px):.1f}" y1="{y(py):.1f}" x2="{ml}" y2="{y(py):.1f}" '
                f'stroke="{red}" stroke-width="1.5" stroke-dasharray="5 4"/>'
            )
            parts.append(f'<circle cx="{x(px):.1f}" cy="{y(py):.1f}" r="4.5" fill="{red}"/>')
            parts.append(_text(_fmt(px), x(px), 226, size=12.5, color=red, weight="bold"))
            parts.append(_text(_fmt(py), ml - 6, y(py) + 4, size=12.5, color=red, weight="bold", anchor="end"))
    else:
        # r≒+1 / r≒0 / r≒−1 の3パネル
        pw, gap, top, bottom = 132, 14, 60, 192
        panels = [
            ("r ≒ ＋1", "右上がりの直線", [(t, min(1, max(0, t + nz))) for t, nz in zip(_SC_T, _SC_NOISE)]),
            ("r ≒ 0", "直線の関係なし", _SC_R0),
            ("r ≒ −1", "右下がりの直線", [(t, min(1, max(0, 1 - t + nz))) for t, nz in zip(_SC_T, _SC_NOISE)]),
        ]
        for k, (title, caption, pts) in enumerate(panels):
            x0 = _ML + k * (pw + gap)
            parts.append(
                f'<rect x="{x0}" y="{top}" width="{pw}" height="{bottom - top}" '
                f'fill="none" stroke="{_AXIS}" stroke-width="1"/>'
            )
            parts.append(_text(title, x0 + pw / 2, top - 12, size=13.5, weight="bold"))
            parts.append(_text(caption, x0 + pw / 2, bottom + 20, size=11.5))
            for u, v in pts:
                cx = x0 + 8 + u * (pw - 16)
                cy = bottom - 8 - v * (bottom - top - 16)
                parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3" fill="{blue}" opacity="0.75"/>')

    if spec.get("note"):
        parts.append(_text(spec["note"], _W / 2, 18, size=12.5))
    return _wrap("".join(parts))


def _t_pdf(x, v):
    """t分布（自由度v）の確率密度関数。"""
    c = math.exp(math.lgamma((v + 1) / 2) - math.lgamma(v / 2)) / math.sqrt(v * math.pi)
    return c * (1 + x * x / v) ** (-(v + 1) / 2)


def _chi2_pdf(x, k):
    """カイ二乗分布（自由度k）の確率密度関数。"""
    if x <= 0:
        return 0.0
    return math.exp(
        (k / 2 - 1) * math.log(x) - x / 2 - (k / 2) * math.log(2) - math.lgamma(k / 2)
    )


def _f_pdf(x, d1, d2):
    """F分布（自由度 d1, d2）の確率密度関数。"""
    if x <= 0:
        return 0.0
    lb = math.lgamma(d1 / 2) + math.lgamma(d2 / 2) - math.lgamma((d1 + d2) / 2)
    return (
        math.exp(
            (d1 / 2) * math.log(d1 * x)
            + (d2 / 2) * math.log(d2)
            - ((d1 + d2) / 2) * math.log(d1 * x + d2)
            - lb
        )
        / x
    )


def _dist_shape(spec):
    """分布の形の図。dist に応じて4種類を描き分ける。

    spec の例:
        {"type": "dist_shape", "dist": "t"}      # 正規分布とt分布の裾の比較
        {"type": "dist_shape", "dist": "chi2", "df": 9}
        {"type": "dist_shape", "dist": "f", "d1": 8, "d2": 7,
         "crit": 3.73, "crit_label": "基準3.73", "stat": 4.0, "stat_label": "F=4.0",
         "mark_one": True}                        # 「等しければ1に近い」の破線
        {"type": "dist_shape", "dist": "usage"}  # 正規・t／χ²／F の使い分け3パネル
    """
    dist = spec.get("dist")
    blue = _COLORS["blue"][0]
    red = _COLORS["red"][0]
    parts = []
    y0, top = 200, 44  # ベースラインと曲線の上端

    def curve(f, xmin, xmax, xof, fmax, color, width=2, dash=""):
        pts = []
        for i in range(161):
            v = xmin + (xmax - xmin) * i / 160
            pts.append(f"{xof(v):.1f},{y0 - f(v) / fmax * (y0 - top):.1f}")
        d = f' stroke-dasharray="{dash}"' if dash else ""
        return (
            f'<polyline points="{" ".join(pts)}" fill="none" stroke="{color}" '
            f'stroke-width="{width}" stroke-linejoin="round"{d}/>'
        )

    def baseline():
        return (
            f'<line x1="{_ML}" y1="{y0}" x2="{_W - _MR}" y2="{y0}" '
            f'stroke="{_AXIS}" stroke-width="1.5"/>'
        )

    if dist == "t":
        # 正規分布（青）と、裾の広いt分布（赤・自由度4で形の違いを見せる）
        def xof(v):
            return _ML + (v + 4) / 8 * (_W - _ML - _MR)

        fmax = _pdf(0)
        parts.append(baseline())
        parts.append(curve(lambda v: _t_pdf(v, 4), -4, 4, xof, fmax, red))
        parts.append(curve(_pdf, -4, 4, xof, fmax, blue))
        parts.append(_text("正規分布", xof(0), top - 6, size=13, color=blue, weight="bold"))
        parts.append(
            _text("t分布（裾が広い）", xof(2.45), y0 - _t_pdf(2.45, 4) / fmax * (y0 - top) - 12,
                  size=12.5, color=red, weight="bold")
        )
        for t in (-2, 0, 2):
            parts.append(_text(_fmt(t), xof(t), y0 + 18, size=12))

    elif dist == "chi2":
        k = spec.get("df", 9)
        xmax = k * 2.7

        def xof(v):
            return _ML + v / xmax * (_W - _ML - _MR)

        fmax = max(_chi2_pdf(0.05 + xmax * i / 200, k) for i in range(200))
        parts.append(baseline())
        parts.append(curve(lambda v: _chi2_pdf(v, k), 0.01, xmax, xof, fmax, blue))
        # 平均（＝自由度）の位置に破線
        h = y0 - _chi2_pdf(k, k) / fmax * (y0 - top)
        parts.append(
            f'<line x1="{xof(k):.1f}" y1="{h - 16:.1f}" x2="{xof(k):.1f}" y2="{y0}" '
            f'stroke="{_COLORS["gray"][0]}" stroke-width="1.5" stroke-dasharray="5 4"/>'
        )
        parts.append(_text(f"平均＝自由度＝{k}", xof(k), h - 24, size=12.5, weight="bold"))
        parts.append(_text("0", xof(0), y0 + 18, size=12))
        parts.append(_text(_fmt(k), xof(k), y0 + 18, size=12.5, weight="bold"))
        parts.append(_text("0以上の値だけをとり、右に裾を引く", _W / 2, y0 + 38, size=12))

    elif dist == "f":
        d1, d2 = spec.get("d1", 7), spec.get("d2", 7)
        stat, crit = spec.get("stat"), spec.get("crit")
        xmax = max(5.0, 1.4 * (stat or 0), 1.4 * (crit or 0))

        def xof(v):
            return _ML + v / xmax * (_W - _ML - _MR)

        f = lambda v: _f_pdf(v, d1, d2)
        fmax = max(f(0.02 + xmax * i / 200) for i in range(200))

        # 棄却域（基準値より右）を赤く塗る
        if crit is not None:
            pts = [f"{xof(crit):.1f},{y0}"]
            for i in range(81):
                v = crit + (xmax - crit) * i / 80
                pts.append(f"{xof(v):.1f},{y0 - f(v) / fmax * (y0 - top):.1f}")
            pts.append(f"{xof(xmax):.1f},{y0}")
            parts.append(f'<path d="M{" L".join(pts)} Z" fill="{_COLORS["red"][1]}"/>')
            parts.append(
                f'<line x1="{xof(crit):.1f}" y1="{y0 - f(crit) / fmax * (y0 - top) - 14:.1f}" '
                f'x2="{xof(crit):.1f}" y2="{y0}" stroke="{red}" stroke-width="1.5" '
                f'stroke-dasharray="5 4"/>'
            )
            parts.append(_text(spec.get("crit_label", _fmt(crit)), xof(crit), y0 + 18,
                               size=12.5, color=red, weight="bold"))
        parts.append(baseline())
        parts.append(curve(f, 0.01, xmax, xof, fmax, blue))

        # 『等しければFは1に近い』の破線
        if spec.get("mark_one"):
            h = y0 - f(1) / fmax * (y0 - top)
            parts.append(
                f'<line x1="{xof(1):.1f}" y1="{h - 12:.1f}" x2="{xof(1):.1f}" y2="{y0}" '
                f'stroke="{_COLORS["gray"][0]}" stroke-width="1.5" stroke-dasharray="5 4"/>'
            )
            parts.append(_text("等しければ1に近い", xof(1), h - 20, size=12))
            parts.append(_text("1", xof(1), y0 + 18, size=12.5, weight="bold"))

        # 検定統計量（F値）のマーカー
        if stat is not None:
            h = y0 - f(stat) / fmax * (y0 - top)
            parts.append(
                f'<line x1="{xof(stat):.1f}" y1="{h - 14:.1f}" x2="{xof(stat):.1f}" '
                f'y2="{y0}" stroke="#444444" stroke-width="2"/>'
            )
            parts.append(_text(spec.get("stat_label", f"F={_fmt(stat)}"), xof(stat),
                               h - 22, size=12.5, color="#444444", weight="bold"))
        parts.append(_text("0", xof(0), y0 + 18, size=12))

    else:  # usage：正規・t／カイ二乗／F の使い分け3パネル
        pw, gap, p_top, p_bot = 132, 14, 64, 180
        panels = [
            ("正規分布・t分布", "平均の検定・推定",
             _pdf, -3.5, 3.5),
            ("カイ二乗分布", "母分散（1つ）の検定",
             lambda v: _chi2_pdf(v, 4), 0.01, 12),
            ("F分布", "母分散の比の検定",
             lambda v: _f_pdf(v, 6, 12), 0.01, 4),
        ]
        for k, (title, caption, f, xmin, xmax) in enumerate(panels):
            x0 = _ML + k * (pw + gap)

            def xof(v, x0=x0, xmin=xmin, xmax=xmax):
                return x0 + 6 + (v - xmin) / (xmax - xmin) * (pw - 12)

            fmax = max(f(xmin + (xmax - xmin) * i / 200) for i in range(1, 201))
            pts = []
            for i in range(121):
                v = xmin + (xmax - xmin) * i / 120
                pts.append(f"{xof(v):.1f},{p_bot - f(v) / fmax * (p_bot - p_top):.1f}")
            parts.append(
                f'<line x1="{x0}" y1="{p_bot}" x2="{x0 + pw}" y2="{p_bot}" '
                f'stroke="{_AXIS}" stroke-width="1.5"/>'
            )
            parts.append(
                f'<polyline points="{" ".join(pts)}" fill="none" stroke="{blue}" '
                f'stroke-width="2" stroke-linejoin="round"/>'
            )
            parts.append(_text(title, x0 + pw / 2, p_top - 16, size=13, weight="bold"))
            parts.append(_text(caption, x0 + pw / 2, p_bot + 22, size=11.5))

    if spec.get("note"):
        parts.append(_text(spec["note"], _W / 2, 18, size=12.5))
    return _wrap("".join(parts))


def _expon_area(spec):
    """指数分布（平均 mean）の曲線と、from から右側の塗り分けを描く。

    spec の例:
        {"type": "expon_area", "mean": 500, "from": 500, "label": "約37%",
         "xlabel": "寿命（時間）",   # 省略時は "x"
         "median": True,            # 中央値の破線も描く（省略可）
         "note": "..."}             # 図の上の一言（省略可）
    """
    mean = spec["mean"]
    u0 = spec["from"] / mean  # 平均を1とした横軸の位置
    umax = 4.0  # 横軸は平均の4倍まで描く
    dmax = 1.08  # 縦軸の上限（x=0 で密度1）

    def xu(u):
        return _ML + u / umax * (_W - _ML - _MR)

    def yd(d):
        return _MT + (_H - _MT - _MB) * (1 - d / dmax)

    def pdf(u):
        return math.exp(-u)

    def curve(a, b, n=120):
        return [
            f"{xu(u):.1f},{yd(pdf(u)):.1f}"
            for u in (a + (b - a) * i / n for i in range(n + 1))
        ]

    parts = []
    line, fill = _COLORS["red"]

    # from から右側の塗り分けと面積ラベル（裾なので曲線の上に置く）
    parts.append(
        f'<path d="M{xu(u0):.1f},{yd(0):.1f} L'
        + " L".join(curve(u0, umax))
        + f' L{xu(umax):.1f},{yd(0):.1f} Z" fill="{fill}"/>'
    )
    if spec.get("label"):
        um = min(u0 + 0.75, umax - 0.6)
        parts.append(
            _text(spec["label"], xu(um), yd(pdf(um)) - 12, size=15, color=line, weight="bold")
        )

    # 中央値の破線（平均×ln2。平均より左に来ることを見せる）
    if spec.get("median"):
        umed = math.log(2)
        parts.append(
            f'<line x1="{xu(umed):.1f}" y1="{yd(pdf(umed)):.1f}" '
            f'x2="{xu(umed):.1f}" y2="{yd(0):.1f}" stroke="{_COLORS["gray"][0]}" '
            f'stroke-width="1.5" stroke-dasharray="5 4"/>'
        )
        parts.append(_text(f"中央値≒{round(mean * umed)}", xu(umed), yd(0) + 36, size=11))

    # 境界の破線（赤で強調）
    parts.append(
        f'<line x1="{xu(u0):.1f}" y1="{yd(pdf(u0)) - 20:.1f}" '
        f'x2="{xu(u0):.1f}" y2="{yd(0):.1f}" stroke="{line}" '
        f'stroke-width="1.5" stroke-dasharray="5 4"/>'
    )

    # 曲線本体とベースライン（横軸）
    parts.append(
        f'<polyline points="{" ".join(curve(0, umax))}" fill="none" '
        f'stroke="{_COLORS["blue"][0]}" stroke-width="2" stroke-linejoin="round"/>'
    )
    parts.append(
        f'<line x1="{_ML}" y1="{yd(0):.1f}" x2="{_W - _MR}" y2="{yd(0):.1f}" '
        f'stroke="{_AXIS}" stroke-width="1.5"/>'
    )

    # 目盛り：平均の倍数（境界と重なるところは省く）＋ 境界の値（赤太字）
    for t in range(0, int(umax) + 1):
        if abs(t - u0) < 0.4:
            continue
        parts.append(
            f'<line x1="{xu(t):.1f}" y1="{yd(0):.1f}" x2="{xu(t):.1f}" '
            f'y2="{yd(0) + 5:.1f}" stroke="{_AXIS}" stroke-width="1"/>'
        )
        parts.append(_text(_fmt(round(mean * t)), xu(t), yd(0) + 20, size=12))
    parts.append(
        _text(_fmt(spec["from"]), xu(u0), yd(0) + 20, size=12.5, color=line, weight="bold")
    )

    # 横軸の名前と図の上の一言（省略可）
    parts.append(_text(spec.get("xlabel", "x"), _W - _MR, yd(0) + 36, size=12, anchor="end"))
    if spec.get("note"):
        parts.append(_text(spec["note"], _W / 2, 18, size=12.5))

    return _wrap("".join(parts))


# 図タイプ名 → 描画関数 の対応表
_BUILDERS = {
    "normal_area": _normal_area,
    "expon_area": _expon_area,
    "ci": _ci,
    "rejection": _rejection,
    "ci_repeat": _ci_repeat,
    "interval": _interval,
    "boxplot": _boxplot,
    "skew": _skew,
    "scatter": _scatter,
    "dist_shape": _dist_shape,
}


def render(spec):
    """図の指定（辞書）からSVG文字列（div込み）を作って返す。"""
    builder = _BUILDERS.get(spec.get("type"))
    if builder is None:
        raise ValueError(f"未対応の図タイプです: {spec.get('type')!r}")
    return builder(spec)
