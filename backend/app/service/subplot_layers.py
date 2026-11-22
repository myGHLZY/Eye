from math import ceil

from app.service.cartesian_charts import load_line_data, load_scatter_data
from app.util.chart import (
    ChartError, chart_object, chart_text, draw_bars, draw_line, draw_scatter, style_choice, style_color, style_flag,
    style_range,
)

LAYER_KINDS = ("bar", "line", "scatter")
LAYER_COLORS = ("#4281bb", "#bb5635")
LINE_STYLES = {"solid": "-", "dashed": "--", "dotted": ":"}
LINE_MARKERS = {"circle": "o", "triangle": "^", "square": "s", "diamond": "D"}


def layer_style(raw, index=0):
    """读取独立图层的配色和图形参数。"""
    style = chart_object(raw)
    return {
        "color": style_color(style, "color", LAYER_COLORS[index]),
        "opacity": style_range(style, "opacity", 0.82 if index == 0 else 0.75, 0.15, 1),
        "markers": style_flag(style, "markers", True),
        "lineWidth": style_range(style, "lineWidth", 1.8, 0.5, 4),
        "lineStyle": LINE_STYLES[style_choice(style, "lineStyle", LINE_STYLES, "solid")],
        "lineMarker": LINE_MARKERS[style_choice(style, "lineMarker", LINE_MARKERS, "circle")],
        "lineMarkerSize": style_range(style, "lineMarkerSize", 4, 2, 10),
        "markerSize": style_range(style, "markerSize", 28, 10, 100),
        "label": chart_text(style, "legendLabel", maximum=40),
    }


def load_overlay(panel):
    """独立读取两个图层并确认横轴类型一致。"""
    entries = panel.get("layers")
    if not isinstance(entries, list) or len(entries) != 2:
        raise ChartError("叠加子图需要两个图层。")
    layers = []
    for index, raw in enumerate(entries):
        entry = chart_object(raw)
        kind = style_choice(entry, "kind", LAYER_KINDS, "bar")
        selection = chart_object(entry.get("selection"))
        if kind == "scatter":
            data = load_scatter_data(selection, require_group=False)
        else:
            data = load_line_data(selection)
            if not data["series"]:
                data["series"] = [{"label": data["seriesName"], "values": [point["value"] for point in data["points"]]}]
                if "secondaryName" in data:
                    data["series"].append({
                        "label": data["secondaryName"], "values": [point["secondary"] for point in data["points"]],
                    })
        axis_type = ("number" if data["series"] else None) if kind == "scatter" else data["xType"]
        second_style = entry.get("secondSeriesStyle")
        layers.append({
            "kind": kind, "data": data, "style": layer_style(entry.get("style", {}), index),
            "secondSeriesStyle": layer_style(second_style, index) if second_style is not None else None,
            "axisType": axis_type, "xLabel": chart_text(selection, "categoryColumn", required=True),
            "yLabel": data.get("yLabel") or data["seriesName"],
        })
    types = {layer["axisType"] for layer in layers if layer["axisType"]}
    if len(types) > 1:
        raise ChartError("两个图层的横轴类型须一致，请同时选择类别、日期或数值字段。")
    return layers


def _category_key(point):
    """使用数据点的稳定键对齐类别。"""
    return point.get("key", point["label"])


def overlay_ticks(layers):
    """合并两个图层的类别或日期刻度，并建立共享坐标。"""
    axis_type = next((layer["axisType"] for layer in layers if layer["axisType"]), "number")
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


def draw_overlay_layer(axes, layer, positions, index, bar_width):
    """将一个子图的全部系列画在共享坐标轴上。"""
    kind, series = layer["kind"], layer["data"]["series"]
    plotted = False
    for series_index, item in enumerate(series):
        style, label = _overlay_series_style(layer, series_index, item["label"])
        options = {"label": label, "color": style["color"], "alpha": style["opacity"]}
        if kind == "scatter":
            xs, ys = zip(*item["samples"])
            draw_scatter(axes, xs, ys, size=style["markerSize"], zorder=3 + index, **options)
            plotted = True
        elif kind == "bar":
            width = bar_width / len(series)
            offset = (series_index - (len(series) - 1) / 2) * width
            present = [(x + offset, value) for x, value in zip(positions, item["values"]) if value is not None]
            if present:
                xs, ys = zip(*present)
                draw_bars(axes, xs, ys, width=width, zorder=2 + index / 10, **options)
                plotted = True
        elif positions:
            xy = sorted(zip(positions, item["values"]), key=lambda point: point[0])
            xs, values = zip(*xy)
            ys = [value if value is not None else float("nan") for value in values]
            draw_line(axes, xs, ys, markers=style["markers"] or len(positions) == 1,
                      marker=style["lineMarker"], markersize=style["lineMarkerSize"], linewidth=style["lineWidth"],
                      linestyle=style["lineStyle"], zorder=3 + index, **options)
            plotted = plotted or any(value is not None for value in values)
    return plotted


def set_shared_ticks(axes, ticks, font, rotation):
    """在共享轴上按可见密度显示类别或日期标签。"""
    if not ticks:
        return
    positions = list(range(0, len(ticks), max(1, ceil(len(ticks) / 6))))
    if positions[-1] != len(ticks) - 1:
        positions.append(len(ticks) - 1)
    degrees = (28 if len(positions) > 4 else 0) if rotation is None else rotation
    axes.set_xticks(
        [ticks[index][0] for index in positions], [ticks[index][1][:16] for index in positions],
        rotation=degrees, ha="right" if degrees else "center", fontsize=8, fontproperties=font, parse_math=False,
    )
