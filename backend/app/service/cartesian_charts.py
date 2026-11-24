from datetime import date, datetime
from decimal import Decimal
from math import isnan

from sqlalchemy import literal, or_, select

from app.service.chart_support import AGGREGATIONS, category_point, grouping_columns, original_rows, paired_totals
from app.service.database_connection import database_engine_for_connection
from app.service.distribution_charts import histogram_bins, histogram_edges
from app.service.scatter_style import draw_scatter_guides, draw_scatter_series, scatter_style
from app.util.chart import (
    ChartError, chart_figure, chart_legend, chart_number, chart_object, chart_palette, chart_text,
    draw_line, figure_png, json_chart_number, render_lock, set_chart_ticks, style_cartesian_axes,
    style_choice, style_flag,
)

MAX_LINE_POINTS = 96
MAX_SCATTER_POINTS = 500
MAX_SERIES = 8
LINE_AGGREGATIONS = tuple(code for code in AGGREGATIONS if code != "share")


def _line_x(value, index):
    """将数字或日期转换成真实横轴坐标，文本类别按等距排列。"""
    if isinstance(value, datetime):
        return value.toordinal() + (value.hour * 3600 + value.minute * 60 + value.second + value.microsecond / 1e6) / 86400
    if isinstance(value, date):
        return value.toordinal()
    if type(value) in (int, float, Decimal):
        return chart_number(value)
    return index


def _axis_type(value):
    """区分可按实际间距对齐的横轴类型。"""
    if isinstance(value, date):
        return "date"
    return "number" if type(value) in (int, float, Decimal) else "category"


def load_line_data(payload, *, chart_name="折线图") -> dict:
    """按横轴升序读取聚合值，可选第二字段形成多条线。"""
    payload = chart_object(payload)
    mode = chart_text(payload, "aggregation", required=True)
    secondary = chart_text(payload, "secondaryValueColumn")
    if mode == "raw":
        return _load_original_line(payload, secondary)
    if mode not in LINE_AGGREGATIONS:
        raise ChartError("所选聚合方式无效。")
    if payload.get("groupColumn"):
        if secondary:
            raise ChartError()
        rows, truncated, name = paired_totals(
            payload, MAX_LINE_POINTS * MAX_SERIES, allowed=LINE_AGGREGATIONS, by_category=True,
        )
        categories = list(dict.fromkeys(category for category, _, _ in rows))
        truncated = truncated or len(categories) > MAX_LINE_POINTS
        categories = categories[:MAX_LINE_POINTS]
        visible = set(categories)
        entries = {(category, group): chart_number(value) for category, group, value in rows if category in visible}
        groups = list(dict.fromkeys(group for _, group in entries))
        if len(groups) > MAX_SERIES:
            raise ChartError(f"{chart_name}最多支持 {MAX_SERIES} 个系列。")
        series = [
            {"label": str(group)[:120] or "空字符串", "values": [entries.get((category, group)) for category in categories]}
            for group in groups
        ]
        points = [
            {**category_point(category, 0), "x": _line_x(category, index)}
            for index, category in enumerate(categories)
        ]
        return {
            "points": points, "series": series, "seriesName": name, "truncated": truncated,
            "xType": _axis_type(categories[0]) if categories else None,
        }

    connection_id = chart_text(payload, "connectionId", required=True)
    table_name = chart_text(payload, "table", required=True)
    category_name = chart_text(payload, "categoryColumn", required=True)
    metric_name = chart_text(payload, "valueColumn", required=True) if mode != "count" else ""
    if secondary and not metric_name:
        raise ChartError()
    label, aggregate = AGGREGATIONS[mode]
    with database_engine_for_connection(connection_id) as engine, engine.connect() as connection:
        source, category, metric = grouping_columns(connection, table_name, category_name, metric_name, secondary,
                                                    numeric_group=bool(secondary))
        value = aggregate(metric) if metric is not None else aggregate()
        extra = source.c[secondary] if secondary else None
        if extra is not None:
            query = select(category, value, aggregate(extra)).where(
                category.is_not(None), or_(metric.is_not(None), extra.is_not(None)),
            )
        else:
            query = select(category, value).where(category.is_not(None))
        if metric is not None and extra is None:
            query = query.where(metric.is_not(None))
        rows = connection.execute(query.group_by(category).order_by(category).limit(MAX_LINE_POINTS + 1)).all()
    points = []
    for index, (category, value, *additional) in enumerate(rows[:MAX_LINE_POINTS]):
        point = category_point(category, 0 if value is None else value)
        point["x"] = _line_x(category, index)
        if additional:
            point["value"] = point["value"] if value is not None else None
            point["secondary"] = chart_number(additional[0]) if additional[0] is not None else None
        points.append(point)
    result = {
        "points": points, "series": [], "seriesName": f"{metric_name}（{label}）" if metric_name else label,
        "truncated": len(rows) > MAX_LINE_POINTS,
        "xType": _axis_type(rows[0][0]) if rows else None,
    }
    if secondary:
        result["secondaryName"] = f"{secondary}（{label}）"
    return result


