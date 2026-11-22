from math import sqrt

from sqlalchemy import func, select

from app.service.bar_chart_render import BAR_RENDERER_REVISION, MAX_BARS, render_bar_chart
from app.service.chart_support import category_point, grouping_columns
from app.service.database_connection import database_engine_for_connection
from app.util.chart import ChartError, chart_number, chart_object, chart_text

BarChartError = ChartError

__all__ = ["BAR_RENDERER_REVISION", "BarChartError", "load_bar_data", "render_bar_chart"]

AGGREGATIONS = {
    "count": ("记录数", func.count),
    "sum": ("合计", func.sum),
    "average": ("平均值", func.avg),
    "max": ("最大值", func.max),
    "min": ("最小值", func.min),
    "share": ("占比", func.sum),
}


def load_bar_data(payload) -> dict:
    """按所选分类聚合 MySQL 数据并返回柱状图数据点。"""
    payload = chart_object(payload)
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
