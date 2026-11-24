from collections import Counter

from app.service.cartesian_charts import load_line_data, load_scatter_data
from app.service.scatter_style import draw_scatter_guides, draw_scatter_series, scatter_style
from app.util.chart import (
    ChartError, chart_object, chart_text, draw_bars, draw_line, style_choice, style_color, style_flag,
    style_range,
)

LAYER_KINDS = ("bar", "line", "scatter")
LAYER_COLORS = ("#4281bb", "#bb5635")
LINE_STYLES = {"solid": "-", "dashed": "--", "dotted": ":"}
LINE_MARKERS = {"circle": "o", "triangle": "^", "square": "s", "diamond": "D"}


def layer_style(raw, index=0, kind=None):
    """读取独立图层的配色和图形参数。"""
    style = chart_object(raw)
    opacity = 0.82 if index == 0 else 0.75
    appearance = {
        "color": style_color(style, "color", LAYER_COLORS[index]),
        "label": chart_text(style, "legendLabel", maximum=40),
    }
    if kind == "scatter":
        return {**appearance, **scatter_style(style, size=28, opacity=opacity)}
    return {
        **appearance,
        "opacity": style_range(style, "opacity", opacity, 0.15, 1),
        "markers": style_flag(style, "markers", True),
        "lineWidth": style_range(style, "lineWidth", 1.8, 0.5, 4),
        "lineStyle": LINE_STYLES[style_choice(style, "lineStyle", LINE_STYLES, "solid")],
        "lineMarker": LINE_MARKERS[style_choice(style, "lineMarker", LINE_MARKERS, "circle")],
        "lineMarkerSize": style_range(style, "lineMarkerSize", 4, 2, 10),
    }


def load_subplot_layer(raw, index=0):
    """加载一种图的数据和样式，供单独子图和重合子图复用。"""
    entry = chart_object(raw)
    kind = style_choice(entry, "kind", LAYER_KINDS, "bar")
    selection = chart_object(entry.get("selection"))
    if kind == "scatter":
        data = load_scatter_data(selection)
    else:
        data = load_line_data(selection)
        if not data["series"]:
            data["series"] = [{"label": data["seriesName"], "values": [point["value"] for point in data["points"]]}]
            if "secondaryName" in data:
                data["series"].append({
                    "label": data["secondaryName"], "values": [point["secondary"] for point in data["points"]],
                })
    second_style = entry.get("secondSeriesStyle")
    return {
        "kind": kind, "data": data, "style": layer_style(entry.get("style", {}), index, kind),
        "secondSeriesStyle": layer_style(second_style, index, kind) if second_style is not None else None,
        "xLabel": chart_text(selection, "categoryColumn", required=True),
        "yLabel": data.get("yLabel") or data["seriesName"],
    }


def load_overlay(panel):
    """独立读取两个图层并确认横轴类型一致。"""
    entries = panel.get("layers")
    if not isinstance(entries, list) or len(entries) != 2:
        raise ChartError("叠加子图需要两个图层。")
    layers = [load_subplot_layer(entry, index) for index, entry in enumerate(entries)]
    types = {layer["data"]["xType"] for layer in layers} - {None}
    if len(types) > 1:
        raise ChartError("两个图层的横轴类型须一致，请同时选择类别、日期或数值字段。")
    return layers

def _category_key(point):
    """使用数据点的稳定键对齐类别。"""
    return point.get("key", point["label"])


def overlay_ticks(layers):
    """合并两个图层的类别或日期刻度，并建立共享坐标。"""
    axis_type = next((layer["data"]["xType"] for layer in layers if layer["data"]["xType"]), "number")
    labels = {}
    for layer in layers:
        for point in layer["data"].get("points", []):
            key = _category_key(point) if axis_type == "category" else point["x"]
            labels.setdefault(key, point["label"] or "空字符串")
    if axis_type == "category":
        ordered = sorted(labels, key=labels.get)
        return {key: index for index, key in enumerate(ordered)}, list(enumerate(labels[key] for key in ordered))
    if axis_type == "date":
        return None, sorted(labels.items())
    return None, []


def series_label(style, group_name, multiple):
    """按需为图层的分组图例添加用户设定的前缀。"""
    label = style["label"]
    if label and multiple:
        return f"{label} · {group_name}"[:60]
    return (label or group_name)[:60]


def layer_positions(layer, coordinates):
    """把原始横轴值映射到共享坐标。"""
    points = layer["data"].get("points", [])
    if coordinates is None:
        return [point["x"] for point in points]
    return [coordinates[_category_key(point)] for point in points]


def _overlay_series_style(layer, index, name):
    """为子图中的每个系列选取颜色和图例。"""
    style = layer["style"]
    if index < 2 and layer["secondSeriesStyle"] is not None:
        style = style if index == 0 else layer["secondSeriesStyle"]
        return style, style["label"] or name[:60]
    label = series_label(style, name, len(layer["data"]["series"]) > 1)
    return (style if index == 0 else {**style, "color": f"C{index}"}), label


def _original_bar_slots(positions, total_width):
    """同一横轴值有多条记录时，在该位置并排画柱。"""
    counts = Counter(positions)
    used = Counter()
    slots = []
    for x in positions:
        width = total_width / counts[x]
        slots.append((x + (used[x] - (counts[x] - 1) / 2) * width, width))
        used[x] += 1
    return slots


def draw_subplot_layer(axes, layer, positions, index, bar_width, font, *, overlay=False):
    """将一个子图的全部系列画在共享坐标轴上。"""
    kind, data = layer["kind"], layer["data"]
    series = data["series"]
    raw = data.get("rawRecords")
    slots = _original_bar_slots(positions, bar_width) if kind == "bar" and raw else []
    point_positions = dict(zip((point["x"] for point in layer["data"]["points"]), positions)) if kind == "scatter" else {}
    plotted = False
    for series_index, item in enumerate(series):
        style, label = _overlay_series_style(layer, series_index, item["label"])
        if kind == "scatter":
            samples = [(point_positions.get(x, x), y) for x, y in item["samples"]]
            draw_scatter_series(axes, samples, style, style["color"], label, zorder=3 + index)
            plotted = True
            continue
        options = {"label": label, "color": style["color"], "alpha": style["opacity"]}
        if kind == "bar":
            width = bar_width / len(series)
            offset = (series_index - (len(series) - 1) / 2) * width
            bar_slots = slots if raw else [(x + offset, width) for x in positions]
            present = [(x, value, size) for (x, size), value in zip(bar_slots, item["values"]) if value is not None]
            if present:
                xs, ys, widths = zip(*present)
                draw_bars(axes, xs, ys, width=widths, zorder=2 + index / 10, **options)
                plotted = True
        elif positions:
            xy = sorted(zip(positions, item["values"]), key=lambda point: point[0])
            if raw and len(series) > 1:
                xy = [pair for pair in xy if pair[1] is not None]
            if not xy:
                continue
            xs, values = zip(*xy)
            ys = [value if value is not None else float("nan") for value in values]
            draw_line(axes, xs, ys, markers=style["markers"] or len(positions) == 1,
                      marker=style["lineMarker"], markersize=style["lineMarkerSize"], linewidth=style["lineWidth"],
                      linestyle=style["lineStyle"], zorder=3 + index, **options)
            plotted = plotted or any(value is not None for value in values)
    if kind == "scatter":
        draw_scatter_guides(axes, series, layer["style"], layer["data"]["xType"], font, layer=index if overlay else None)
    return plotted
