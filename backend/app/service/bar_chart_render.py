from io import BytesIO

from app.service.bar_chart_annotations import comparisons, draw_bar_labels, draw_comparisons, error_bars
from app.util.chart import (
    DPI_OPTIONS, ChartError, chart_font, chart_object, chart_points, chart_text, figure_png,
    render_lock, style_choice, style_color, style_flag, style_range,
)

MAX_BARS = 24
BAR_RENDERER_REVISION = "3"
CHART_SIZES = {"wide": (9, 5), "square": (7, 7), "portrait": (6, 8)}
FRAME_SIDES = {"none": (), "axes": ("left", "bottom"), "plot": ("top", "right", "left", "bottom"), "canvas": ()}
GRID_STYLES = {"solid": "-", "dashed": "--", "dotted": ":"}
LEGEND_POSITIONS = {"auto": "best", "top-right": "upper right", "top-left": "upper left", "bottom": "outside lower center"}


def _bar_list(style: dict, key: str, size: int, max_length: int) -> list[str] | None:
    """读取与柱数量相同的一组图例名称或颜色。"""
    if key not in style:
        return None
    entries = style[key]
    if not isinstance(entries, list) or len(entries) != size or any(
        not isinstance(entry, str) or len(entry) > max_length for entry in entries
    ):
        raise ChartError()
    return entries


def _new_figure(style: dict):
    """创建画布，并按设置绘制坐标轴外框。"""
    from matplotlib.figure import Figure

    shape = style_choice(style, "chartSize", CHART_SIZES, "wide")
    dpi = style_choice(style, "dpi", DPI_OPTIONS, 130)
    frame = style_choice(style, "frameMode", FRAME_SIDES, "none")
    frame_color = style_color(style, "frameColor", "#485b76")
    frame_width = style_range(style, "frameWidth", 1, 0.5, 3)
    figure_color = style_color(style, "figureColor", "#ffffff")
    plot_color = style_color(style, "plotColor", "#ffffff")
    if style_flag(style, "transparentBackground", False):
        figure_color = plot_color = "none"

    # The canvas edge is centered on the image boundary, so only half its stroke is visible.
    figure = Figure(
        figsize=CHART_SIZES[shape], dpi=dpi, layout="constrained", facecolor=figure_color,
        edgecolor=frame_color if frame == "canvas" else "none",
        linewidth=frame_width * 2 if frame == "canvas" else 0,
    )
    axes = figure.subplots()
    axes.set_facecolor(plot_color)
    for side, spine in axes.spines.items():
        spine.set_visible(side in FRAME_SIDES[frame])
        spine.set_color(frame_color)
        spine.set_linewidth(frame_width)
    return figure, axes


def _draw_grid(axes, style: dict) -> None:
    """设置横纵网格和零值基线。"""
    if style_flag(style, "showZeroLine", True):
        axes.axhline(0, color="#bbc8dc", linewidth=0.9)
    color = style_color(style, "gridColor", "#e4ebf4")
    line = GRID_STYLES[style_choice(style, "gridStyle", GRID_STYLES, "solid")]
    axes.set_axisbelow(True)
    for axis, visible in (
        ("x", style_flag(style, "showVerticalGrid", False)),
        ("y", style_flag(style, "showGrid", True)),
    ):
        if visible:
            axes.grid(True, axis=axis, color=color, linewidth=0.8, linestyle=line)
        else:
            axes.grid(False, axis=axis)


