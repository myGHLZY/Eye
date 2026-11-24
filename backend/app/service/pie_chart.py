from io import BytesIO

from sqlalchemy import func, select, true

from app.service.chart_support import AGGREGATIONS, category_point, grouping_columns, original_point, original_rows
from app.service.database_connection import database_engine_for_connection

from app.util.chart import (
    DPI_OPTIONS, HEX_COLOR, ChartError, chart_font, chart_number, chart_object, chart_points,
    chart_text, figure_png, render_lock, style_choice, style_color, style_flag, style_range,
)

MAX_SLICES = 12
PIE_COLORS = ("#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#17becf")
LEGEND_LOCATIONS = {"right": "outside right upper", "bottom": "outside lower center"}


def load_pie_data(payload) -> dict:
    """按分类读取可组成饼图的总量，必要时合并长尾分类。"""
    payload = chart_object(payload)
    aggregation = payload.get("aggregation")
    if aggregation == "raw":
        rows, truncated, name = original_rows(payload, MAX_SLICES)
        if any(value < 0 for _, value in rows):
            raise ChartError("饼图需要非负数值，请换一个数值字段或按记录数统计。")
        points = [original_point(category, value, index) for index, (category, value) in enumerate(rows) if value > 0]
        for point in points:
            point["label"] = point["label"] or "空字符串"
        return {
            "points": points, "seriesName": name, "total": sum(point["value"] for point in points),
            "combined": False, "truncated": truncated,
        }
    if aggregation not in ("count", "sum", "average", "max", "min"):
        raise ChartError("所选聚合方式无效。")
    connection_id = chart_text(payload, "connectionId", required=True)
    table_name = chart_text(payload, "table", required=True)
    category_name = chart_text(payload, "categoryColumn", required=True)
    metric_name = chart_text(payload, "valueColumn", required=True) if aggregation != "count" else ""
    label, function = AGGREGATIONS[aggregation]
    with database_engine_for_connection(connection_id) as engine, engine.connect() as connection:
        _, category, metric = grouping_columns(connection, table_name, category_name, metric_name)
        conditions = [category.is_not(None)]
        if metric is not None:
            conditions.append(metric.is_not(None))
        value = function(metric) if metric is not None else function()
        groups = select(category.label("category"), value.label("amount")).where(*conditions).group_by(category).subquery()
        minimum = func.min(groups.c.amount)
        if aggregation == "sum":
            minimum = select(func.min(metric)).where(*conditions).scalar_subquery()
        summary = select(func.sum(groups.c.amount).label("total"), minimum.label("minimum")).subquery()
        statement = (
            select(groups.c.category, groups.c.amount, summary.c.total, summary.c.minimum)
            .select_from(groups.join(summary, true()))
            .order_by(groups.c.amount.desc(), groups.c.category.asc())
            .limit(MAX_SLICES + 1)
        )
        rows = connection.execute(statement).all()

    label = f"{metric_name}（{label}）" if metric_name else label
    if not rows:
        return {"points": [], "seriesName": label, "total": 0, "combined": False}
    if rows[0][3] < 0:
        raise ChartError("饼图需要非负数值，请换一个数值字段或按记录数统计。")
    total_value = rows[0][2]
    numeric_total = chart_number(total_value)
    positive_rows = [(category, value) for category, value, _, _ in rows if value > 0]
    combined = len(positive_rows) > MAX_SLICES
    if combined:
        positive_rows = positive_rows[:MAX_SLICES - 1]

    points = []
    for category, value in positive_rows:
        point = category_point(category, value, stable_key=True)
        point["label"] = point["label"] or "空字符串"
        points.append(point)
    if combined:
        remainder = total_value - sum(value for _, value in positive_rows)
        points.append({"key": "others", "label": "其他分类", "value": float(remainder)})
    return {"points": points, "seriesName": label, "total": numeric_total, "combined": combined}


def render_pie_chart(payload) -> BytesIO:
    """按扇区大小和样式生成饼图或环形图 PNG。"""
    payload = chart_object(payload)
    points = chart_points(payload, MAX_SLICES)
    labels, values = zip(*points)
    if min(values) <= 0:
        raise ChartError("饼图扇区需要有限的正数。")
    style = chart_object(payload.get("style", {}))
    angle = style_range(style, "startAngle", 90, 0, 360)
    dpi = style_choice(style, "dpi", DPI_OPTIONS, 130)
    legend = style_choice(style, "legendPosition", ("right", "bottom", "none"), "right")
    label_mode = style_choice(style, "labelMode", ("percent", "value", "none"), "percent")
    clockwise = style_flag(style, "clockwise", True)
    donut = style_flag(style, "donut", False)
    outline = style_flag(style, "showOutline", True)
    transparent = style_flag(style, "transparentBackground", False)
    highlight = style.get("highlight")
    if highlight is not None and (type(highlight) is not int or not 0 <= highlight < len(points)):
        raise ChartError()
    colors = style.get("colors", [PIE_COLORS[index % len(PIE_COLORS)] for index in range(len(points))])
    if not isinstance(colors, list) or len(colors) != len(points) or any(
        not isinstance(color, str) or not HEX_COLOR.fullmatch(color) for color in colors
    ):
        raise ChartError()

    title = chart_text(style, "title", maximum=60)
    legend_title = chart_text(style, "legendTitle", maximum=60)
    background = style_color(style, "figureColor", "#ffffff")
    outline_color = style_color(style, "outlineColor", "#ffffff")
    largest = max(values)
    scaled = [value / largest for value in values]
    total = sum(scaled)

    with render_lock:
        from matplotlib.figure import Figure

        font = chart_font()
        figure = Figure(figsize=(9, 6), dpi=dpi, layout="constrained", facecolor="none" if transparent else background)
        axes = figure.subplots()
        wedges, _, texts = axes.pie(
            scaled, colors=colors, startangle=angle, counterclock=not clockwise,
            explode=[0.09 if index == highlight else 0 for index in range(len(points))],
            autopct="%1.1f%%", pctdistance=0.78 if donut else 0.68,
            wedgeprops={
                "width": 0.45 if donut else 1,
                "linewidth": 1 if outline else 0,
                "edgecolor": outline_color if outline else "none",
            },
            textprops={"fontsize": 10, "parse_math": False},
        )
        for wedge, artist, value, scaled_value in zip(wedges, texts, values, scaled):
            fraction = scaled_value / total
            if label_mode == "none" or fraction < 0.035:
                artist.set_visible(False)
                continue
            artist.set_text(f"{value:.4g}" if label_mode == "value" else f"{fraction:.1%}")
            red, green, blue, _ = wedge.get_facecolor()
            lightness = 0.2126 * red + 0.7152 * green + 0.0722 * blue
            artist.set_color("#14233b" if lightness > 0.58 else "#ffffff")

        if title:
            figure.suptitle(title, fontproperties=font, fontsize=15, color="#15243b", parse_math=False)
        if legend != "none":
            names = [name if len(name) <= 18 else name[:17] + "…" for name in labels]
            artist = figure.legend(wedges, names, title=legend_title, frameon=False, loc=LEGEND_LOCATIONS[legend],
                                   prop=font, title_fontproperties=font,
                                   ncols=1 if legend == "right" else min(3, len(wedges)))
            for text in [*artist.get_texts(), artist.get_title()]:
                text.set_parse_math(False)

        return figure_png(figure)
