from math import cos, isclose, radians, sin

from app.service.chart_support import category_point, paired_totals
from app.service.pie_chart import MAX_SLICES
from app.util.chart import (
    ChartError, chart_figure, chart_object, chart_palette, chart_points, chart_text, draw_bars,
    figure_png, render_lock,
)

MAX_PARTS = 12


def load_bar_of_pie_data(payload):
    rows, truncated, name = paired_totals(payload, MAX_SLICES * MAX_PARTS)
    if truncated:
        raise ChartError(f"最多支持 {MAX_SLICES} 个主类别，每个类别最多 {MAX_PARTS} 个子类别。")
    groups = {}
    for category, part, value in rows:
        if value < 0:
            raise ChartError("饼图与构成柱图需要非负的汇总数值。")
        if value > 0:
            groups.setdefault(category, []).append(category_point(part, value))

    if len(groups) > MAX_SLICES or any(len(parts) > MAX_PARTS for parts in groups.values()):
        raise ChartError(f"最多支持 {MAX_SLICES} 个主类别，每个类别最多 {MAX_PARTS} 个子类别。")
    points = []
    for category, parts in groups.items():
        point = category_point(category, sum(part["value"] for part in parts), stable_key=True)
        parts.sort(key=lambda part: (-part["value"], part["label"]))
        points.append({**point, "parts": parts})
    points.sort(key=lambda point: (-point["value"], point["label"]))
    return {"points": points, "seriesName": name, "detailKey": points[0]["key"] if points else ""}


def _details(payload, values):
    points = payload["points"]
    keys = [chart_text(item, "key", required=True) for item in points]
    key = chart_text(payload, "detailKey") or keys[0]
    if len(set(keys)) != len(keys) or key not in keys:
        raise ChartError("请选择饼图中的有效主类别。")
    index = keys.index(key)
    parts = chart_points({"points": points[index].get("parts")}, MAX_PARTS)
    part_labels, part_values = zip(*parts)
    if min(part_values) <= 0 or not isclose(sum(part_values), values[index], rel_tol=1e-9):
        raise ChartError("子类别须为正数，合计须与所选扇区数值一致。")
    return index, part_labels, part_values


def render_bar_of_pie_chart(payload):
    from matplotlib.patches import ConnectionPatch
    from matplotlib.ticker import PercentFormatter

    payload = chart_object(payload)
    style = chart_object(payload.get("style", {}))
    labels, values = zip(*chart_points(payload, MAX_SLICES))
    if min(values) <= 0:
        raise ChartError("饼图扇区需要正数。")
    index, part_labels, part_values = _details(payload, values)
    total = sum(values)
    wedge_colors = chart_palette(style)
    pie_colors = [wedge_colors[i % len(wedge_colors)] for i in range(len(values))]

    with render_lock:
        figure, font = chart_figure(style, figsize=(10, 6))
        pie_axes, bar_axes = figure.subplots(1, 2, width_ratios=(1.3, 1))
        wedges = pie_axes.pie(
            [value / total for value in values], colors=pie_colors,
            explode=[0.07 if i == index else 0 for i in range(len(values))],
            startangle=-180 * values[index] / total, wedgeprops={"edgecolor": "white"},
        )[0]
        legend = pie_axes.legend(
            wedges, [f"{label[:18] or '空字符串'} · {value / total:.1%}" for label, value in zip(labels, values)],
            loc="upper center", bbox_to_anchor=(0.5, -0.02), ncols=2, prop=font, fontsize=9, frameon=False,
        )
        for label in legend.get_texts():
            label.set_parse_math(False)

        bottom = 0
        width = 0.62
        for part_index, (label, value) in enumerate(zip(part_labels, part_values)):
            share = value / values[index]
            draw_bars(bar_axes, 0, share, width=width, bottom=bottom, edgecolor="white",
                      color=wedge_colors[(index + part_index) % len(wedge_colors)],
                      label=f"{label[:18] or '空字符串'} · {share:.1%}")
            bottom += share
        bar_axes.set(xlim=(-0.8, 0.8), ylim=(0, 1), xticks=[])
        bar_axes.set_title(labels[index] or "空字符串", fontproperties=font, parse_math=False)
        bar_axes.yaxis.tick_right()
        bar_axes.yaxis.set_major_formatter(PercentFormatter(xmax=1))
        bar_axes.spines[["top", "left", "bottom"]].set_visible(False)
        legend = bar_axes.legend(loc="upper center", bbox_to_anchor=(0.5, -0.02), ncols=2,
                                 prop=font, fontsize=9, frameon=False)
        for label in legend.get_texts():
            label.set_parse_math(False)

        wedge = wedges[index]
        center_x, center_y = wedge.center
        for angle, height in ((max(wedge.theta1, -90), 0), (min(wedge.theta2, 90), 1)):
            theta = radians(angle)
            edge = (center_x + wedge.r * cos(theta), center_y + wedge.r * sin(theta))
            connector = ConnectionPatch(
                edge, (-width / 2, height), "data", "data", axesA=pie_axes, axesB=bar_axes,
                color="#7d8da1", linewidth=0.9, clip_on=False,
            )
            connector.set_in_layout(False)
            figure.add_artist(connector)
        return figure_png(figure)
