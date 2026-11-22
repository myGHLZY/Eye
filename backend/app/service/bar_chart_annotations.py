from app.util.chart import ChartError, chart_number, chart_object


MAX_COMPARISONS = 8


def error_bars(style: dict, size: int) -> list:
    """读取与数据点一一对应的误差幅度。"""
    entries = style.get("errorBars", [None] * size)
    if not isinstance(entries, list) or len(entries) != size:
        raise ChartError()
    result = []
    for entry in entries:
        if entry is None:
            result.append(None)
        elif type(entry) not in (int, float) or entry < 0:
            raise ChartError()
        else:
            result.append(chart_number(entry))
    return result


def _significance_label(entry: dict) -> str:
    """将已有 p 值或选定符号转为图上文字。"""
    if "pValue" in entry:
        p_value = entry["pValue"]
        if "label" in entry or type(p_value) not in (int, float) or not 0 <= p_value <= 1:
            raise ChartError()
        for threshold, label in ((0.001, "***"), (0.01, "**"), (0.05, "*")):
            if p_value < threshold:
                return label
        return "ns"
    label = entry.get("label")
    if label not in ("*", "**", "***", "ns"):
        raise ChartError()
    return label


def comparisons(style: dict, size: int) -> list:
    """校验比较的柱索引，按区间长度从短到长排序。"""
    entries = style.get("significance", [])
    if not isinstance(entries, list) or len(entries) > MAX_COMPARISONS:
        raise ChartError()
    comparisons = {}
    for entry in entries:
        entry = chart_object(entry)
        left, right = entry.get("left"), entry.get("right")
        if not all(type(index) is int and 0 <= index < size for index in (left, right)) or left == right:
            raise ChartError()
        pair = tuple(sorted((left, right)))
        if pair in comparisons:
            raise ChartError()
        comparisons[pair] = _significance_label(entry)
    return sorted(
        ((left, right, label) for (left, right), label in comparisons.items()),
        key=lambda comparison: (comparison[1] - comparison[0], comparison[0]),
    )


def draw_bar_labels(axes, bars, positions, values, errors, unit: str) -> None:
    """让数值标签避开误差棒端帽。"""
    labels = [f"{value:.4g}{unit}" for value in values]
    if all(error is None for error in errors):
        axes.bar_label(bars, labels=labels, padding=4, fontsize=8, color="#283e5a")
        return
    for x, value, error, label in zip(positions, values, errors, labels):
        direction = 1 if value >= 0 else -1
        axes.annotate(
            label, xy=(x, value + (error or 0) * direction), xytext=(0, 4 * direction),
            textcoords="offset points", ha="center", va="bottom" if direction > 0 else "top",
            fontsize=8, color="#283e5a",
        )


def draw_comparisons(axes, positions, values, errors, comparisons, show_values: bool) -> None:
    """为相交的比较括号逐层留出高度。"""
    lower, upper = axes.get_ylim()
    gap = (upper - lower) * 0.075
    peaks = [max(0, value + (error or 0)) for value, error in zip(values, errors)]
    levels = []
    for left, right, label in comparisons:
        top = max(peaks[left:right + 1]) + gap * (1.15 if show_values else 0.65)
        for other_left, other_right, height in levels:
            if left <= other_right and other_left <= right:
                top = max(top, height + gap)
        x1, x2 = positions[left], positions[right]
        foot = top - gap * 0.22
        axes.plot([x1, x1, x2, x2], [foot, top, top, foot], color="#263c5a", linewidth=1.2, zorder=6)
        axes.annotate(label, xy=((x1 + x2) / 2, top), xytext=(0, 2), textcoords="offset points",
                      ha="center", va="bottom", fontsize=10, color="#263c5a", zorder=6)
        levels.append((left, right, top))
    axes.set_ylim(lower, max(upper, max(height for _, _, height in levels) + gap))
