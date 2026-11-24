from flask import Blueprint, abort, current_app, jsonify, request, send_file
from sqlalchemy.exc import DBAPIError, NoSuchTableError, SQLAlchemyError
from werkzeug.exceptions import RequestEntityTooLarge

from app.database.database import DatabaseConfigurationError

from app.service.bar_chart import BAR_RENDERER_REVISION, load_bar_data, render_bar_chart
from app.service.bar_of_pie_chart import load_bar_of_pie_data, render_bar_of_pie_chart
from app.service.cartesian_charts import (
    load_line_data, load_scatter_data, load_scatter_histogram_data, load_stacked_area_data,
    render_line_chart, render_scatter_chart, render_scatter_histogram_chart, render_stacked_area_chart,
)
from app.service.database_catalog import describe_chart_source, list_chart_sources
from app.service.database_connection import (
    DatabaseConnectionError,
    DatabaseConnectionNotFoundError,
    apply_connection,
    disconnect_database_connection,
    get_connection_settings,
    list_database_connections,
    test_connection,
)
from app.service.distribution_charts import (
    load_boxplot_data, load_cumulative_data, load_histogram_data, load_violin_data,
    render_boxplot_chart, render_cumulative_chart, render_histogram_chart, render_violin_chart,
)
from app.service.pie_chart import load_pie_data, render_pie_chart
from app.service.heatmap_chart import load_heatmap_data, render_heatmap_chart
from app.service.database_views import create_view, list_pivot_categories, preview_saved_view, preview_view
from app.service.radar_chart import load_radar_data, render_radar_chart
from app.service.sankey_chart import load_sankey_data, render_sankey_chart
from app.service.statistical_charts import (
    load_errorbar_data, load_numeric_pair_data, render_confidence_ellipse_chart, render_errorbar_chart,
    render_hexbin_chart,
)
from app.service.subplot_chart import render_subplot_chart
from app.service.table_rows import TableRowsError, list_table_rows, mutate_table_rows
from app.service.table_schema import get_schema_diagram, get_table_schema, list_tables
from app.service.view_fields import ViewError
from app.util.chart import ChartError
from app.util.response import ok

blueprint = Blueprint("database", __name__, url_prefix="/api/database")
ADDITIONAL_CHARTS = {
    "line": (load_line_data, render_line_chart),
    "scatter": (load_scatter_data, render_scatter_chart),
    "heatmap": (load_heatmap_data, render_heatmap_chart),
    "scatter-histogram": (load_scatter_histogram_data, render_scatter_histogram_chart),
    "stacked-area": (load_stacked_area_data, render_stacked_area_chart),
    "histogram": (load_histogram_data, render_histogram_chart),
    "boxplot": (load_boxplot_data, render_boxplot_chart),
    "bar-of-pie": (load_bar_of_pie_data, render_bar_of_pie_chart),
    "errorbar": (load_errorbar_data, render_errorbar_chart),
    "confidence-ellipse": (load_numeric_pair_data, render_confidence_ellipse_chart),
    "cumulative": (load_cumulative_data, render_cumulative_chart),
    "hexbin": (load_numeric_pair_data, render_hexbin_chart),
    "violin": (load_violin_data, render_violin_chart),
}
CHART_RENDER_LIMITS_KIB = {
    "scatter": 384, "scatter-histogram": 384, "boxplot": 384, "cumulative": 384, "violin": 384,
    "confidence-ellipse": 640, "hexbin": 640,
}


@blueprint.before_request
def require_local_request():
    if request.remote_addr not in {"127.0.0.1", "::1", "::ffff:127.0.0.1"}:
        return _error(403, "LOCAL_ACCESS_REQUIRED", "请从运行 Eye 后端的本机访问连接设置。")


@blueprint.get("/connection")
def connection_settings():
    response = ok(get_connection_settings(current_app))
    response.headers["Cache-Control"] = "no-store"
    return response


@blueprint.get("/connections")
def connections():
    return _database_response(list_database_connections, current_app)


