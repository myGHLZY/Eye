from io import BytesIO
from math import sqrt

from sqlalchemy import func, select

from app.service.bar_chart_annotations import comparisons, draw_bar_labels, draw_comparisons, error_bars
from app.service.chart_support import AGGREGATIONS, category_point, grouping_columns, paired_totals
from app.service.database_connection import database_engine_for_connection
from app.util.chart import (
    DPI_OPTIONS, ChartError, chart_font, chart_number, chart_object, chart_points, chart_text, draw_bars, figure_png,
    render_lock, style_choice, style_color, style_flag, style_range,
)

BarChartError = ChartError

__all__ = ["BAR_RENDERER_REVISION", "BarChartError", "load_bar_data", "render_bar_chart"]

MAX_BARS = 24
BAR_RENDERER_REVISION = "4"
MAX_SERIES = 8
CHART_SIZES = {"wide": (9, 5), "square": (7, 7), "portrait": (6, 8)}
FRAME_SIDES = {"none": (), "axes": ("left", "bottom"), "plot": ("top", "right", "left", "bottom"), "canvas": ()}
GRID_STYLES = {"solid": "-", "dashed": "--", "dotted": ":"}
LEGEND_POSITIONS = {"auto": "best", "top-right": "upper right", "top-left": "upper left", "bottom": "outside lower center"}




def load_bar_data(payload) -> dict:
    """按所选分类聚合 MySQL 数据并返回柱状图数据点。"""
    payload = chart_object(payload)
    if payload.get("groupColumn"):
        return _load_grouped_bars(payload)
    connection_id = chart_text(payload, "connectionId", required=True)
    table_name = chart_text(payload, "table", required=True)
    category_name = chart_text(payload, "categoryColumn", required=True)
    aggregation = chart_text(payload, "aggregation", required=True)
    if aggregation not in AGGREGATIONS:
        raise ChartError("所选聚合方式无效。")
    aggregation_label, aggregate = AGGREGATIONS[aggregation]
    is_share = aggregation == "share"
    metric_name = chart_text(payload, "valueColumn", required=True) if aggregation != "count" else ""

    with database_engine_for_connection(connection_id) as engine, engine.connect() as connection:
        _, category, metric = grouping_columns(connection, table_name, category_name, metric_name)
        conditions = [category.is_not(None)]
        if metric is not None:
            conditions.append(metric.is_not(None))
        value = aggregate(metric) if metric is not None else aggregate()
        if is_share:
            total = select(func.sum(metric)).where(*conditions).correlate(None).scalar_subquery()
            # Use floating-point division even when the underlying metric is an integer.
            value = value / (func.nullif(total, 0) * 1.0) * 100
        sample_stats = (func.count(metric), func.stddev_samp(metric)) if aggregation == "average" else ()
        statement = (
            select(category, value.label("chart_value"), *sample_stats)
            .where(*conditions)
            .group_by(category)
            .order_by(value.desc(), category.asc())
            .limit(MAX_BARS + 1)
        )
        rows = connection.execute(statement).all()

    if is_share and rows and rows[0][1] is None:
        raise ChartError("数值字段的总和为 0，无法计算占比。")
    result = {
        "points": [_data_point(*row) for row in rows[:MAX_BARS]],
        "seriesName": f"{metric_name}（{aggregation_label}）" if metric_name else aggregation_label,
        "truncated": len(rows) > MAX_BARS,
    }
    if is_share:
        result["valueUnit"] = "%"
    return result


def _data_point(category, value, sample_size=None, sample_sd=None) -> dict:
    """序列化一个分类，并附上平均值的样本统计。"""
    point = category_point(category, value)
    if sample_size is not None:
        sd = chart_number(sample_sd) if sample_size >= 2 and sample_sd is not None else None
        point.update(sampleSize=sample_size, sampleSd=sd, sampleSem=sd / sqrt(sample_size) if sd is not None else None)
    return point


def _load_grouped_bars(payload) -> dict:
    """将两字段的汇总结果展开为横轴分类和系列矩阵。"""
    rows, truncated, name = paired_totals(payload, MAX_BARS * MAX_SERIES, allowed=AGGREGATIONS)
    categories = list(dict.fromkeys(category for category, _, _ in rows))
    groups = list(dict.fromkeys(group for _, group, _ in rows))
    if truncated or len(categories) > MAX_BARS or len(groups) > MAX_SERIES:
        raise ChartError(f"横轴最多 {MAX_BARS} 个分类，系列最多 {MAX_SERIES} 个，请选择分类较少的字段。")

    values = {(category, group): chart_number(value) for category, group, value in rows}
    series = [
        {**category_point(group, 0, stable_key=True), "values": [values.get((category, group), 0) for category in categories]}
        for group in groups
    ]
    for item in series:
        del item["value"]
    points = [
        category_point(category, sum(item["values"][index] for item in series))
        for index, category in enumerate(categories)
    ]
    result = {"points": points, "series": series, "seriesName": name, "truncated": False}
    if payload["aggregation"] == "share":
        result["valueUnit"] = "%"
    return result


