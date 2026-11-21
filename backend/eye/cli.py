import click
from flask.cli import with_appcontext
from sqlalchemy.exc import DBAPIError, SQLAlchemyError

from eye.config.database import DatabaseConfigurationError, get_database_engine


MYSQL_ERROR_MESSAGES = {
    1044: "账号没有访问所配置数据库的权限。",
    1045: "MySQL 拒绝登录。请检查账号、密码和账号允许的连接来源。",
    1049: "所配置的数据库不存在。请检查 MYSQL_DATABASE。",
    2002: "无法连接 MySQL。请检查服务状态和连接地址。",
    2003: "无法连接 MySQL。请检查服务状态、主机和端口。",
    2005: "无法解析 MySQL 主机名。请检查 MYSQL_HOST。",
}


@click.command("db-check")
@with_appcontext
def check_database() -> None:
    """执行 SELECT 1 检查 MySQL 连接。"""
    try:
        with get_database_engine().connect() as connection:
            connection.exec_driver_sql("SELECT 1").scalar_one()
    except DatabaseConfigurationError as error:
        raise click.ClickException(str(error)) from None
    except DBAPIError as error:
        code = next(iter(error.orig.args), None)
        message = MYSQL_ERROR_MESSAGES.get(code, "MySQL 连接测试失败。请检查本机配置。")
        raise click.ClickException(message) from None
    except SQLAlchemyError:
        raise click.ClickException("MySQL 连接测试失败。请检查本机配置。") from None

    click.echo("MySQL 连接成功（SELECT 1）。")
