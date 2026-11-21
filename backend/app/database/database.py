from collections.abc import Mapping

from flask import Flask, current_app
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, URL


class DatabaseConfigurationError(ValueError):
    """MySQL 连接配置缺失或无效。"""


def init_database(app: Flask) -> None:
    try:
        app.extensions["eye_database"] = create_database_engine(app.config)
    except DatabaseConfigurationError as error:
        app.extensions["eye_database"] = str(error)


def create_database_engine(settings: Mapping[str, str]) -> Engine:
    return create_engine(
        _database_url(settings),
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args={"connect_timeout": 5, "read_timeout": 10, "write_timeout": 10},
    )


def get_database_engine() -> Engine:
    database = current_app.extensions["eye_database"]
    if isinstance(database, str):
        raise DatabaseConfigurationError(database)
    return database


def _database_url(config: Mapping[str, str]) -> URL:
    required_fields = ("MYSQL_HOST", "MYSQL_DATABASE", "MYSQL_USER")
    missing_fields = [field for field in required_fields if not config[field].strip()]
    if missing_fields:
        raise DatabaseConfigurationError(
            f"请在 backend/.env 中填写 {', '.join(missing_fields)}。"
        )

    try:
        port = int(config["MYSQL_PORT"])
    except ValueError:
        raise DatabaseConfigurationError("MYSQL_PORT 必须是 1 到 65535 之间的整数。") from None
    if not 1 <= port <= 65535:
        raise DatabaseConfigurationError("MYSQL_PORT 必须是 1 到 65535 之间的整数。")

    return URL.create(
        "mysql+pymysql",
        username=config["MYSQL_USER"],
        password=config["MYSQL_PASSWORD"],
        host=config["MYSQL_HOST"],
        port=port,
        database=config["MYSQL_DATABASE"],
        query={"charset": "utf8mb4"},
    )
