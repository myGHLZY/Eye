from hashlib import sha256

from sqlalchemy import column, inspect, table
from sqlalchemy.dialects.mysql import YEAR
from sqlalchemy.exc import NoSuchTableError
from sqlalchemy.sql import quoted_name
from sqlalchemy.types import Boolean, Date, DateTime, Float, Integer, Numeric, String, Time

from app.util.chart import ChartError, chart_number

NUMERIC_TYPES = (Integer, Numeric, Float, YEAR)
CATEGORY_TYPES = (String, Date, DateTime, Time, Boolean, *NUMERIC_TYPES)


def grouping_columns(connection, table_name, category_name, metric_name):
    """校验所选列，并生成带标识符引用的 SQLAlchemy 列。"""
    inspector = inspect(connection)
    if table_name not in inspector.get_table_names():
        raise NoSuchTableError(table_name)
    types = {item["name"]: item["type"] for item in inspector.get_columns(table_name)}
    if not isinstance(types.get(category_name), CATEGORY_TYPES):
        raise ChartError("请输入表中的有效分类字段。")
    if metric_name and not isinstance(types.get(metric_name), NUMERIC_TYPES):
        raise ChartError("所选聚合方式需要指定数值字段。")

    names = dict.fromkeys((category_name, metric_name)) if metric_name else [category_name]
    source = table(quoted_name(table_name, True), *(column(quoted_name(name, True)) for name in names))
    category = source.c[category_name]
    metric = source.c[metric_name] if metric_name else None
    return source, category, metric


def category_point(category, value, stable_key: bool = False) -> dict:
    """将数据库结果转成图表数据点，必要时生成稳定的分类键。"""
    name = str(category)
    point = {"label": name[:120], "value": chart_number(value)}
    if stable_key or len(name) > 120:
        point["key"] = sha256(name.encode("utf-8")).hexdigest()
    return point