@blueprint.delete("/connections/<connection_id>")
def disconnect(connection_id: str):
    try:
        disconnect_database_connection(current_app, connection_id)
    except OSError:
        return _error(500, "DATABASE_SETTINGS_WRITE_FAILED", "无法保存断开结果。请检查后端目录的写入权限。")
    return ok({"status": "ok", "message": "数据库连接已断开。"})


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


@blueprint.post("/views/preview")
def view_preview():
    """生成定义并预览可视化构建结果。"""
    return _database_response(preview_view, _read_json(128 * 1024))


@blueprint.post("/views/categories")
def view_categories():
    """获取转宽表时可选的类别值。"""
    return _database_response(list_pivot_categories, _read_json(128 * 1024))


@blueprint.post("/views")
def save_view():
    """创建用户已确认的视图。"""
    return _database_response(create_view, _read_json(128 * 1024), status=201)


@blueprint.get("/views/rows")
def view_rows():
    """预览已保存视图的前 20 行。"""
    return _database_response(preview_saved_view, request.args.get("connectionId"), request.args.get("name"))


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


@blueprint.post("/charts/bar/data")
def bar_chart_data():
    """查询柱状图聚合数据。"""
    return _database_response(load_bar_data, _read_json(32 * 1024))


@blueprint.post("/charts/bar/render")
def bar_chart_render():
    """生成柱状图 PNG，并返回渲染接口版本。"""
    return _chart_image(
        render_bar_chart, "bar-chart.png", "INVALID_BAR_CHART",
        headers={"X-Eye-Bar-Renderer": BAR_RENDERER_REVISION},
    )


@blueprint.post("/charts/pie/data")
def pie_chart_data():
    """查询饼图的分类数值和总量。"""
    return _database_response(load_pie_data, _read_json(32 * 1024), chart_error="INVALID_PIE_CHART")


@blueprint.post("/charts/pie/render")
def pie_chart_render():
    """生成饼图 PNG。"""
    return _chart_image(render_pie_chart, "pie-chart.png", "INVALID_PIE_CHART")


@blueprint.post("/charts/radar/data")
def radar_chart_data():
    """查询雷达图的指标和系列。"""
    return _database_response(load_radar_data, _read_json(32 * 1024), chart_error="INVALID_RADAR_CHART")


@blueprint.post("/charts/radar/render")
def radar_chart_render():
    """生成雷达图 PNG。"""
    return _chart_image(render_radar_chart, "radar-chart.png", "INVALID_RADAR_CHART")


@blueprint.post("/charts/sankey/data")
def sankey_chart_data():
    """查询桑基图的来源、目标与流量。"""
    return _database_response(load_sankey_data, _read_json(32 * 1024), chart_error="INVALID_SANKEY_CHART")


@blueprint.post("/charts/sankey/render")
def sankey_chart_render():
    """生成桑基图 PNG。"""
    return _chart_image(render_sankey_chart, "sankey-chart.png", "INVALID_SANKEY_CHART")


@blueprint.post(f"/charts/<any({','.join(map(repr, ADDITIONAL_CHARTS))}):kind>/<any(data,render):action>")
def additional_chart(kind, action):
    """通过统一入口读取数据或渲染 PNG。"""
    load, render = ADDITIONAL_CHARTS[kind]
    error_code = f"INVALID_{kind.upper().replace('-', '_')}_CHART"
    if action == "data":
        return _database_response(load, _read_json(32 * 1024), chart_error=error_code)
    maximum = CHART_RENDER_LIMITS_KIB.get(kind, 96) * 1024
    return _chart_image(render, f"{kind}-chart.png", error_code, maximum=maximum)


@blueprint.post("/charts/subplot/render")
def subplot_chart_render():
    """读取各子图数据并返回组合 PNG。"""
    return _chart_image(render_subplot_chart, "subplot-chart.png", "INVALID_SUBPLOT_CHART")


def _chart_image(render, filename: str, error_code: str, *, headers=None, maximum=32 * 1024):
    """统一解析渲染请求并封装 PNG 响应。"""
    try:
        image = render(_read_json(maximum))
    except ChartError as error:
        return _error(400, error_code, str(error))
    response = send_file(image, mimetype="image/png", download_name=filename)
    response.headers["Cache-Control"] = "no-store"
    response.headers.update(headers or {})
    return response


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