def _load_original_line(payload, secondary):
    """保留重复横轴下的明细，并使不同系列各自按实际记录连线。"""
    grouped = bool(payload.get("groupColumn"))
    rows, truncated, name = original_rows(payload, MAX_LINE_POINTS, grouped=grouped, secondary=secondary)
    groups = list(dict.fromkeys(row[1] for row in rows)) if grouped else []
    if len(groups) > MAX_SERIES:
        raise ChartError(f"折线图最多支持 {MAX_SERIES} 个系列。")
    categories, points = {}, []
    for row in rows:
        category = row[0]
        value = row[-1] if grouped else row[1]
        ordinal = categories.setdefault(category, len(categories))
        point = {**category_point(category, 0 if value is None else value), "x": _line_x(category, ordinal)}
        if secondary:
            point["value"] = None if value is None else point["value"]
            point["secondary"] = None if row[2] is None else chart_number(row[2])
        points.append(point)
    result = {
        "points": points, "seriesName": name, "truncated": truncated, "rawRecords": True,
        "xType": _axis_type(rows[0][0]) if rows else None,
        "series": [
            {"label": str(group)[:120] or "空字符串",
             "values": [point["value"] if row[1] == group else None for row, point in zip(rows, points)]}
            for group in groups
        ],
    }
    if secondary:
        result["secondaryName"] = f"{secondary}（原始记录）"
    return result


def load_scatter_data(payload, *, numeric_x=False) -> dict:
    """每条记录绘制一个点，横轴支持数值、日期或类别，分组可选。"""
    payload = chart_object(payload)
    connection_id = chart_text(payload, "connectionId", required=True)
    table_name = chart_text(payload, "table", required=True)
    x_name = chart_text(payload, "categoryColumn", required=True)
    y_name = chart_text(payload, "valueColumn", required=True)
    group_name = chart_text(payload, "groupColumn")
    raw_limit = payload.get("maxPoints", MAX_SCATTER_POINTS)
    if type(raw_limit) is not int or not 1 <= raw_limit <= MAX_SCATTER_POINTS:
        raise ChartError(f"散点图最多支持 {MAX_SCATTER_POINTS} 个点。")
    if group_name in (x_name, y_name):
        raise ChartError("请选择独立的分组字段。")
    with database_engine_for_connection(connection_id) as engine, engine.connect() as connection:
        source, x, y = grouping_columns(connection, table_name, x_name, y_name, group_name, numeric_axis=numeric_x)
        group = source.c[group_name] if group_name else literal("数据")
        query = select(x, y, group).where(x.is_not(None), y.is_not(None), group.is_not(None))
        rows = connection.execute(query.order_by(x, y, group).limit(raw_limit + 1)).all()
    x_type = _axis_type(rows[0][0]) if rows else None
    positions = {}
    groups = {}
    for x, y, group in rows[:raw_limit]:
        if x_type == "number":
            position = chart_number(x)
        else:
            if x not in positions:
                positions[x] = {**category_point(x, 0), "x": _line_x(x, len(positions))}
            position = positions[x]["x"]
        groups.setdefault(group, []).append([position, chart_number(y)])
    if len(groups) > MAX_SERIES:
        raise ChartError(f"散点图最多支持 {MAX_SERIES} 个分组，请更换分组字段。")
    return {
        "series": [{"label": str(group)[:120] or "空字符串", "samples": points} for group, points in groups.items()],
        "xLabel": x_name, "yLabel": y_name, "seriesName": "原始记录",
        "points": list(positions.values()), "xType": x_type, "truncated": len(rows) > raw_limit,
    }