def render_bar_chart(payload) -> BytesIO:
    """把柱状图数据、样式和统计标注渲染成 PNG。"""
    payload = chart_object(payload)
    points = chart_points(payload, MAX_BARS)
    style = chart_object(payload.get("style", {}))
    errors = error_bars(style, len(points))
    marks = comparisons(style, len(points))
    color = style_color(style, "color", "#356fe5") if style.get("color") != "" else "#356fe5"
    title = chart_text(style, "title", maximum=60)
    legend_label = chart_text(style, "legendLabel", maximum=60) or "数值"
    legend_title = chart_text(style, "legendTitle", maximum=60)
    x_label = chart_text(style, "xLabel", maximum=60)
    y_label = chart_text(style, "yLabel", maximum=60)
    bar_colors = _bar_list(style, "barColors", len(points), 40)
    bar_labels = _bar_list(style, "barLabels", len(points), 60)
    show_legend = style_flag(style, "showLegend", True)
    show_values = style_flag(style, "showValues", True)
    legend_position = style_choice(style, "legendPosition", LEGEND_POSITIONS, "auto")
    outline = style_flag(style, "showBarOutline", False)
    outline_color = style_color(style, "barOutlineColor", "#263c5a")
    outline_width = style_range(style, "barOutlineWidth", 1, 0.5, 3)
    value_unit = chart_text(style, "valueUnit", maximum=1)
    if value_unit not in ("", "%"):
        raise ChartError()
    bar_spacing = style_range(style, "barSpacing", 1, 0.7, 2)
    y_tick_bins = style.get("yTickBins")
    if y_tick_bins is not None and (type(y_tick_bins) is not int or not 3 <= y_tick_bins <= 12):
        raise ChartError()

    with render_lock:
        from matplotlib.colors import is_color_like
        from matplotlib.ticker import MaxNLocator

        if bar_colors is not None and any(not is_color_like(value) for value in bar_colors):
            raise ChartError()

        font = chart_font()
        figure, axes = _new_figure(style)
        labels, values = zip(*points)
        positions = [index * bar_spacing for index in range(len(points))]
        if bar_labels is None and bar_colors is not None:
            bar_labels = [label[:60] for label in labels]
        bars = axes.bar(
            positions, values, color=bar_colors if bar_colors is not None else color,
            width=0.65, label=bar_labels if bar_labels is not None else legend_label,
            edgecolor=outline_color if outline else "none", linewidth=outline_width if outline else 0,
        )
        error_points = [(x, y, error) for x, y, error in zip(positions, values, errors) if error is not None]
        if error_points:
            xs, ys, amplitudes = zip(*error_points)
            axes.errorbar(xs, ys, yerr=amplitudes, fmt="none", capsize=4, ecolor="#263c5a", zorder=4)
        axis_labels = [label if len(label) <= 15 else label[:14] + "…" for label in labels]
        rotate = len(points) > 6 or any(len(label) > 6 for label in axis_labels)
        axes.set_xticks(positions, axis_labels, rotation=35 if rotate else 0,
                        ha="right" if rotate else "center", fontproperties=font, fontsize=9)
        if title:
            axes.set_title(title, fontproperties=font, fontsize=15, color="#15243b", pad=16, parse_math=False)
        if x_label:
            axes.set_xlabel(x_label, fontproperties=font, parse_math=False)
        if y_label:
            axes.set_ylabel(y_label, fontproperties=font, parse_math=False)
        axes.margins(y=0.16)
        _draw_grid(axes, style)
        axes.tick_params(axis="both", length=0, colors="#485b76", labelsize=9)
        if value_unit == "%":
            axes.yaxis.set_major_formatter("{x:g}%")
        if y_tick_bins is not None:
            axes.yaxis.set_major_locator(MaxNLocator(nbins=y_tick_bins))
        for label in axes.get_xticklabels():
            label.set_parse_math(False)
        if show_values:
            draw_bar_labels(axes, bars, positions, values, errors, value_unit)
        if marks:
            draw_comparisons(axes, positions, values, errors, marks, show_values)
        if show_legend:
            handles, names = axes.get_legend_handles_labels()
            if names:
                below = legend_position == "bottom" or (legend_position == "auto" and (marks or len(names) > 6))
                above = bool(marks) and legend_position in ("top-left", "top-right")
                outside = below or above
                owner = figure if outside else axes
                location = LEGEND_POSITIONS["bottom" if below else legend_position]
                if above:
                    location = "outside " + location
                columns = min(len(names), 2 if figure.get_figwidth() <= 6 else 3) if outside else 1
                if outside or len(names) > 6:
                    names = [name if len(name) <= 18 else name[:17] + "…" for name in names]
                legend = owner.legend(
                    handles, names, title=legend_title, prop=font, title_fontproperties=font,
                    frameon=False, loc=location, ncols=columns,
                )
                for label in [*legend.get_texts(), legend.get_title()]:
                    label.set_parse_math(False)

        return figure_png(figure)
