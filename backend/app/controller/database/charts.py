from flask import send_file

from app.service.bar_chart import BAR_RENDERER_REVISION, load_bar_data, render_bar_chart
from app.service.bar_of_pie_chart import load_bar_of_pie_data, render_bar_of_pie_chart
from app.service.cartesian_charts import (
    load_line_data, load_scatter_data, load_scatter_histogram_data, load_stacked_area_data,
    render_line_chart, render_scatter_chart, render_scatter_histogram_chart, render_stacked_area_chart,
)
from app.service.distribution_charts import (
    load_boxplot_data, load_cumulative_data, load_histogram_data, load_violin_data,
    render_boxplot_chart, render_cumulative_chart, render_histogram_chart, render_violin_chart,
)
from app.service.heatmap_chart import load_heatmap_data, render_heatmap_chart
from app.service.pie_chart import load_pie_data, render_pie_chart
from app.service.radar_chart import load_radar_data, render_radar_chart
from app.service.sankey_chart import load_sankey_data, render_sankey_chart
from app.service.statistical_charts import (
    load_errorbar_data, load_numeric_pair_data, render_confidence_ellipse_chart, render_errorbar_chart,
    render_hexbin_chart,
)
from app.service.subplot_chart import render_subplot_chart
from app.util.chart import ChartError
from app.util.response import error_response as _error

from .common import _database_response, _read_json, blueprint


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
