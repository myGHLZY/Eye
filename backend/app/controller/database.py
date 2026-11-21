from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import NoSuchTableError, SQLAlchemyError

from app.database.database import DatabaseConfigurationError

from app.service.database_connection import (
    DatabaseConnectionError,
    apply_connection,
    get_connection_settings,
    test_connection,
)
from app.service.table_schema import get_schema_diagram, get_table_schema, list_tables
from app.util.response import ok

blueprint = Blueprint("database", __name__, url_prefix="/api/database")


@blueprint.before_request
def require_local_request():
    if request.remote_addr not in {"127.0.0.1", "::1", "::ffff:127.0.0.1"}:
        return _error(403, "LOCAL_ACCESS_REQUIRED", "请从运行 Eye 后端的本机访问连接设置。")


@blueprint.get("/connection")
def connection_settings():
    response = ok(get_connection_settings(current_app))
    response.headers["Cache-Control"] = "no-store"
    return response


@blueprint.get("/tables")
def tables():
    return _read_schema(list_tables)


@blueprint.get("/schema/diagram")
def schema_diagram():
    return _read_schema(get_schema_diagram)


@blueprint.get("/tables/detail")
def table_detail():
    name = request.args.get("name", "")
    if not name.strip():
        return _error(400, "TABLE_NAME_REQUIRED", "请指定要查看的表。")
    return _read_schema(get_table_schema, name)


def _read_schema(read, *args):
    try:
        response = ok(read(*args))
    except DatabaseConfigurationError:
        return _error(503, "DATABASE_NOT_CONFIGURED", "请先在「数据库连接」中保存可用的 MySQL 连接。")
    except NoSuchTableError:
        return _error(404, "TABLE_NOT_FOUND", "当前数据库中找不到这张表，请刷新表列表。")
    except SQLAlchemyError:
        return _error(503, "SCHEMA_READ_FAILED", "无法读取表结构，请检查数据库连接及账号权限。")
    response.headers["Cache-Control"] = "no-store"
    return response


@blueprint.post("/test-connection")
def test_database_connection():
    return _submit_connection(apply=False)


@blueprint.put("/connection")
def save_database_connection():
    return _submit_connection(apply=True)


def _submit_connection(*, apply: bool):
    try:
        settings = _parse_connection_settings(request.get_json(silent=True))
    except ValueError as error:
        return _error(400, "INVALID_DATABASE_SETTINGS", str(error))

    try:
        if apply:
            apply_connection(current_app, settings)
            return ok({"status": "ok", "message": "数据库连接已保存并生效。"})
        test_connection(settings)
        return ok({"status": "ok", "message": "数据库连接测试成功。"})
    except DatabaseConnectionError as error:
        return _error(503, "DATABASE_CONNECTION_FAILED", str(error))
    except OSError:
        return _error(500, "DATABASE_SETTINGS_WRITE_FAILED", "无法保存数据库设置。请检查后端目录的写入权限。")


def _parse_connection_settings(payload) -> dict[str, str]:
    if not isinstance(payload, dict):
        raise ValueError("请提交 JSON 格式的 MySQL 连接参数。")

    settings = {}
    for field, key, label in (
        ("host", "MYSQL_HOST", "主机地址"),
        ("database", "MYSQL_DATABASE", "数据库名"),
        ("username", "MYSQL_USER", "用户名"),
    ):
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip() or "\x00" in value:
            raise ValueError(f"请填写有效的{label}。")
        settings[key] = value.strip()

    port = payload.get("port")
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("端口必须是 1 到 65535 之间的整数。")
    settings["MYSQL_PORT"] = str(port)

    password = payload.get("password", "")
    if not isinstance(password, str):
        raise ValueError("密码必须是字符串。")
    settings["MYSQL_PASSWORD"] = password
    return settings


def _error(status: int, code: str, message: str):
    return jsonify(error={"code": code, "message": message}), status
