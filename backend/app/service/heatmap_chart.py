from sqlalchemy import select

from app.service.chart_support import AGGREGATIONS, grouping_columns, paired_totals
from app.service.database_connection import database_engine_for_connection
from app.util.chart import (
    DPI_OPTIONS, ChartError, chart_font, chart_number, chart_object, chart_text, figure_png, render_lock,
    style_choice, style_flag,
)

MAX_ROWS, MAX_COLUMNS = 30, 16
WIDE_AGGREGATIONS = ("raw", "sum", "average", "max", "min")


def _wide_row_range(payload):
    """读取可选的数值行范围。"""
    bounds = payload.get("rowMin"), payload.get("rowMax")
    for value in bounds:
        if value is not None:
            if type(value) not in (int, float):
                raise ChartError("请输入有效的行字段范围。")
            chart_number(value)
    if None not in bounds and bounds[0] > bounds[1]:
        raise ChartError("行范围的上限不能小于下限。")
    return bounds


def _load_wide_heatmap(payload):
    """按选择顺序读取宽表的数值列，直接组成矩阵。"""
    connection_id = chart_text(payload, "connectionId", required=True)
    table_name = chart_text(payload, "table", required=True)
    row_name = chart_text(payload, "categoryColumn", required=True)
    names = payload.get("valueColumns")
    if (
        not isinstance(names, list) or not 1 <= len(names) <= MAX_COLUMNS
        or any(not isinstance(name, str) or not name or len(name) > 120 for name in names)
        or len(set(names)) != len(names) or row_name in names
    ):
        raise ChartError(f"请选择 1 至 {MAX_COLUMNS} 个不同的数值列。")
    mode = style_choice(payload, "aggregation", WIDE_AGGREGATIONS, "raw")
    minimum, maximum = _wide_row_range(payload)
    with database_engine_for_connection(connection_id) as engine, engine.connect() as connection:
        source, row_column, _ = grouping_columns(
            connection, table_name, row_name, "", numeric_axis=minimum is not None or maximum is not None,
            extra_metrics=names,
        )
        columns = [source.c[name] for name in names]
        label = "原值"
        if mode != "raw":
            label, aggregate = AGGREGATIONS[mode]
            query = select(row_column, *(aggregate(column) for column in columns)).group_by(row_column)
        else:
            query = select(row_column, *columns)
        query = query.where(row_column.is_not(None))
        if minimum is not None:
            query = query.where(row_column >= minimum)
        if maximum is not None:
            query = query.where(row_column <= maximum)
        records = connection.execute(query.order_by(row_column).limit(MAX_ROWS + 1)).all()

    keys = [record[0] for record in records]
    if len(set(keys)) != len(keys):
        raise ChartError("行字段有重复值，请选择合计、平均值等聚合方式。")
    if len(records) > MAX_ROWS:
        raise ChartError(f"热力图最多支持 {MAX_ROWS} 行，请缩小行字段范围。")
    return {
        "rows": [str(key)[:120] or "空字符串" for key in keys],
        "columns": names,
        "values": [[chart_number(value) if value is not None else None for value in record[1:]] for record in records],
        "seriesName": label,
    }


def load_heatmap_data(payload) -> dict:
    """从长表或宽表读取矩阵，保留空单元格。"""
    payload = chart_object(payload)
    if style_choice(payload, "layout", ("long", "wide"), "long") == "wide":
        return _load_wide_heatmap(payload)
    allowed = (*[code for code in AGGREGATIONS if code != "share"], "raw")
    entries, truncated, name = paired_totals(payload, MAX_ROWS * MAX_COLUMNS, allowed=allowed, by_category=True)
    rows = list(dict.fromkeys(row for row, _, _ in entries))
    columns = list(dict.fromkeys(column for _, column, _ in entries))
    if truncated or len(rows) > MAX_ROWS or len(columns) > MAX_COLUMNS:
        raise ChartError(f"热力图最多支持 {MAX_ROWS} 行和 {MAX_COLUMNS} 列，请缩小分类数量。")
    cells = {(row, column): chart_number(value) for row, column, value in entries}
    if payload.get("aggregation") == "raw" and len(cells) != len(entries):
        raise ChartError("每个热力图单元格只能有一条原始记录，请选择合计或平均值等聚合方式。")
    return {
        "rows": [str(row)[:120] or "空字符串" for row in rows],
        "columns": [str(column)[:120] or "空字符串" for column in columns],
        "values": [[cells.get((row, column)) for column in columns] for row in rows],
        "seriesName": name,
    }


def render_heatmap_chart(payload):
    """用带色标的矩阵绘制热力图，灰色表示没有记录。"""
    payload = chart_object(payload)
    style = chart_object(payload.get("style", {}))
    rows, columns, values = (payload.get(key) for key in ("rows", "columns", "values"))
    if (
        not isinstance(rows, list) or not 1 <= len(rows) <= MAX_ROWS
        or not isinstance(columns, list) or not 1 <= len(columns) <= MAX_COLUMNS
        or any(not isinstance(label, str) or len(label) > 120 for label in (*rows, *columns))
        or not isinstance(values, list) or len(values) != len(rows)
    ):
        raise ChartError()
    matrix = []
    for row in values:
        if not isinstance(row, list) or len(row) != len(columns) or any(
            value is not None and type(value) not in (int, float) for value in row
        ):
            raise ChartError()
        matrix.append([chart_number(value) if value is not None else float("nan") for value in row])
    dpi = style_choice(style, "dpi", DPI_OPTIONS, 130)

    with render_lock:
        import numpy as np
        from matplotlib import colormaps
        from matplotlib.figure import Figure

        font = chart_font()
        palette = style_choice(style, "colorMap", ("Blues", "YlOrRd", "viridis", "coolwarm"), "Blues")
        color_map = colormaps[palette].with_extremes(bad="#edf2f7")
        figure = Figure(figsize=(9, 6), dpi=dpi, layout="constrained", facecolor="#ffffff")
        axes = figure.subplots()
        image = axes.imshow(np.ma.masked_invalid(matrix), cmap=color_map, aspect="auto")
        axes.set_xticks(range(len(columns)), [name[:15] for name in columns], rotation=35, ha="right",
                        fontproperties=font, fontsize=9, parse_math=False)
        axes.set_yticks(range(len(rows)), [name[:15] for name in rows], fontproperties=font, fontsize=9, parse_math=False)
        axes.set_xlabel(chart_text(style, "xLabel", maximum=60), fontproperties=font, parse_math=False)
        axes.set_ylabel(chart_text(style, "yLabel", maximum=60), fontproperties=font, parse_math=False)
        figure.suptitle(chart_text(style, "title", maximum=60), fontproperties=font, parse_math=False)
        figure.colorbar(image, ax=axes, shrink=0.82)
        if style_flag(style, "showValues", True):
            for y, row in enumerate(values):
                for x, value in enumerate(row):
                    if value is None:
                        continue
                    red, green, blue, _ = image.cmap(image.norm(value))
                    color = "#14233b" if 0.21 * red + 0.72 * green + 0.07 * blue > 0.55 else "#ffffff"
                    axes.text(x, y, f"{value:.3g}", ha="center", va="center", fontsize=8, color=color)
        return figure_png(figure)
