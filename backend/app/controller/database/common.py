from flask import Blueprint, abort, current_app, request
from sqlalchemy.exc import DBAPIError, NoSuchTableError, SQLAlchemyError

from app.database.database import DatabaseConfigurationError
from app.service.database_connection import DatabaseConnectionNotFoundError
from app.service.table_rows import TableRowsError
from app.service.view_fields import ViewError
from app.util.chart import ChartError
from app.util.response import error_response as _error
from app.util.response import ok


blueprint = Blueprint("database", __name__, url_prefix="/api/database")


@blueprint.before_request
def require_local_request():
    if request.remote_addr not in {"127.0.0.1", "::1", "::ffff:127.0.0.1"}:
        return _error(403, "LOCAL_ACCESS_REQUIRED", "请从运行 Eye 后端的本机访问连接设置。")


def _read_json(maximum: int):
    if not request.is_json:
        return None
    body = request.stream.read(maximum + 1)
    if len(body) > maximum:
        abort(413)
    try:
        return current_app.json.loads(body)
    except ValueError:
        return None


def _database_response(read, *args, row_request=False, status=200, chart_error="INVALID_BAR_CHART"):
    try:
        response = ok(read(*args))
    except ChartError as error:
        return _error(400, chart_error, str(error))
    except ViewError as error:
        return _error(error.status, "DATABASE_VIEW_FAILED", str(error))
    except TableRowsError as error:
        return _error(error.status, error.code, str(error))
    except DatabaseConfigurationError:
        return _error(503, "DATABASE_NOT_CONFIGURED", "请先在「数据库连接」中保存可用的 MySQL 连接。")
    except DatabaseConnectionNotFoundError:
        return _error(404, "DATABASE_CONNECTION_NOT_FOUND", "找不到这条数据库连接。")
    except NoSuchTableError:
        return _error(404, "TABLE_NOT_FOUND", "当前数据库中找不到此数据源，请刷新列表。")
    except SQLAlchemyError as error:
        if row_request:
            return _table_rows_database_error(error)
        return _error(503, "SCHEMA_READ_FAILED", "无法读取表结构，请检查数据库连接及账号权限。")
    except OSError:
        return _error(500, "DATABASE_CONNECTIONS_READ_FAILED", "无法读取本地数据库连接记录。")
    response.headers["Cache-Control"] = "no-store"
    response.status_code = status
    return response


def _table_rows_database_error(error):
    code = error.orig.args[0] if isinstance(error, DBAPIError) and error.orig.args else None
    if code in {1044, 1045, 1142, 1143}:
        return _error(403, "TABLE_ROWS_ACCESS_DENIED", "当前 MySQL 账号没有执行该操作的权限。")
    if code == 1146:
        return _error(404, "TABLE_NOT_FOUND", "当前数据库中找不到这张表，请刷新表列表。")
    if code == 1062:
        return _error(409, "TABLE_ROW_DUPLICATE", "主键或唯一字段的值已存在。")
    if code in {1451, 1452}:
        return _error(409, "TABLE_ROW_FOREIGN_KEY", "外键约束阻止了本次操作，请检查相关表中的记录。")
    if code in {1205, 1213}:
        return _error(409, "TABLE_ROW_BUSY", "当前记录正在被其他操作占用，请稍后重试。")
    if code in {1048, 1264, 1265, 1292, 1364, 1366, 1406, 3140, 3819, 4025}:
        return _error(400, "INVALID_TABLE_ROWS", "字段值不符合 MySQL 的类型、长度或检查约束。")
    return _error(503, "TABLE_ROWS_UNAVAILABLE", "无法完成数据操作，请检查数据库连接、表结构及账号权限。")
