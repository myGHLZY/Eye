from hashlib import sha256

from sqlalchemy import column, func, inspect, select, table
from sqlalchemy.dialects.mysql import YEAR
from sqlalchemy.exc import NoSuchTableError
from sqlalchemy.sql import quoted_name
from sqlalchemy.types import Boolean, Date, DateTime, Float, Integer, Numeric, String, Time

from app.service.database_connection import database_engine_for_connection
from app.util.chart import ChartError, chart_number, chart_object, chart_text

NUMERIC_TYPES = (Integer, Numeric, Float, YEAR)
CATEGORY_TYPES = (String, Date, DateTime, Time, Boolean, *NUMERIC_TYPES)
AGGREGATIONS = {
    "sum": ("合计", func.sum),
    "average": ("平均值", func.avg),
    "count": ("记录数", func.count),
    "max": ("最大值", func.max),
    "min": ("最小值", func.min),
    "share": ("占比", func.sum),
}


def grouping_columns(connection, table_name, category_name, metric_name, group_name="", *,
                     numeric_axis=False, numeric_group=False, extra_metrics=()):
    """校验所选列，并生成带标识符引用的 SQLAlchemy 列。"""
    inspector = inspect(connection)
    if table_name not in inspector.get_table_names():
        raise NoSuchTableError(table_name)
    types = {item["name"]: item["type"] for item in inspector.get_columns(table_name)}
    axis_types = NUMERIC_TYPES if numeric_axis else CATEGORY_TYPES
    group_types = NUMERIC_TYPES if numeric_group else CATEGORY_TYPES
    if not isinstance(types.get(category_name), axis_types) or (
        group_name and not isinstance(types.get(group_name), group_types)
    ):
        raise ChartError("请输入表中的有效分类字段。")
    metrics = (metric_name, *extra_metrics) if metric_name else extra_metrics
    if any(not isinstance(types.get(name), NUMERIC_TYPES) for name in metrics):
        raise ChartError("所选聚合方式需要指定数值字段。")

    names = dict.fromkeys(name for name in (category_name, metric_name, group_name, *extra_metrics) if name)
    source = table(quoted_name(table_name, True), *(column(quoted_name(name, True)) for name in names))
    category = source.c[category_name]
    metric = source.c[metric_name] if metric_name else None
    return source, category, metric


def paired_totals(payload, limit, *, allowed=("count", "sum"), by_category=False):
    """按两列分组，以数值大小排序读取有限数量的组合。"""
    payload = chart_object(payload)
    aggregation = chart_text(payload, "aggregation", required=True)
    if aggregation not in allowed:
        raise ChartError("所选聚合方式无效。")
    connection_id = chart_text(payload, "connectionId", required=True)
    table_name = chart_text(payload, "table", required=True)
    category_name = chart_text(payload, "categoryColumn", required=True)
    group_name = chart_text(payload, "groupColumn", required=True)
    if category_name == group_name:
        raise ChartError("请选择两个不同的分类字段。")
    metric_name = chart_text(payload, "valueColumn", required=True) if aggregation != "count" else ""
    label, function = AGGREGATIONS[aggregation]
    with database_engine_for_connection(connection_id) as engine, engine.connect() as connection:
        source, category, metric = grouping_columns(connection, table_name, category_name, metric_name, group_name)
        group = source.c[group_name]
        conditions = [category.is_not(None), group.is_not(None)]
        if metric is not None:
            conditions.append(metric.is_not(None))
        value = function(metric) if metric is not None else function()
        if aggregation == "share":
            total = select(func.sum(metric)).where(*conditions).correlate(None).scalar_subquery()
            value = value / (func.nullif(total, 0) * 1.0) * 100
        order = (category, group) if by_category else (func.abs(value).desc(), category, group)
        statement = select(category, group, value).where(*conditions)
        rows = connection.execute(statement.group_by(category, group)
                                  .order_by(*order).limit(limit + 1)).all()
    if rows and aggregation == "share" and rows[0][2] is None:
        raise ChartError("数值字段的总和为 0，无法计算占比。")
    return rows[:limit], len(rows) > limit, f"{metric_name}（{label}）" if metric_name else label


def category_point(category, value, stable_key: bool = False) -> dict:
    """将数据库结果转成图表数据点，必要时生成稳定的分类键。"""
    name = str(category)
    point = {"label": name[:120], "value": chart_number(value)}
    if stable_key or len(name) > 120:
        point["key"] = sha256(name.encode("utf-8")).hexdigest()
    return point
