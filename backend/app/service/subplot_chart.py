from math import ceil

from app.service.cartesian_charts import load_line_data
from app.service.subplot_layers import (
    draw_subplot_layer, layer_positions, layer_style, load_overlay, load_subplot_layer, overlay_ticks,
)
from app.util.chart import (
    DPI_OPTIONS, ChartError, chart_font, chart_number, chart_object, chart_text, draw_bars, draw_line,
    figure_png, render_lock, set_chart_ticks, style_choice, style_color, style_flag,
)

MAX_PANELS = 6
PANEL_KINDS = ("bar", "line", "bar_line", "scatter", "overlay")
LEGEND_LOCATIONS = {"auto": "best", "top-left": "upper left", "top-right": "upper right", "bottom": "lower center"}


def _axis_limits(style, low_key, high_key):
    """读取可留空的纵轴上下限。"""
    values = [style.get(low_key), style.get(high_key)]
    if any(value is not None and type(value) not in (int, float) for value in values):
        raise ChartError()
    bounds = tuple(chart_number(value) if value is not None else None for value in values)
    if None not in bounds and bounds[0] >= bounds[1]:
        raise ChartError("纵轴上限要大于下限。")
    return bounds


def _panel_style(raw):
    """读取单个子图的画布、网格、坐标轴和图例设置。"""
    style = chart_object(raw)
    rotation = style.get("tickRotation")
    if rotation is not None and (type(rotation) is not int or rotation not in (0, 25, 45)):
        raise ChartError()
    return {
        "backgroundColor": style_color(style, "backgroundColor", "#ffffff"),
        "grid": style_choice(style, "grid", ("none", "x", "y", "both"), "both"),
        "frame": style_choice(style, "frame", ("none", "axes", "box"), "box"),
        "legend": style_choice(style, "legend", ("inherit", "none", *LEGEND_LOCATIONS), "inherit"),
        "legendFrame": style_flag(style, "legendFrame", False),
        "tickRotation": rotation,
        "limits": _axis_limits(style, "yMin", "yMax"),
        "rightLimits": _axis_limits(style, "rightYMin", "rightYMax"),
    }


def _load_panel(panel):
    """根据面板配置读取本子图的数据。"""
    panel = chart_object(panel)
    kind = style_choice(panel, "kind", PANEL_KINDS, "bar")
    details = {
        "kind": kind,
        "title": chart_text(panel, "title", maximum=60),
        "xLabel": chart_text(panel, "xLabel", maximum=60),
        "yLabel": chart_text(panel, "yLabel", maximum=60),
        "rightLabel": chart_text(panel, "rightLabel", maximum=60),
        "style": _panel_style(panel.get("style", {})),
        "rightAxis": kind in ("bar_line", "overlay") and style_flag(panel, "rightAxis", False),
    }
    if kind == "overlay":
        layers = load_overlay(panel)
        details.update(data=layers)
        details["xLabel"] = details["xLabel"] or layers[0]["xLabel"]
        details["yLabel"] = details["yLabel"] or layers[0]["yLabel"]
        return details

    selection = chart_object(panel.get("selection"))
    primary = chart_object(panel.get("primaryStyle", {}))
    if kind != "bar_line":
        if kind == "scatter" and style_flag(panel, "fit", False):
            primary = {**primary, "fit": True}
        layer = load_subplot_layer({"kind": kind, "selection": selection, "style": primary})
        details.update(data=layer)
        details["xLabel"] = details["xLabel"] or layer["xLabel"]
        details["yLabel"] = details["yLabel"] or layer["yLabel"]
        return details

    secondary = chart_text(selection, "secondaryValueColumn", required=True)
    if secondary == selection.get("valueColumn"):
        raise ChartError("请选择不同的柱形与折线数值字段。")
    data = load_line_data(selection)
    details["xLabel"] = details["xLabel"] or chart_text(selection, "categoryColumn", required=True)
    details["yLabel"] = details["yLabel"] or data["seriesName"]
    details.update(data=data, primary=layer_style(primary), secondary=layer_style(panel.get("secondaryStyle", {}), 1))
    return details

def _draw_overlay(axes, panel, font):
    """对齐两张图的横轴，复用各图的绘制函数。"""
    layers = panel["data"]
    coordinates, ticks = overlay_ticks(layers)
    positions = [layer_positions(layer, coordinates) for layer in layers]
    bar_x = sorted({x for layer, xs in zip(layers, positions) if layer["kind"] == "bar" for x in xs})
    step = min((next_x - x for x, next_x in zip(bar_x, bar_x[1:])), default=1)
    both_bars = all(layer["kind"] == "bar" for layer in layers)
    right = axes.twinx() if panel["rightAxis"] else None
    plotted = False
    for index, (layer, xs) in enumerate(zip(layers, positions)):
        target = right if index == 1 and right is not None else axes
        width = step * (0.4 if index == 1 and both_bars else 0.65)
        plotted = draw_subplot_layer(target, layer, xs, index, width, font, overlay=True) or plotted
    set_chart_ticks(axes, ticks, font, panel["style"]["tickRotation"])
    if right is not None:
        right.set_ylabel((panel["rightLabel"] or layers[1]["yLabel"])[:40], fontproperties=font, parse_math=False)
    return right, plotted


