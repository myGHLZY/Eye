from threading import Lock

from flask import Flask
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError, SQLAlchemyError

from app.config.settings import save_database_settings
from app.database.database import create_database_engine

_settings_lock = Lock()
_mysql_errors = {
    1044: "当前用户无权访问此数据库。请检查数据库权限。",
    1045: "MySQL 拒绝登录。请检查用户名、密码和登录权限。",
    1049: "数据库不存在。请检查数据库名。",
    2005: "无法解析 MySQL 主机名。请检查主机地址。",
}


class DatabaseConnectionError(RuntimeError):
    """提供给连接页面的错误信息。"""


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
            save_database_settings(settings)
            previous_engine = app.extensions["eye_database"]
            app.config.update(settings)
            app.extensions["eye_database"] = engine
    except OSError:
        engine.dispose()
        raise

    if isinstance(previous_engine, Engine):
        previous_engine.dispose()


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
