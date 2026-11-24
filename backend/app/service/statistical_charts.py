from math import log1p, sqrt

from sqlalchemy import func, select

from app.service.chart_support import (
    MAX_SAMPLES, axis_position, category_point, grouping_columns, read_sample_rows, sample_point,
)
from app.service.database_connection import database_engine_for_connection
from app.util.chart import (
    ChartError, chart_figure, chart_legend, chart_number, chart_object, chart_palette, chart_text,
    draw_scatter, figure_png, json_chart_number, render_lock, set_chart_ticks, style_cartesian_axes,
    style_choice, style_flag,
)

MAX_ERROR_POINTS = 96


def load_errorbar_data(payload):
    payload = chart_object(payload)
    connection_id = chart_text(payload, "connectionId", required=True)
    table_name = chart_text(payload, "table", required=True)
    x_name = chart_text(payload, "categoryColumn", required=True)
    y_name = chart_text(payload, "valueColumn", required=True)
    error_name = chart_text(payload, "secondaryValueColumn")
    if error_name == y_name:
        raise ChartError("请选择不同的估计值字段和误差字段。")

    with database_engine_for_connection(connection_id) as engine, engine.connect() as connection:
        source, x, y = grouping_columns(connection, table_name, x_name, y_name, error_name,
                                         numeric_group=bool(error_name))
        conditions = (x.is_not(None), y.is_not(None))
        if error_name:
            error = source.c[error_name]
            query = select(x, y, error).where(*conditions, error.is_not(None))
        else:
            query = select(x, func.avg(y), func.count(y), func.stddev_samp(y)).where(*conditions).group_by(x)
        rows = connection.execute(query.order_by(x).limit(MAX_ERROR_POINTS + 1)).all()

    if error_name and len({row[0] for row in rows}) != len(rows):
        raise ChartError("使用误差字段时，每个横轴值必须只对应一条记录。")
    points = []
    for index, (category, value, *stats) in enumerate(rows[:MAX_ERROR_POINTS]):
        if error_name:
            error = chart_number(stats[0])
            if error < 0:
                raise ChartError("误差字段必须是非负数值。")
            point = {**category_point(category, value), "error": error}
        else:
            point = sample_point(category, value, *stats)
        points.append({**point, "x": axis_position(category, index)})
    return {
        "points": points, "xLabel": x_name, "yLabel": y_name if error_name else f"{y_name}（平均值）",
        "errorMode": "column" if error_name else "samples", "truncated": len(rows) > MAX_ERROR_POINTS,
    }


def render_errorbar_chart(payload):
    payload = chart_object(payload)
    style = chart_object(payload.get("style", {}))
    mode = style_choice(payload, "errorMode", ("samples", "column"), "samples")
    measure = style_choice(style, "errorMeasure", ("sd", "sem"), "sd")
    error_key = "error" if mode == "column" else {"sd": "sampleSd", "sem": "sampleSem"}[measure]
    raw_points = payload.get("points")
    if not isinstance(raw_points, list) or not 1 <= len(raw_points) <= MAX_ERROR_POINTS:
        raise ChartError()
    positions, values, labels, errors = [], [], [], []
    for index, raw in enumerate(raw_points):
        point = chart_object(raw)
        positions.append(json_chart_number(point.get("x", index)))
        values.append(json_chart_number(point.get("value")))
        labels.append(chart_text(point, "label"))
        error = point.get(error_key)
        if error is None and mode == "samples":
            errors.append(float("nan"))
        else:
            error = json_chart_number(error)
            if error < 0:
                raise ChartError("误差幅度必须为非负数。")
            errors.append(error)

    with render_lock:
        figure, font = chart_figure(style)
        axes = figure.subplots()
        style_cartesian_axes(axes, style, font)
        yerr = errors if any(error >= 0 for error in errors) else None
        axes.errorbar(positions, values, yerr=yerr, fmt="o", capsize=4, markersize=4,
                      color=chart_palette(style)[0])
        set_chart_ticks(axes, list(zip(positions, labels)), font, max_labels=10, label_length=20, fontsize=9)
        return figure_png(figure)


