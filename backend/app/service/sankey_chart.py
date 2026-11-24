from collections import defaultdict

from app.service.chart_support import category_point, paired_totals
from app.util.chart import (
    ChartError, chart_font, chart_number, chart_object, chart_text, figure_png, render_lock, style_flag, style_range,
)

MAX_FLOWS = 24
FLOW_X = (0.03, 0.37, 0.63, 0.97)


def load_sankey_data(payload) -> dict:
    """按来源和目标统计带方向的正流量。"""
    rows, truncated, name = paired_totals(payload, MAX_FLOWS, allowed=("count", "sum", "raw"))
    if any(value < 0 for _, _, value in rows):
        raise ChartError("桑基图需要非负流量。")
    flows = []
    for source, target, value in rows:
        if value == 0:
            continue
        flow = {"value": chart_number(value)}
        for side, node in (("source", source), ("target", target)):
            point = category_point(node, value, stable_key=True)
            flow[side] = point["label"] or "空字符串"
            flow[side + "Key"] = point["key"]
        flows.append(flow)
    return {"flows": flows, "seriesName": name, "truncated": truncated}


def _node_layout(flows, side, gap):
    """为一侧节点累计流量并分配垂直位置。"""
    totals = defaultdict(float)
    labels = {}
    for flow in flows:
        key = flow[side + "Key"]
        totals[key] += flow["width"]
        labels[key] = flow[side]

    span = sum(totals.values()) + (len(totals) - 1) * gap
    y = (1 + span) / 2
    nodes = {}
    for key in sorted(totals, key=totals.get, reverse=True):
        height = totals[key]
        y -= height
        nodes[key] = (y, height, labels[key])
        y -= gap
    return nodes


def _flow_starts(flows, side, nodes, opposite_side, opposite_nodes):
    """按对侧节点的顺序排列流带，减少交叉与遮挡。"""
    side_key, opposite_key = side + "Key", opposite_side + "Key"
    offsets = {key: node[0] for key, node in nodes.items()}
    starts = [0.0] * len(flows)
    ordered = sorted(enumerate(flows), key=lambda pair: opposite_nodes[pair[1][opposite_key]][0])
    for index, flow in ordered:
        key = flow[side_key]
        starts[index] = offsets[key]
        offsets[key] += flow["width"]
    return starts


def _draw_flow_values(axes, labels, font):
    """沿流带中心错开放置数值，优先保留大流量标签。"""
    x0, x1, x2, x3 = FLOW_X
    anchors = []
    for t in (0.5, 0.38, 0.62, 0.26, 0.74, 0.14, 0.86):
        inverse = 1 - t
        x = x0 * inverse**3 + 3 * x1 * inverse**2 * t + 3 * x2 * inverse * t**2 + x3 * t**3
        anchors.append((x, t**2 * (3 - 2 * t)))
    occupied = []
    for value, start, end in sorted(labels, key=lambda label: label[0], reverse=True):
        label = f"{value:,.8g}"
        half_width = 0.009 + 0.005 * len(label)
        for x, progress in anchors:
            y = start + (end - start) * progress
            if any(abs(x - prev_x) < half_width + width and abs(y - prev_y) < 0.034
                   for prev_x, prev_y, width in occupied):
                continue
            axes.text(
                x, y, label, ha="center", va="center", fontsize=8, fontproperties=font, color="#15243b",
                bbox={"boxstyle": "round,pad=0.17", "facecolor": "#ffffff", "edgecolor": "none", "alpha": 0.88},
                zorder=4, parse_math=False,
            )
            occupied.append((x, y, half_width))
            break


def render_sankey_chart(payload):
    """将成对流量画成宽度与数值成比例的连接带。"""
    payload = chart_object(payload)
    style = chart_object(payload.get("style", {}))
    entries = payload.get("flows")
    if not isinstance(entries, list) or not 1 <= len(entries) <= MAX_FLOWS:
        raise ChartError()
    flows = []
    for entry in entries:
        entry = chart_object(entry)
        flow = {field: chart_text(entry, field, required=True) for field in ("source", "target")}
        for side in ("source", "target"):
            key = side + "Key"
            flow[key] = chart_text(entry, key) or flow[side]
        value = entry.get("value")
        if type(value) not in (int, float) or not 0 < value <= 1e150:
            raise ChartError("桑基图流量需要为正数。")
        flows.append({**flow, "value": value})

    colors = style.get("colors", [])
    if not isinstance(colors, list) or any(not isinstance(color, str) for color in colors):
        raise ChartError()
    title = chart_text(style, "title", maximum=60)
    alpha = style_range(style, "flowOpacity", 0.42, 0.15, 0.85)
    show_values = style_flag(style, "showFlowValues", False)
    gap = 0.018
    counts = [len({flow[side + "Key"] for flow in flows}) for side in ("source", "target")]
    available = 0.90 - (max(counts) - 1) * gap
    total = sum(flow["value"] for flow in flows)
    for flow in flows:
        flow["width"] = (flow["value"] / total) * available
    sources = _node_layout(flows, "source", gap)
    targets = _node_layout(flows, "target", gap)
    left = _flow_starts(flows, "source", sources, "target", targets)
    right = _flow_starts(flows, "target", targets, "source", sources)

    with render_lock:
        from matplotlib.colors import is_color_like, to_rgba
        from matplotlib.figure import Figure
        from matplotlib.patches import PathPatch, Rectangle
        from matplotlib.path import Path

        if any(not is_color_like(color) for color in colors):
            raise ChartError()
        palette = colors or [f"C{index}" for index in range(10)]
        source_colors = {key: palette[index % len(palette)] for index, key in enumerate(sources)}
        font = chart_font()
        figure = Figure(figsize=(10, 6), dpi=130, layout="constrained", facecolor="#ffffff")
        axes = figure.subplots()
        axes.set(xlim=(-0.27, 1.27), ylim=(0, 1))
        axes.axis("off")
        x0, x1, x2, x3 = FLOW_X
        labels = []
        for flow, y0, y1 in zip(flows, left, right):
            width = flow["width"]
            vertices = [(x0, y0), (x1, y0), (x2, y1), (x3, y1),
                        (x3, y1 + width), (x2, y1 + width), (x1, y0 + width), (x0, y0 + width), (x0, y0)]
            codes = [Path.MOVETO, *([Path.CURVE4] * 3), Path.LINETO, *([Path.CURVE4] * 3), Path.CLOSEPOLY]
            axes.add_patch(PathPatch(
                Path(vertices, codes), facecolor=to_rgba(source_colors[flow["sourceKey"]], alpha),
                edgecolor=(1, 1, 1, 0.65), linewidth=min(0.55, 90 * width),
            ))
            labels.append((flow["value"], y0 + width / 2, y1 + width / 2))

        for nodes, x, label_x, alignment in ((sources, 0, -0.02, "right"), (targets, 0.97, 1.02, "left")):
            for key, (y, height, label) in nodes.items():
                color = source_colors[key] if alignment == "right" else "#526c8f"
                axes.add_patch(Rectangle((x, y), 0.03, height, color=color, linewidth=0))
                name = label if len(label) <= 14 else label[:13] + "…"
                axes.text(label_x, y + height / 2, name, ha=alignment, va="center",
                          fontproperties=font, fontsize=7 if max(counts) > 15 else 9, parse_math=False)
        if show_values:
            _draw_flow_values(axes, labels, font)
        if title:
            figure.suptitle(title, fontproperties=font, parse_math=False)
        return figure_png(figure)
