from contextlib import contextmanager
from threading import Lock

from flask import Flask, current_app
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError, SQLAlchemyError

from app.config.settings import (
    DATABASE_SETTING_KEYS,
    DEFAULT_MYSQL_SETTINGS,
    database_connection_id,
    load_database_connections,
    save_database_settings,
    write_database_connections,
)
from app.database.database import create_database_engine, get_database_engine

_settings_lock = Lock()
_mysql_errors = {
    1044: "当前用户无权访问此数据库。请检查数据库权限。",
    1045: "MySQL 拒绝登录。请检查用户名、密码和登录权限。",
    1049: "数据库不存在。请检查数据库名。",
    2005: "无法解析 MySQL 主机名。请检查主机地址。",
}


class DatabaseConnectionError(RuntimeError):
    """提供给连接页面的错误信息。"""


class DatabaseConnectionNotFoundError(LookupError):
    """指定的数据库连接不存在。"""


def list_database_connections(app: Flask) -> dict:
    with _settings_lock:
        connections, _ = _available_connections(app)
    entries = [
        {
            "id": connection_id,
            "database": settings["MYSQL_DATABASE"],
            "host": settings["MYSQL_HOST"],
            "port": int(settings["MYSQL_PORT"]),
            "username": settings["MYSQL_USER"],
        }
        for connection_id, settings in connections.items()
    ]
    entries.sort(key=lambda entry: (entry["database"].casefold(), entry["host"], entry["port"], entry["username"]))
    return {"connections": entries}


@contextmanager
def database_engine_for_connection(connection_id: str | None):
    if connection_id is None:
        yield get_database_engine()
        return

    with _settings_lock:
        connections, active_id = _available_connections(current_app)
        settings = connections.get(connection_id)
        engine = get_database_engine() if connection_id == active_id else None

    if settings is None:
        raise DatabaseConnectionNotFoundError(connection_id)
    if engine is not None:
        yield engine
        return

    engine = create_database_engine(settings)
    try:
        yield engine
    finally:
        engine.dispose()


def _available_connections(app: Flask):
    connections = load_database_connections()
    active_id = None
    active = _current_connection(app)
    if active is not None:
        active_id = database_connection_id(active)
        connections[active_id] = active
    return connections, active_id


def _current_connection(app: Flask) -> dict[str, str] | None:
    if isinstance(app.extensions["eye_database"], Engine):
        return {key: app.config[key] for key in DATABASE_SETTING_KEYS}
    return None


def get_connection_settings(app: Flask) -> dict[str, str | int | None]:
    with _settings_lock:
        config = app.config
        port = config["MYSQL_PORT"].strip()
        return {
            "host": config["MYSQL_HOST"],
            "port": int(port) if port.isascii() and port.isdecimal() and len(port) <= 5 else None,
            "database": config["MYSQL_DATABASE"],
            "username": config["MYSQL_USER"],
        }


def test_connection(settings: dict[str, str]) -> None:
    engine = _connect(settings)
    engine.dispose()


def apply_connection(app: Flask, settings: dict[str, str]) -> None:
    engine = _connect(settings)
    try:
        with _settings_lock:
            previous_engine = app.extensions["eye_database"]
            save_database_settings(settings, _current_connection(app))
            app.config.update(settings)
            app.extensions["eye_database"] = engine
    except OSError:
        engine.dispose()
        raise

    if isinstance(previous_engine, Engine):
        previous_engine.dispose()


def disconnect_database_connection(app: Flask, connection_id: str) -> None:
    disconnected_engine = None
    with _settings_lock:
        connections, active_id = _available_connections(app)
        if connection_id not in connections:
            return

        del connections[connection_id]
        write_database_connections(connections.get(active_id), connections)
        if connection_id == active_id:
            disconnected_engine = app.extensions["eye_database"]
            app.config.update(DEFAULT_MYSQL_SETTINGS)
            app.extensions["eye_database"] = "当前没有默认的 MySQL 连接。"

    if disconnected_engine is not None:
        disconnected_engine.dispose()


def _connect(settings: dict[str, str]) -> Engine:
    engine = create_database_engine(settings)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except (SQLAlchemyError, UnicodeError) as error:
        engine.dispose()
        code = error.orig.args[0] if isinstance(error, DBAPIError) and error.orig.args else None
        raise DatabaseConnectionError(
            _mysql_errors.get(code, "无法连接 MySQL。请检查主机、端口和数据库服务。")
        ) from None
    return engine
