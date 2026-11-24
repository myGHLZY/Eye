from sqlalchemy import inspect, text
from sqlalchemy.exc import NoSuchTableError

from app.service.database_connection import database_engine_for_connection


def reflect_source(inspector, name):
    """读取当前库中数据表或视图的字段。"""
    if not inspector.has_table(name):
        raise NoSuchTableError(name)
    columns = inspector.get_columns(name)
    if inspector.dialect.name == "mysql" and any("%%" in column["name"] for column in columns):
        # MySQL 视图反射可能转义列名中的百分号，以实际列名为准。
        actual = inspector.bind.execute(text("""
            SELECT COLUMN_NAME FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :name
            ORDER BY ORDINAL_POSITION
        """), {"name": name}).scalars().all()
        if len(actual) == len(columns):
            return [{**column, "name": name} for column, name in zip(columns, actual)]
    return columns


def describe_columns(columns):
    """将数据库字段转换为选择器需要的格式。"""
    return [{"name": column["name"], "type": str(column["type"])} for column in columns]


def list_chart_sources(connection_id):
    """列出可供图表和视图工作台使用的数据源。"""
    with database_engine_for_connection(connection_id) as engine, engine.connect() as connection:
        inspector = inspect(connection)
        return {"tables": sorted(inspector.get_table_names()), "views": sorted(inspector.get_view_names())}


def describe_chart_source(connection_id, name):
    """返回数据表或视图的字段清单。"""
    with database_engine_for_connection(connection_id) as engine, engine.connect() as connection:
        return {"columns": describe_columns(reflect_source(inspect(connection), name))}