def load_scatter_histogram_data(payload):
    return load_scatter_data(payload, numeric_x=True)


def load_stacked_area_data(payload):
    payload = chart_object(payload)
    if payload.get("aggregation") not in LINE_AGGREGATIONS or payload.get("secondaryValueColumn"):
        raise ChartError("请选择支持的横轴聚合方式和系列字段。")
    return load_line_data(payload, chart_name="堆叠面积图")


def _figure(style):
    figure, font = chart_figure(style)
    axes = figure.subplots()
    style_cartesian_axes(axes, style, font)
    return figure, axes, font


def _cartesian_series(payload, style, missing):
    points = payload.get("points")
    series = payload.get("series", [])
    if not isinstance(points, list) or not 1 <= len(points) <= MAX_LINE_POINTS or not isinstance(series, list) or len(series) > MAX_SERIES:
        raise ChartError()
    positions, labels = [], []
    values = []
    for index, raw in enumerate(points):
        point = chart_object(raw)
        positions.append(json_chart_number(point.get("x", index)))
        labels.append(chart_text(point, "label"))
        value = point.get("value")
        values.append(json_chart_number(value) if value is not None else missing)
    lines = [(chart_text(style, "legendLabel"), values)]
    if series:
        lines = []
        for raw in series:
            item = chart_object(raw)
            group_values = item.get("values")
            if not isinstance(group_values, list) or len(group_values) != len(points):
                raise ChartError()
            values = [json_chart_number(value) if value is not None else missing for value in group_values]
            lines.append((chart_text(item, "label"), values))
    return positions, labels, lines


def render_line_chart(payload):
    """保持数值、日期间距，并在缺失组合处断开折线。"""
    payload = chart_object(payload)
    style = chart_object(payload.get("style", {}))
    positions, labels, lines = _cartesian_series(payload, style, float("nan"))

    with render_lock:
        figure, axes, font = _figure(style)
        palette = chart_palette(style)
        show_markers = style_flag(style, "showMarkers", True)
        for index, (label, values) in enumerate(lines):
            plotted = list(zip(positions, values))
            if payload.get("series") and payload.get("rawRecords"):
                plotted = [(x, y) for x, y in plotted if not isnan(y)]
            if plotted:
                xs, ys = zip(*plotted)
                draw_line(axes, xs, ys, color=palette[index % len(palette)],
                          markers=show_markers or len(xs) == 1, label=label[:24])
        set_chart_ticks(axes, list(zip(positions, labels)), font, 25 if len(positions) > 5 else 0,
                        max_labels=10, label_length=20, fontsize=9)
        chart_legend(axes, style, font)
        return figure_png(figure)


