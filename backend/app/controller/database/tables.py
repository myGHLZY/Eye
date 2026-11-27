from flask import request
from werkzeug.exceptions import RequestEntityTooLarge

from app.service.database_catalog import describe_chart_source, list_chart_sources
from app.service.table_rows import list_table_rows, mutate_table_rows
from app.service.table_schema import get_schema_diagram, get_table_schema, list_tables
from app.util.response import error_response as _error

from .common import _database_response, _read_json, blueprint


@blueprint.get("/tables")
def tables():
    return _database_response(list_tables, request.args.get("connectionId"))


@blueprint.get("/sources")
def chart_sources():
    """列出可用于图表和视图工作台的数据源。"""
    return _database_response(list_chart_sources, request.args.get("connectionId"))


@blueprint.get("/sources/detail")
def chart_source_detail():
    """读取数据表或视图的字段名称与类型。"""
    return _database_response(describe_chart_source, request.args.get("connectionId"), request.args.get("name", ""))


@blueprint.get("/schema/diagram")
def schema_diagram():
    return _database_response(get_schema_diagram, request.args.get("connectionId"))


@blueprint.get("/tables/detail")
def table_detail():
    name = request.args.get("name", "")
    if not name.strip():
        return _error(400, "TABLE_NAME_REQUIRED", "请指定要查看的表。")
    return _database_response(get_table_schema, name, request.args.get("connectionId"))


@blueprint.route("/tables/rows", methods=["GET", "POST", "PATCH", "DELETE"])
def table_rows():
    name = request.args.get("name", "")
    connection_id = request.args.get("connectionId")
    if not name:
        return _error(400, "TABLE_NAME_REQUIRED", "请指定要操作的表。")
    if request.method in {"GET", "HEAD"}:
        return _database_response(list_table_rows, name, connection_id, request.args, row_request=True)
    if not connection_id:
        return _error(400, "DATABASE_CONNECTION_REQUIRED", "请指定要写入的数据库连接。")
    try:
        payload = _read_json(1024 * 1024)
    except RequestEntityTooLarge:
        return _error(413, "TABLE_ROW_PAYLOAD_TOO_LARGE", "记录请求体不能超过 1 MiB。")
    return _database_response(
        mutate_table_rows, name, connection_id, request.method, payload,
        row_request=True, status=201 if request.method == "POST" else 200,
    )
