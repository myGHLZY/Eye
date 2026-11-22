from app.util.chart import draw_line, draw_scatter, style_choice, style_flag, style_range

SCATTER_MARKERS = {"circle": "o", "square": "s", "triangle": "^", "diamond": "D", "cross": "x"}


def scatter_style(style, *, size=40, opacity=0.75):
    """统一读取独立图和子图的散点样式。"""
    return {
        "markerSize": style_range(style, "markerSize", size, 10, 100),
        "opacity": style_range(style, "opacity", opacity, 0.15, 1),
        "markerShape": SCATTER_MARKERS[style_choice(style, "markerShape", SCATTER_MARKERS, "circle")],
        "hollow": style_flag(style, "hollow", False),
        "fit": style_flag(style, "fit", False),
        "referenceLine": style_flag(style, "referenceLine", False),
    }


def draw_scatter_series(axes, samples, style, color, label, zorder=3):
    """用相同样式在任意坐标轴上绘制一个散点系列。"""
    xs, ys = zip(*samples)
    marker = style["markerShape"]
    colors = {"facecolors": "none", "edgecolors": color} if style["hollow"] and marker != "x" else {"color": color}
    draw_scatter(axes, xs, ys, size=style["markerSize"], alpha=style["opacity"],
                 marker=marker, label=label, zorder=zorder, **colors)


def draw_scatter_guides(axes, series, style, x_type, font, layer=None):
    """在数值横轴上绘制参考线和全体散点的线性拟合。"""
    if x_type != "number" or not series or not (style["fit"] or style["referenceLine"]):
        return
    import numpy as np

    x, y = np.asarray([sample for item in series for sample in item["samples"]], dtype=float).T
    low, high = x.min(), x.max()
    if low == high:
        return
    prefix = f"{'AB'[layer]} · " if layer is not None else ""
    if style["referenceLine"]:
        draw_line(axes, [low, high], [low, high], markers=False, color="#697b91",
                  linestyle=":", label=f"{prefix}y = x", zorder=2.5)
    if not style["fit"]:
        return
    scaled_x = (x - low) / (high - low)
    slope, intercept = np.polyfit(scaled_x, y, 1)
    residual = np.sum((y - (slope * scaled_x + intercept)) ** 2)
    variance = np.sum((y - y.mean()) ** 2)
    r2 = f"{1 - residual / variance:.3f}" if variance > 0 else "—"
    rmse = np.sqrt(residual / len(x))
    draw_line(axes, [low, high], [intercept, slope + intercept], markers=False, color="#243858",
              linestyle="--", label=f"{prefix}线性拟合", zorder=5)
    axes.text(0.97, 0.04 + (layer or 0) * 0.12, f"{prefix}R² = {r2}   RMSE = {rmse:.3g}",
              transform=axes.transAxes, ha="right", va="bottom", fontsize=8,
              color="#243858", fontproperties=font, zorder=6, parse_math=False)