def render_stacked_area_chart(payload):
    payload = chart_object(payload)
    style = chart_object(payload.get("style", {}))
    positions, labels, series = _cartesian_series(payload, style, 0)
    if len(positions) < 2 or any(left >= right for left, right in zip(positions, positions[1:])):
        raise ChartError("堆叠面积图需要至少两个按升序排列且互不重复的横轴值。")
    names, values = zip(*series)
    if any(value < 0 for row in values for value in row):
        raise ChartError("堆叠面积图需要非负的聚合值。")

    with render_lock:
        figure, axes, font = _figure(style)
        axes.stackplot(positions, *values, labels=[name[:24] for name in names],
                       colors=chart_palette(style), alpha=0.8)
        axes.set_ylim(bottom=0)
        axes.margins(x=0)
        set_chart_ticks(axes, list(zip(positions, labels)), font, max_labels=10, label_length=20, fontsize=9)
        chart_legend(axes, style, font)
        return figure_png(figure)


def render_scatter_chart(payload, *, marginal=False):
    """按系列颜色绘制原始散点。"""
    payload = chart_object(payload)
    style = chart_object(payload.get("style", {}))
    appearance = scatter_style(style)
    x_type = style_choice(payload, "xType", ("number", "category", "date"), "number")
    if marginal and x_type != "number":
        raise ChartError("带边际直方图的散点图需要两个数值字段。")
    series = payload.get("series")
    if not isinstance(series, list) or not 1 <= len(series) <= MAX_SERIES:
        raise ChartError()

    groups = []
    count = 0
    for raw in series:
        item = chart_object(raw)
        samples = item.get("samples")
        if not isinstance(samples, list) or not samples or count + len(samples) > MAX_SCATTER_POINTS:
            raise ChartError()
        coordinates = []
        for pair in samples:
            if not isinstance(pair, list) or len(pair) != 2:
                raise ChartError()
            coordinates.append((json_chart_number(pair[0]), json_chart_number(pair[1])))
        count += len(samples)
        groups.append({"label": chart_text(item, "label"), "samples": coordinates})
    ticks = []
    if x_type != "number":
        points = payload.get("points")
        if not isinstance(points, list) or not 1 <= len(points) <= MAX_SCATTER_POINTS:
            raise ChartError()
        for raw in points:
            point = chart_object(raw)
            ticks.append((json_chart_number(point.get("x")), chart_text(point, "label")))

    with render_lock:
        figure, font = chart_figure(style, figsize=(9, 7) if marginal else (9, 5))
        palette = chart_palette(style)
        axes = _marginal_axes(figure, groups, palette, histogram_bins(style)) if marginal else figure.subplots()
        style_cartesian_axes(axes, style, font)
        for index, group in enumerate(groups):
            draw_scatter_series(axes, group["samples"], appearance, palette[index % len(palette)], group["label"][:24])
        draw_scatter_guides(axes, groups, appearance, x_type, font)
        set_chart_ticks(axes, ticks, font, max_labels=10, label_length=20, fontsize=9)
        chart_legend(axes, style, font)
        return figure_png(figure)


def _marginal_axes(figure, groups, palette, bins):
    from matplotlib.ticker import MaxNLocator

    grid = figure.add_gridspec(2, 2, width_ratios=(4, 1), height_ratios=(1, 4))
    scatter = figure.add_subplot(grid[1, 0])
    top = figure.add_subplot(grid[0, 0], sharex=scatter)
    right = figure.add_subplot(grid[1, 1], sharey=scatter)
    top.tick_params(axis="x", labelbottom=False)
    right.tick_params(axis="y", labelleft=False)
    top.yaxis.set_major_locator(MaxNLocator(nbins=3, integer=True))
    right.xaxis.set_major_locator(MaxNLocator(nbins=3, integer=True))

    colors = [palette[index % len(palette)] for index in range(len(groups))]
    coordinates = [tuple(zip(*group["samples"])) for group in groups]
    x_groups, y_groups = zip(*coordinates)
    for axes, samples, orientation in ((top, x_groups, "vertical"), (right, y_groups, "horizontal")):
        edges = histogram_edges([value for sample in samples for value in sample], bins)
        axes.hist(samples, bins=edges, orientation=orientation, stacked=True, color=colors, alpha=0.75)
    return scatter


def render_scatter_histogram_chart(payload):
    return render_scatter_chart(payload, marginal=True)