def load_numeric_pair_data(payload):
    payload = chart_object(payload)
    connection_id = chart_text(payload, "connectionId", required=True)
    table_name = chart_text(payload, "table", required=True)
    x_name = chart_text(payload, "categoryColumn", required=True)
    y_name = chart_text(payload, "valueColumn", required=True)
    with database_engine_for_connection(connection_id) as engine, engine.connect() as connection:
        _, x, y = grouping_columns(connection, table_name, x_name, y_name, numeric_axis=True)
        rows = read_sample_rows(connection, select(x, y).where(x.is_not(None), y.is_not(None)))
    samples = [[chart_number(x), chart_number(y)] for x, y in rows]
    return {
        "samples": samples, "xLabel": x_name, "yLabel": y_name,
        "ranges": [[min(axis), max(axis)] for axis in zip(*samples)],
    }


def _numeric_pairs(payload):
    import numpy as np

    samples = payload.get("samples")
    if not isinstance(samples, list) or not 1 <= len(samples) <= MAX_SAMPLES:
        raise ChartError()
    pairs = []
    for pair in samples:
        if not isinstance(pair, list) or len(pair) != 2:
            raise ChartError()
        pairs.append([json_chart_number(axis) for axis in pair])
    return np.asarray(pairs)


def _ellipse_parameters(points):
    import numpy as np

    if len(points) < 3:
        raise ChartError("二维置信椭圆至少需要三对样本。")
    center = points.mean(axis=0)
    centered = points - center
    scales = np.max(np.abs(centered), axis=0)
    if np.any(np.ptp(points, axis=0) == 0):
        raise ChartError("二维置信椭圆需要两个有变化的数值字段。")
    covariance = np.cov(centered / scales, rowvar=False)
    deviations = np.sqrt(covariance.diagonal())
    correlation = covariance[0, 1] / deviations[0] / deviations[1]
    if abs(correlation) >= 1 - 1e-12:
        raise ChartError("两个字段的点近似成一直线，无法形成二维置信椭圆。")
    return center, scales * deviations, correlation


def render_confidence_ellipse_chart(payload):
    from matplotlib.patches import Ellipse
    from matplotlib.transforms import Affine2D

    payload = chart_object(payload)
    style = chart_object(payload.get("style", {}))
    coverage = style_choice(style, "coverage", (68, 90, 95, 99), 95)
    points = _numeric_pairs(payload)
    center, deviations, correlation = _ellipse_parameters(points)
    radius = sqrt(-2 * log1p(-coverage / 100))
    with render_lock:
        figure, font = chart_figure(style)
        axes = figure.subplots()
        style_cartesian_axes(axes, style, font)
        color = chart_palette(style)[0]
        draw_scatter(axes, *points.T, color=color, size=16, alpha=0.4)
        ellipse = Ellipse((0, 0), 2 * sqrt(1 + correlation), 2 * sqrt(1 - correlation),
                          edgecolor=color, facecolor="none", linewidth=1.7, label=f"{coverage}% 数据椭圆")
        ellipse.set_transform(Affine2D().rotate_deg(45).scale(*(deviations * radius)).translate(*center)
                              + axes.transData)
        axes.add_patch(ellipse)
        axes.autoscale_view()
        chart_legend(axes, style, font)
        return figure_png(figure)


def render_hexbin_chart(payload):
    payload = chart_object(payload)
    style = chart_object(payload.get("style", {}))
    points = _numeric_pairs(payload)
    grid_size = style_choice(style, "gridSize", range(10, 81), 30)
    color_map = style_choice(style, "colorMap", ("Blues", "YlOrRd", "viridis", "coolwarm"), "viridis")
    logarithmic = style_flag(style, "logScale", False)
    with render_lock:
        figure, font = chart_figure(style)
        axes = figure.subplots()
        style_cartesian_axes(axes, style, font)
        bins = axes.hexbin(*points.T, gridsize=grid_size, cmap=color_map, mincnt=1,
                           bins="log" if logarithmic else None)
        bar = figure.colorbar(bins, ax=axes)
        bar.set_label("频数（对数色阶）" if logarithmic else "频数", fontproperties=font)
        return figure_png(figure)
