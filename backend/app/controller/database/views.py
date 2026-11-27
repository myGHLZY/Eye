from flask import request

from app.service.database_views import create_view, list_pivot_categories, preview_saved_view, preview_view

from .common import _database_response, _read_json, blueprint


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
