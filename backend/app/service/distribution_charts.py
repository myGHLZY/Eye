from collections import defaultdict

from sqlalchemy import select

from app.service.chart_support import grouping_columns
from app.service.database_connection import database_engine_for_connection
from app.util.chart import (
    MAX_CHART_VALUE, ChartError, chart_figure, chart_number, chart_object, chart_palette, chart_text,
    draw_bars, figure_png, json_chart_number, render_lock, set_chart_ticks, style_cartesian_axes, style_flag,
)

MAX_SAMPLES = 10_000
MAX_BOX_GROUPS = 12
MIN_BINS = 5
MAX_BINS = 80


def histogram_bins(options):
    bins = options.get("bins", 20)
    if type(bins) is not int or not MIN_BINS <= bins <= MAX_BINS:
        raise ChartError(f"分箱数量必须是 {MIN_BINS} 至 {MAX_BINS} 之间的整数。")
    return bins


def histogram_edges(samples, bins):
    """生成等宽分箱，并处理常量样本及浮点精度下重合的边界。"""
    import numpy as np

    low, high = min(samples), max(samples)
    if low == high:
        padding = max(0.5, abs(low) * 1e-6)
        low, high = max(-MAX_CHART_VALUE, low - padding), min(MAX_CHART_VALUE, high + padding)
    return np.unique(np.linspace(low, high, bins + 1))


def _load_samples(payload, *, grouped=False):
    payload = chart_object(payload)
    connection_id = chart_text(payload, "connectionId", required=True)
    table_name = chart_text(payload, "table", required=True)
    value_name = chart_text(payload, "valueColumn", required=True)
    group_name = chart_text(payload, "groupColumn") if grouped else ""
    if group_name == value_name:
        raise ChartError("请选择与数值字段不同的分组字段。")

    with database_engine_for_connection(connection_id) as engine, engine.connect() as connection:
        _, category, metric = grouping_columns(connection, table_name, group_name or value_name, value_name)
        columns = (category, metric) if group_name else (metric,)
        query = select(*columns).where(*(column.is_not(None) for column in columns))
        rows = connection.execute(query.limit(MAX_SAMPLES + 1)).all()
    if len(rows) > MAX_SAMPLES:
        raise ChartError(f"此图最多读取 {MAX_SAMPLES:,} 条有效记录，请先用视图筛选数据。")
    return value_name, group_name, rows


def load_histogram_data(payload):
    import numpy as np

    bins = histogram_bins(chart_object(payload))
    value_name, _, rows = _load_samples(payload)
    samples = [chart_number(value) for (value,) in rows]
    if not samples:
        return {"xLabel": value_name, "edges": [], "counts": []}
    edges = histogram_edges(samples, bins)
    counts, _ = np.histogram(samples, bins=edges)
    return {"xLabel": value_name, "edges": edges.tolist(), "counts": counts.tolist()}


def render_histogram_chart(payload):
    from matplotlib.ticker import MaxNLocator, PercentFormatter

    payload = chart_object(payload)
    style = chart_object(payload.get("style", {}))
    raw_edges, counts = payload.get("edges"), payload.get("counts")
    if (not isinstance(raw_edges, list) or not isinstance(counts, list)
            or not 1 <= len(counts) <= MAX_BINS or len(raw_edges) != len(counts) + 1):
        raise ChartError()
    edges = [json_chart_number(edge) for edge in raw_edges]
    widths = [right - left for left, right in zip(edges, edges[1:])]
    if any(width <= 0 for width in widths) or any(type(count) is not int or count < 0 for count in counts):
        raise ChartError()
    total = sum(counts)
    if not 1 <= total <= MAX_SAMPLES:
        raise ChartError()

    percent = style_flag(style, "histogramPercent", False)
    heights = [count / total * 100 for count in counts] if percent else counts
    with render_lock:
        figure, font = chart_figure(style)
        axes = figure.subplots()
        style_cartesian_axes(axes, style, font)
        draw_bars(axes, edges[:-1], heights, width=widths, align="edge",
                  color=chart_palette(style)[0], edgecolor="white", linewidth=0.6)
        axes.set_ylim(bottom=0)
        if percent:
            axes.yaxis.set_major_formatter(PercentFormatter(xmax=100))
        else:
            axes.yaxis.set_major_locator(MaxNLocator(integer=True))
        return figure_png(figure)


def load_boxplot_data(payload):
    from matplotlib.cbook import boxplot_stats

    value_name, group_name, rows = _load_samples(payload, grouped=True)
    groups = defaultdict(list)
    for row in rows:
        group = row[0] if group_name else value_name
        groups[group].append(chart_number(row[-1]))
    if len(groups) > MAX_BOX_GROUPS:
        raise ChartError(f"箱线图最多支持 {MAX_BOX_GROUPS} 个分组。")
    boxes = []
    for group, values in sorted(groups.items()):
        stats = boxplot_stats(values, whis=1.5)[0]
        boxes.append({
            "label": str(group)[:120] or "空字符串", "count": len(values),
            **{key: float(stats[key]) for key in ("whislo", "q1", "med", "q3", "whishi")},
            "fliers": stats["fliers"].tolist(),
        })
    return {"boxes": boxes, "xLabel": group_name, "yLabel": value_name}


def render_boxplot_chart(payload):
    payload = chart_object(payload)
    style = chart_object(payload.get("style", {}))
    raw_boxes = payload.get("boxes")
    if not isinstance(raw_boxes, list) or not 1 <= len(raw_boxes) <= MAX_BOX_GROUPS:
        raise ChartError()
    keys = ("whislo", "q1", "med", "q3", "whishi")
    boxes, total = [], 0
    for raw in raw_boxes:
        item = chart_object(raw)
        values = [json_chart_number(item.get(key)) for key in keys]
        fliers, count = item.get("fliers"), item.get("count")
        if (values != sorted(values) or type(count) is not int or not isinstance(fliers, list)
                or not 0 <= len(fliers) < count <= MAX_SAMPLES or total + count > MAX_SAMPLES):
            raise ChartError()
        total += count
        boxes.append({
            "label": chart_text(item, "label", required=True), **dict(zip(keys, values)),
            "fliers": [json_chart_number(value) for value in fliers],
        })

    with render_lock:
        figure, font = chart_figure(style)
        axes = figure.subplots()
        style_cartesian_axes(axes, style, font)
        plot = axes.bxp(boxes, patch_artist=True, manage_ticks=False,
                        showfliers=style_flag(style, "showFliers", True),
                        medianprops={"color": "#172942", "linewidth": 1.6},
                        flierprops={"marker": "o", "markersize": 3, "alpha": 0.6})
        palette = chart_palette(style)
        for index, box in enumerate(plot["boxes"]):
            box.set_facecolor(palette[index % len(palette)])
            box.set_alpha(0.65)
        axes.set_xlim(0.5, len(boxes) + 0.5)
        set_chart_ticks(axes, [(index, box["label"]) for index, box in enumerate(boxes, 1)], font,
                        max_labels=MAX_BOX_GROUPS, label_length=20, fontsize=9)
        return figure_png(figure)
