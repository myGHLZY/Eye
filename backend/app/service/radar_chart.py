from math import tau

from app.service.bar_chart import load_bar_data, read_series
from app.util.chart import (
    ChartError, chart_font, chart_object, chart_points, chart_text, figure_png, render_lock, style_flag,
)

MAX_AXES = 12


def load_radar_data(payload) -> dict:
    """把分类汇总结果用作雷达图的各个指标轴。"""
    data = load_bar_data(payload)
    data["truncated"] = data["truncated"] or len(data["points"]) > MAX_AXES
    data["points"] = data["points"][:MAX_AXES]
    for series in data.get("series", []):
        series["values"] = series["values"][:MAX_AXES]
    return data


def render_radar_chart(payload):
    """在统一刻度的极坐标轴上绘制单条或多条指标轮廓。"""
    payload = chart_object(payload)
    points = chart_points(payload, MAX_AXES)
    if len(points) < 3:
        raise ChartError("雷达图至少需要三个指标分类。")
    labels, values = zip(*points)
    style = chart_object(payload.get("style", {}))
    series = read_series(payload, len(points)) or [(chart_text(style, "legendLabel", maximum=60) or "数值", values)]
    if any(min(profile) < 0 for _, profile in series):
        raise ChartError("雷达图需要非负指标。")
    fill = style_flag(style, "fill", True)
    title = chart_text(style, "title", maximum=60)
    colors = style.get("colors", [])
    if not isinstance(colors, list) or any(not isinstance(color, str) for color in colors):
        raise ChartError()

    with render_lock:
        from matplotlib.colors import is_color_like
        from matplotlib.figure import Figure

        if any(not is_color_like(color) for color in colors):
            raise ChartError()
        font = chart_font()
        figure = Figure(figsize=(8, 6), dpi=130, layout="constrained", facecolor="#ffffff")
        axes = figure.add_subplot(projection="polar")
        angles = [index * tau / len(points) for index in range(len(points))]
        loop = [*angles, angles[0]]
        axes.set_theta_offset(tau / 4)
        axes.set_theta_direction(-1)
        axes.set_xticks(angles, [label if len(label) <= 15 else label[:14] + "…" for label in labels],
                        fontproperties=font, parse_math=False, fontsize=9)
        axes.set_ylim(0, max((max(profile) for _, profile in series), default=0) * 1.12 or 1)
        axes.grid(color="#dbe5f0")
        axes.spines["polar"].set_color("#aebed1")
        for index, (label, profile) in enumerate(series):
            color = colors[index % len(colors)] if colors else f"C{index}"
            closed = [*profile, profile[0]]
            axes.plot(loop, closed, color=color, linewidth=1.8, marker="o", markersize=3, label=label[:22])
            if fill:
                axes.fill(loop, closed, color=color, alpha=0.14)
        if title:
            figure.suptitle(title, fontproperties=font, parse_math=False)
        if len(series) > 1 or style_flag(style, "showLegend", True):
            handles, names = axes.get_legend_handles_labels()
            if handles:
                legend = figure.legend(handles, names, loc="outside lower center", ncols=min(4, len(series)),
                                       prop=font, frameon=False)
                for text in legend.get_texts():
                    text.set_parse_math(False)
        return figure_png(figure)
