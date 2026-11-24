from datetime import date, time, timedelta
from decimal import Decimal
from re import match

from pymysql.constants import CLIENT
from sqlalchemy import String, cast, func, inspect, select
from sqlalchemy.exc import DBAPIError

from app.service.database_connection import database_engine_for_connection
from app.service.view_fields import ViewError, select_column, view_object, view_text
from app.service.view_query import MAX_CATEGORY_LENGTH, ViewQueryBuilder

PREVIEW_LIMIT = 20
CATEGORY_LIMIT = 80


def _configuration(payload):
    """取得已保存的连接及本次视图或草稿配置。"""
    payload = view_object(payload)
    connection_id = view_text(payload.get("connectionId"), "请先选择数据库连接。", 120)
    return connection_id, view_object(payload.get("spec")), payload.get("drafts", [])


def _raw_query(spec):
    """接受一条 SELECT 或 WITH 查询，交由 MySQL 验证视图定义。"""
    sql = spec.get("sql")
    if not isinstance(sql, str) or len(sql) > 24000 or "\x00" in sql:
        raise ViewError("请输入有效的 SELECT 查询。")
    query = sql.strip().removesuffix(";").rstrip()
    if not match(r"(?i)(SELECT|WITH)\b", query) or "/*!" in query or "/*M!" in query.upper():
        raise ViewError("请输入一条以 SELECT 或 WITH 开头的查询。")
    return query


def _format_sql(connection, sql, params):
    """使用当前 MySQL 会话的驱动转义规则。"""
    with connection.connection.driver_connection.cursor() as cursor:
        return cursor.mogrify(sql, params)


def _prepare(connection, spec, drafts):
    """返回用户查询或可视化生成的 SELECT。"""
    if spec.get("mode") == "sql":
        return _raw_query(spec), None
    statement = ViewQueryBuilder(connection, drafts).build(spec)
    compiled = statement.compile(dialect=connection.dialect)
    return _format_sql(connection, str(compiled), compiled.params), statement


def _preview_rows(connection, statement):
    """将预览限制为 20 行，并将数据库值转成可显示的 JSON。"""
    connection.exec_driver_sql("START TRANSACTION READ ONLY")
    result = connection.execute(statement.limit(PREVIEW_LIMIT + 1))
    records = result.fetchmany(PREVIEW_LIMIT + 1)
    return {
        "columns": [{"name": item.name, "type": str(item.type)} for item in statement.selected_columns],
        "rows": [[_display_value(value) for value in record] for record in records[:PREVIEW_LIMIT]],
        "truncated": len(records) > PREVIEW_LIMIT,
    }


def _display_value(value):
    """保留空值和数值精度，缩短预览中的长文本和二进制。"""
    if isinstance(value, bytes):
        return "0x" + value[:80].hex() + ("…" if len(value) > 80 else "")
    if isinstance(value, (Decimal, date, time, timedelta)):
        return str(value)
    if isinstance(value, str) and len(value) > 500:
        return value[:500] + "…"
    return value


def _view_database_error(error):
    """用简单的错误说明回应 MySQL 操作失败。"""
    code = error.orig.args[0] if error.orig.args else None
    if code == 1050:
        return ViewError("这个库中已有同名数据表或视图。", 409)
    if code in (1044, 1045, 1142, 1143, 1227, 1356):
        return ViewError("当前 MySQL 账号无权执行操作，请检查视图和来源权限。", 403)
    if code in (1054, 1060, 1064, 1146, 1222, 1267, 1349, 1350, 1351, 1352, 1353, 1584):
        return ViewError("查询无法使用，请检查 SQL、字段名称及输出列是否唯一。")
    return ViewError("MySQL 无法完成本次操作，请检查连接、来源和查询。", 503)


def preview_view(payload):
    """可视化步骤查询少量记录，SQL 编辑模式仅返回待保存的定义。"""
    connection_id, spec, drafts = _configuration(payload)
    try:
        with database_engine_for_connection(connection_id) as engine, engine.connect() as connection:
            query, statement = _prepare(connection, spec, drafts)
            if statement is None:
                return {"query": query}
            return {"query": query, **_preview_rows(connection, statement)}
    except DBAPIError as error:
        raise _view_database_error(error) from None


def create_view(payload):
    """确认后在指定库创建新视图，由数据库原子处理同名冲突。"""
    connection_id, spec, drafts = _configuration(payload)
    name = view_text(payload.get("name"), "请输入视图名称（最多 64 个字符）。").strip()
    if any(character in name for character in (".", "/", "\\")):
        raise ViewError("视图名称请使用当前库中的单个名称。")
    if payload.get("confirmed") is not True:
        raise ViewError("请先确认要保存的视图。")
    try:
        with database_engine_for_connection(connection_id) as engine, engine.begin() as connection:
            query, _ = _prepare(connection, spec, drafts)
            driver = connection.connection.driver_connection
            if driver.client_flag & CLIENT.MULTI_STATEMENTS:
                raise ViewError("此连接启用了多语句执行，无法保存视图。")
            identifier = connection.dialect.identifier_preparer.quote_identifier(name)
            quoted_name = _format_sql(connection, identifier, {})
            connection.exec_driver_sql(f"CREATE SQL SECURITY INVOKER VIEW {quoted_name} AS\n{query}",
                                       execution_options={"no_parameters": True})
            return {"name": name, "query": query}
    except DBAPIError as error:
        raise _view_database_error(error) from None


def list_pivot_categories(payload):
    """读取类别值供长表转宽表选择。"""
    payload = view_object(payload)
    connection_id = view_text(payload.get("connectionId"), "请先选择数据库连接。", 120)
    try:
        with database_engine_for_connection(connection_id) as engine, engine.connect() as connection:
            source = ViewQueryBuilder(connection, payload.get("drafts", [])).source(payload.get("source"), "category_data")
            category = cast(select_column(source, payload.get("column")), String)
            query = select(category).where(category.is_not(None), func.char_length(category) <= MAX_CATEGORY_LENGTH)
            connection.exec_driver_sql("START TRANSACTION READ ONLY")
            values = connection.execute(query.distinct().order_by(category).limit(CATEGORY_LIMIT + 1)).scalars().all()
            return {"values": values[:CATEGORY_LIMIT], "truncated": len(values) > CATEGORY_LIMIT}
    except DBAPIError as error:
        raise _view_database_error(error) from None


def preview_saved_view(connection_id, name):
    """读取已保存视图的少量数据。"""
    connection_id = view_text(connection_id, "请先选择数据库连接。", 120)
    name = view_text(name, "请选择视图。")
    try:
        with database_engine_for_connection(connection_id) as engine, engine.connect() as connection:
            inspector = inspect(connection)
            if name not in inspector.get_view_names():
                raise ViewError("找不到这个视图，请刷新列表。", 404)
            source = ViewQueryBuilder(connection, []).source(f"db:{name}", "saved_view")
            return _preview_rows(connection, select(source))
    except DBAPIError as error:
        raise _view_database_error(error) from None