def _draw_panel(axes, panel, font):
    """将已有的柱形、折线或散点图层画到当前子图。"""
    kind, data, right_axis = (panel[key] for key in ("kind", "data", "rightAxis"))
    tick_rotation = panel["style"]["tickRotation"]
    if kind == "overlay":
        return _draw_overlay(axes, panel, font)

    if kind != "bar_line":
        points = data["data"]["points"]
        positions = list(range(len(points))) if kind == "bar" else layer_positions(data, None)
        visible = draw_subplot_layer(axes, data, positions, 0, 0.65, font)
        set_chart_ticks(axes, list(zip(positions, (point["label"] for point in points))), font, tick_rotation)
        return None, visible

    points = data["points"]
    if not points:
        return None, False
    positions = list(range(len(points)))
    primary, secondary_style = panel["primary"], panel["secondary"]
    draw_bars(axes, positions, [point["value"] or 0 for point in points],
              color=primary["color"], alpha=primary["opacity"], label=primary["label"] or data["seriesName"][:24])
    secondary = axes.twinx() if right_axis else axes
    draw_line(secondary, positions, [point["secondary"] if point["secondary"] is not None else float("nan") for point in points],
              color=secondary_style["color"], label=secondary_style["label"] or data["secondaryName"][:24],
              markers=secondary_style["markers"], linewidth=secondary_style["lineWidth"],
              linestyle=secondary_style["lineStyle"], alpha=secondary_style["opacity"],
              marker=secondary_style["lineMarker"], markersize=secondary_style["lineMarkerSize"])
    if right_axis:
        secondary.set_ylabel((panel["rightLabel"] or data["secondaryName"])[:40], fontproperties=font, parse_math=False)
    set_chart_ticks(axes, list(zip(positions, (point["label"] for point in points))), font, tick_rotation)
    return secondary if right_axis else None, True

def _apply_axes_style(axes, right, style):
    """应用绘图区背景、网格、边框和纵轴上下限。"""
    axes.set_facecolor(style["backgroundColor"])
    axes.set_axisbelow(True)
    axes.grid(False)
    if style["grid"] != "none":
        axes.grid(True, axis=style["grid"], color="#e5edf6", linewidth=0.7)
    visible_sides = {"none": (), "axes": ("left", "bottom"), "box": ("left", "bottom", "right", "top")}
    for name, spine in axes.spines.items():
        spine.set_visible(name in visible_sides[style["frame"]])
    for target, limits in ((axes, style["limits"]), (right, style["rightLimits"])):
        if target is None or limits == (None, None):
            continue
        current = target.get_ylim()
        low, high = (actual if chosen is None else chosen for actual, chosen in zip(current, limits))
        if low >= high:
            raise ChartError("纵轴上限要大于下限。")
        target.set_ylim(low, high)
    if right is not None:
        for name, spine in right.spines.items():
            spine.set_visible(name == "right" and style["frame"] != "none")
    if style["tickRotation"] is not None:
        degrees = style["tickRotation"]
        for label in axes.get_xticklabels():
            label.set_rotation(degrees)
            label.set_ha("right" if degrees else "center")


def _panel_legend(axes, right, style, show_legend, font):
    """合并左右纵轴的图例，允许按子图覆盖总图默认值。"""
    placement = style["legend"]
    if placement == "none" or (placement == "inherit" and not show_legend):
        return
    handles, names = axes.get_legend_handles_labels()
    if right is not None:
        extra_handles, extra_names = right.get_legend_handles_labels()
        handles.extend(extra_handles)
        names.extend(extra_names)
    if handles:
        location = LEGEND_LOCATIONS["auto" if placement == "inherit" else placement]
        target = right if right is not None else axes
        legend = target.legend(handles, names, prop=font, frameon=style["legendFrame"], fontsize=8, loc=location)
        for label in legend.get_texts():
            label.set_parse_math(False)


def render_subplot_chart(payload):
    """组合独立子图，并将不足一行的子图居中。"""
    payload = chart_object(payload)
    style = chart_object(payload.get("style", {}))
    entries = payload.get("panels")
    if not isinstance(entries, list) or not 1 <= len(entries) <= MAX_PANELS:
        raise ChartError(f"组合图支持 1 至 {MAX_PANELS} 个子图。")
    columns = min(len(entries), style_choice(style, "columns", (1, 2, 3), 2))
    dpi = style_choice(style, "dpi", DPI_OPTIONS, 130)
    title = chart_text(style, "title", maximum=60)
    caption = chart_text(style, "caption", maximum=120)
    show_legend = style_flag(style, "showLegend", True)
    panels = [_load_panel(entry) for entry in entries]
    rows = ceil(len(panels) / columns)

    with render_lock:
        from matplotlib.figure import Figure

        font = chart_font()
        figure = Figure(figsize=(4.4 * columns, 3.5 * rows), dpi=dpi, layout="constrained", facecolor="white")
        grid = figure.add_gridspec(rows, columns * 2)
        if title:
            figure.suptitle(title, fontproperties=font, parse_math=False)
        if caption:
            figure.supxlabel(caption, fontproperties=font, parse_math=False, fontsize=10)
        for index, panel in enumerate(panels):
            row, column = divmod(index, columns)
            remaining = min(columns, len(panels) - row * columns)
            start = columns - remaining + 2 * column
            axes = figure.add_subplot(grid[row, start:start + 2])
            axes.set_title(f"({chr(97 + index)}) {panel['title']}".rstrip(), loc="left", fontproperties=font, parse_math=False)
            axes.set_xlabel(panel["xLabel"][:40], fontproperties=font, parse_math=False)
            axes.set_ylabel(panel["yLabel"][:40], fontproperties=font, parse_math=False)
            right, visible = _draw_panel(axes, panel, font)
            _apply_axes_style(axes, right, panel["style"])
            if not visible:
                axes.text(0.5, 0.5, "没有可用记录", transform=axes.transAxes,
                          fontproperties=font, ha="center", va="center")
            _panel_legend(axes, right, panel["style"], show_legend, font)
        return figure_png(figure)
