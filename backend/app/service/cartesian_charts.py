from datetime import date, datetime
from decimal import Decimal
from math import ceil

from sqlalchemy import literal, or_, select

from app.service.chart_support import AGGREGATIONS, category_point, grouping_columns, paired_totals
from app.service.database_connection import database_engine_for_connection
from app.util.chart import (
    ChartError, chart_font, chart_number, chart_object, chart_text, draw_line, draw_scatter, figure_png,
    render_lock, style_flag, style_range,
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


def load_line_data(payload) -> dict:
    """按横轴升序读取聚合值，可选第二字段形成多条线。"""
    payload = chart_object(payload)
    mode = chart_text(payload, "aggregation", required=True)
    secondary = chart_text(payload, "secondaryValueColumn")
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
            raise ChartError(f"折线图最多支持 {MAX_SERIES} 个系列。")
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


def load_scatter_data(payload, *, require_group=True) -> dict:
    """读取两列数值与分组字段，每条记录对应一个散点。"""
    payload = chart_object(payload)
    connection_id = chart_text(payload, "connectionId", required=True)
    table_name = chart_text(payload, "table", required=True)
    x_name = chart_text(payload, "categoryColumn", required=True)
    y_name = chart_text(payload, "valueColumn", required=True)
    group_name = chart_text(payload, "groupColumn", required=require_group)
    if group_name in (x_name, y_name):
        raise ChartError("请选择独立的分组字段。")
    with database_engine_for_connection(connection_id) as engine, engine.connect() as connection:
        source, x, y = grouping_columns(connection, table_name, x_name, y_name, group_name, numeric_axis=True)
        group = source.c[group_name] if group_name else literal("数据")
        query = select(x, y, group).where(x.is_not(None), y.is_not(None), group.is_not(None))
        rows = connection.execute(query.order_by(x, y, group).limit(MAX_SCATTER_POINTS + 1)).all()
    groups = {}
    for x, y, group in rows[:MAX_SCATTER_POINTS]:
        groups.setdefault(group, []).append([chart_number(x), chart_number(y)])
    if len(groups) > MAX_SERIES:
        raise ChartError(f"散点图最多支持 {MAX_SERIES} 个分组，请更换分组字段。")
    return {
        "series": [{"label": str(group)[:120] or "空字符串", "samples": points} for group, points in groups.items()],
        "xLabel": x_name, "yLabel": y_name, "seriesName": "原始记录",
        "truncated": len(rows) > MAX_SCATTER_POINTS,
    }


def _figure(style):
    """配置折线图与散点图共用的画布和字体。"""
    from matplotlib.figure import Figure

    font = chart_font()
    figure = Figure(figsize=(9, 5), dpi=130, layout="constrained", facecolor="#ffffff")
    axes = figure.subplots()
    for method, key in ((figure.suptitle, "title"), (axes.set_xlabel, "xLabel"), (axes.set_ylabel, "yLabel")):
        method(chart_text(style, key, maximum=60), fontproperties=font, parse_math=False)
    axes.set_axisbelow(True)
    axes.grid(color="#e5edf6", linewidth=0.7)
    return figure, axes, font


def _palette(style):
    """读取前端预设色组，缺省时使用 Matplotlib 默认颜色。"""
    from matplotlib.colors import is_color_like

    colors = style.get("colors", [])
    if not isinstance(colors, list) or any(not isinstance(color, str) or not is_color_like(color) for color in colors):
        raise ChartError()
    return colors or [f"C{index}" for index in range(MAX_SERIES)]


def _number(value):
    """校验来自 JSON 的真实数值。"""
    if type(value) not in (int, float):
        raise ChartError()
    return chart_number(value)


def _legend(axes, style, font):
    """显示系列图例，并按纯文本处理分类名。"""
    handles, names = axes.get_legend_handles_labels()
    if handles and style_flag(style, "showLegend", True):
        legend = axes.legend(handles, names, prop=font, frameon=False)
        for label in legend.get_texts():
            label.set_parse_math(False)


def render_line_chart(payload):
    """保持数值、日期间距，并在缺失组合处断开折线。"""
    payload = chart_object(payload)
    style = chart_object(payload.get("style", {}))
    points = payload.get("points")
    series = payload.get("series", [])
    if not isinstance(points, list) or not 1 <= len(points) <= MAX_LINE_POINTS or not isinstance(series, list) or len(series) > MAX_SERIES:
        raise ChartError()
    positions, labels, values = [], [], []
    for index, raw in enumerate(points):
        point = chart_object(raw)
        positions.append(_number(point.get("x", index)))
        labels.append(chart_text(point, "label"))
        values.append(_number(point.get("value")))
    lines = [(chart_text(style, "legendLabel"), values)]
    if series:
        lines = []
        for raw in series:
            item = chart_object(raw)
            group_values = item.get("values")
            if not isinstance(group_values, list) or len(group_values) != len(points):
                raise ChartError()
            lines.append((chart_text(item, "label"), [_number(value) if value is not None else float("nan") for value in group_values]))

    with render_lock:
        figure, axes, font = _figure(style)
        palette = _palette(style)
        show_markers = style_flag(style, "showMarkers", True)
        for index, (label, values) in enumerate(lines):
            draw_line(axes, positions, values, color=palette[index % len(palette)],
                      markers=show_markers or len(points) == 1, label=label[:24])
        indices = list(range(0, len(points), max(1, ceil(len(points) / 10))))
        if indices[-1] != len(points) - 1:
            indices.append(len(points) - 1)
        axes.set_xticks([positions[i] for i in indices], [labels[i][:20] for i in indices],
                        rotation=25 if len(indices) > 5 else 0, ha="right" if len(indices) > 5 else "center",
                        fontproperties=font, parse_math=False, fontsize=9)
        _legend(axes, style, font)
        return figure_png(figure)


def render_scatter_chart(payload):
    """按系列颜色绘制原始散点。"""
    payload = chart_object(payload)
    style = chart_object(payload.get("style", {}))
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
            coordinates.append((_number(pair[0]), _number(pair[1])))
        count += len(samples)
        groups.append((chart_text(item, "label"), coordinates))

    with render_lock:
        figure, axes, font = _figure(style)
        palette = _palette(style)
        size = style_range(style, "markerSize", 40, 10, 100)
        for index, (label, coordinates) in enumerate(groups):
            xs, ys = zip(*coordinates)
            draw_scatter(axes, xs, ys, color=palette[index % len(palette)], size=size, label=label[:24])
        _legend(axes, style, font)
        return figure_png(figure)