def read_series(payload, size: int) -> list:
    """读取与横轴分类一一对应的系列数值。"""
    entries = payload.get("series", [])
    if not isinstance(entries, list) or len(entries) > MAX_SERIES:
        raise ChartError()
    series = []
    for raw in entries:
        entry = chart_object(raw)
        values = entry.get("values")
        if not isinstance(values, list) or len(values) != size or any(type(value) not in (int, float) for value in values):
            raise ChartError()
        series.append((chart_text(entry, "label") or "空字符串", [chart_number(value) for value in values]))
    return series


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


def _draw_series(axes, series, positions, colors, layout, bar_spacing, border, show_values, unit):
    """绘制并列或分正负方向堆叠的系列柱。"""
    width = min(0.65, bar_spacing * 0.85)
    if layout == "grouped":
        width /= len(series)
    positive = [0] * len(positions)
    negative = positive.copy()
    for index, ((label, values), color) in enumerate(zip(series, colors)):
        if layout == "stacked":
            bottom = [upper if value >= 0 else lower for upper, lower, value in zip(positive, negative, values)]
            bars = draw_bars(axes, positions, values, width=width, bottom=bottom, color=color, label=label, **border)
            positive = [base + max(value, 0) for base, value in zip(positive, values)]
            negative = [base + min(value, 0) for base, value in zip(negative, values)]
        else:
            offset = (index - (len(series) - 1) / 2) * width
            bars = draw_bars(axes, [x + offset for x in positions], values, width=width, color=color, label=label, **border)
        if show_values:
            labels = [f"{value:.4g}{unit}" if value else "" for value in values]
            axes.bar_label(bars, labels=labels, label_type="center" if layout == "stacked" else "edge",
                           padding=0 if layout == "stacked" else 3, fontsize=8)


def _draw_gradient(axes, bars):
    """将每根柱的原色渐变为较浅的同色。"""
    from matplotlib.colors import LinearSegmentedColormap
    from numpy import linspace

    limits = axes.dataLim.frozen()
    gradient = linspace(0, 1, 96).reshape(-1, 1)
    for bar in bars:
        if bar.get_height() == 0:
            continue
        x, y = bar.get_xy()
        end_y = y + bar.get_height()
        red, green, blue, alpha = bar.get_facecolor()
        start = (red, green, blue, alpha)
        end = tuple(channel + (1 - channel) * 0.58 for channel in start[:3]) + (alpha,)
        image = axes.imshow(
            gradient, origin="lower", aspect="auto", cmap=LinearSegmentedColormap.from_list("bar", [start, end]),
            extent=(x, x + bar.get_width(), min(y, end_y), max(y, end_y)), zorder=bar.get_zorder() + 0.1,
        )
        image.set_clip_path(bar)
    axes.dataLim.set(limits)
    axes.autoscale_view()


def render_bar_chart(payload) -> BytesIO:
    """把柱状图数据、样式和统计标注渲染成 PNG。"""
    payload = chart_object(payload)
    points = chart_points(payload, MAX_BARS)
    style = chart_object(payload.get("style", {}))
    series = read_series(payload, len(points))
    layout = style_choice(style, "layout", ("grouped", "stacked"), "grouped") if series else "single"
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
    gradient = style_flag(style, "gradient", False)
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
        series_colors = _bar_list(style, "seriesColors", len(series), 40)
        if series_colors is not None and any(not is_color_like(value) for value in series_colors):
            raise ChartError()

        font = chart_font()
        figure, axes = _new_figure(style)
        labels, values = zip(*points)
        positions = [index * bar_spacing for index in range(len(points))]
        if bar_labels is None and bar_colors is not None:
            bar_labels = [label[:60] for label in labels]
        border = {"edgecolor": outline_color if outline else "none", "linewidth": outline_width if outline else 0}
        if series:
            _draw_series(axes, series, positions, series_colors or [f"C{i}" for i in range(len(series))],
                         layout, bar_spacing, border, show_values, value_unit)
        else:
            bars = draw_bars(axes, positions, values, color=bar_colors if bar_colors is not None else color,
                             label=bar_labels if bar_labels is not None else legend_label, **border)
            if gradient:
                _draw_gradient(axes, bars)
        error_points = [(x, y, error) for x, y, error in zip(positions, values, errors) if error is not None]
        if error_points and not series:
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
        if show_values and not series:
            draw_bar_labels(axes, bars, positions, values, errors, value_unit)
        if marks and not series:
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
