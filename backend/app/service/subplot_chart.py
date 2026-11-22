from math import ceil

from app.service.cartesian_charts import load_line_data, load_scatter_data
from app.service.subplot_layers import (
    draw_overlay_layer, layer_positions, layer_style, load_overlay, overlay_ticks, series_label, set_shared_ticks,
)
from app.util.chart import (
    DPI_OPTIONS, ChartError, chart_font, chart_number, chart_object, chart_text, draw_bars, draw_line, draw_scatter,
    figure_png, render_lock, style_choice, style_color, style_flag,
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
    details["xLabel"] = details["xLabel"] or chart_text(selection, "categoryColumn", required=True)
    if kind == "scatter":
        data = load_scatter_data(selection, require_group=False)
    else:
        if kind == "bar_line":
            secondary = chart_text(selection, "secondaryValueColumn", required=True)
            if secondary == selection.get("valueColumn"):
                raise ChartError("请选择不同的柱形与折线数值字段。")
        data = load_line_data(selection)
    details["yLabel"] = details["yLabel"] or data.get("yLabel") or data["seriesName"]
    details.update(
        data=data, fit=kind == "scatter" and style_flag(panel, "fit", False),
        primary=layer_style(panel.get("primaryStyle", {})),
        secondary=layer_style(panel.get("secondaryStyle", {}), 1),
    )
    return details


def _fit_scatter(axes, samples):
    """为散点添加一元线性拟合及基于拟合残差的指标。"""
    import numpy as np

    values = np.asarray(samples, dtype=float)
    x, y = values.T
    width = np.ptp(x)
    if len(x) < 2 or width == 0:
        return
    scaled_x = (x - x.mean()) / width
    slope, intercept = np.polyfit(scaled_x, y, 1)
    fitted = slope * scaled_x + intercept
    residual = np.sum((y - fitted) ** 2)
    variance = np.sum((y - y.mean()) ** 2)
    xs = np.array([x.min(), x.max()])
    draw_line(axes, xs, slope * (xs - x.mean()) / width + intercept, markers=False,
              color="#243858", linestyle="--", label="线性拟合")
    r2 = f"{(1 - residual / variance):.3f}" if variance > 0 else "—"
    rmse = np.sqrt(residual / len(x))
    axes.text(0.97, 0.04, f"R² = {r2}\nRMSE = {rmse:.3g}", transform=axes.transAxes,
              ha="right", va="bottom", fontsize=8, color="#243858")


def _draw_panel(axes, panel, font):
    """将已有的柱形、折线或散点图层画到当前子图。"""
    kind, data, right_axis = (panel[key] for key in ("kind", "data", "rightAxis"))
    tick_rotation = panel["style"]["tickRotation"]
    if kind == "overlay":
        coordinates, ticks = overlay_ticks(data)
        positions = [layer_positions(layer, coordinates) for layer in data]
        bar_x = sorted({x for layer, xs in zip(data, positions) if layer["kind"] == "bar" for x in xs})
        step = min((next_x - x for x, next_x in zip(bar_x, bar_x[1:])), default=1)
        second_width = step * (0.4 if all(layer["kind"] == "bar" for layer in data) else 0.65)
        right = axes.twinx() if right_axis else None
        first = draw_overlay_layer(axes, data[0], positions[0], 0, step * 0.65)
        second = draw_overlay_layer(
            right if right is not None else axes, data[1], positions[1], 1, second_width,
        )
        set_shared_ticks(axes, ticks, font, tick_rotation)
        if right is not None:
            right.set_ylabel((panel["rightLabel"] or data[1]["yLabel"])[:40], fontproperties=font, parse_math=False)
        return right, first or second

    primary = panel["primary"]
    secondary_style = panel["secondary"]

    if kind == "scatter":
        samples = []
        for index, series in enumerate(data["series"]):
            points = series["samples"]
            xs, ys = zip(*points)
            label = series_label(primary, series["label"], len(data["series"]) > 1)
            draw_scatter(axes, xs, ys, size=primary["markerSize"], alpha=primary["opacity"],
                         label=label, color=primary["color"] if index == 0 else f"C{index}")
            samples.extend(points)
        if panel["fit"] and len(samples) >= 2:
            _fit_scatter(axes, samples)
        return None, bool(samples)

    points = data["points"]
    if not points:
        return None, False
    positions = [point["x"] for point in points] if kind == "line" else list(range(len(points)))
    if kind in ("bar", "bar_line"):
        draw_bars(axes, positions, [point["value"] or 0 for point in points],
                  color=primary["color"], alpha=primary["opacity"], label=primary["label"] or data["seriesName"][:24])
    if kind == "line":
        series = data.get("series") or [{"label": data["seriesName"], "values": [p["value"] for p in points]}]
        for index, item in enumerate(series):
            draw_line(axes, positions, [value if value is not None else float("nan") for value in item["values"]],
                      color=primary["color"] if index == 0 else f"C{index}",
                      label=series_label(primary, item["label"], len(series) > 1), markers=primary["markers"],
                      linewidth=primary["lineWidth"], linestyle=primary["lineStyle"], alpha=primary["opacity"],
                      marker=primary["lineMarker"], markersize=primary["lineMarkerSize"])

    secondary = None
    if kind == "bar_line":
        secondary = axes.twinx() if right_axis else axes
        draw_line(secondary, positions, [point["secondary"] if point["secondary"] is not None else float("nan") for point in points],
                  color=secondary_style["color"], label=secondary_style["label"] or data["secondaryName"][:24],
                  markers=secondary_style["markers"], linewidth=secondary_style["lineWidth"],
                  linestyle=secondary_style["lineStyle"], alpha=secondary_style["opacity"],
                  marker=secondary_style["lineMarker"], markersize=secondary_style["lineMarkerSize"])
        if right_axis:
            secondary.set_ylabel((panel["rightLabel"] or data["secondaryName"])[:40], fontproperties=font, parse_math=False)
    set_shared_ticks(axes, list(zip(positions, (point["label"] for point in points))), font, tick_rotation)
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
