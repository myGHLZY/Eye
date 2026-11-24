from functools import lru_cache
from io import BytesIO
from math import ceil, isfinite
from pathlib import Path
from re import compile
from threading import Lock

DPI_OPTIONS = (130, 200, 300)
MAX_CHART_VALUE = 1e150
HEX_COLOR = compile(r"#[0-9a-fA-F]{6}")
render_lock = Lock()


class ChartError(ValueError):
    """供图表接口统一返回的参数错误。"""

    def __init__(self, message: str = "图表参数无效，请检查数据和样式设置。"):
        """没有具体处理建议时使用统一提示。"""
        super().__init__(message)


def chart_object(value) -> dict:
    """确认 JSON 请求体或子项是对象。"""
    if not isinstance(value, dict):
        raise ChartError()
    return value


def chart_text(data: dict, key: str, maximum: int = 120, required: bool = False) -> str:
    """读取字符串，按需限制长度并拒绝空值。"""
    value = data.get(key, "")
    if not isinstance(value, str) or len(value) > maximum or (required and not value.strip()):
        raise ChartError()
    return value


def chart_number(value) -> float:
    """把数据库数值转成 Matplotlib 可绘制的有限浮点数。"""
    try:
        number = float(value)
    except (OverflowError, ValueError, TypeError):
        raise ChartError() from None
    if not isfinite(number) or abs(number) > MAX_CHART_VALUE:
        raise ChartError()
    return number


def chart_points(payload: dict, limit: int) -> list[tuple[str, float]]:
    """按传入顺序读取标签与数值，并限制预览的分类数。"""
    raw_points = payload.get("points")
    if not isinstance(raw_points, list) or not 1 <= len(raw_points) <= limit:
        raise ChartError(f"预览需要 1 至 {limit} 个分类。")
    points = []
    for raw in raw_points:
        point = chart_object(raw)
        value = point.get("value")
        if type(value) not in (int, float):
            raise ChartError()
        points.append((chart_text(point, "label"), chart_number(value)))
    return points


def style_choice(style: dict, key: str, choices, default):
    """读取枚举或布尔字段，保持 JSON 类型严格匹配。"""
    value = style.get(key, default)
    if type(value) is not type(default) or value not in choices:
        raise ChartError()
    return value


def style_flag(style: dict, key: str, default: bool) -> bool:
    """读取布尔开关。"""
    return style_choice(style, key, (True, False), default)


def style_range(style: dict, key: str, default: float, minimum: float, maximum: float) -> float:
    """读取有上下界的数值，排除布尔值。"""
    value = style.get(key, default)
    if type(value) not in (int, float) or not minimum <= value <= maximum:
        raise ChartError()
    return value


def style_color(style: dict, key: str, default: str) -> str:
    """读取六位 RGB 颜色。"""
    value = style.get(key, default)
    if not isinstance(value, str) or not HEX_COLOR.fullmatch(value):
        raise ChartError()
    return value


@lru_cache(maxsize=1)
def chart_font():
    """优先选取系统里的中文字体，并缓存查找结果。"""
    from matplotlib.font_manager import FontProperties, fontManager

    families = ("Noto Sans CJK SC", "Source Han Sans SC", "PingFang SC", "Microsoft YaHei", "SimHei")
    candidates = [font.fname for font in fontManager.ttflist if font.name.startswith(families)]
    candidates.extend(("/System/Library/Fonts/STHeiti Medium.ttc", "/System/Library/Fonts/Supplemental/Songti.ttc"))
    path = next((candidate for candidate in candidates if Path(candidate).is_file()), None)
    return FontProperties(fname=path)


def figure_png(figure) -> BytesIO:
    """把 Matplotlib Figure 写成可直接发送的 PNG 数据。"""
    from matplotlib.backends.backend_agg import FigureCanvasAgg

    image = BytesIO()
    FigureCanvasAgg(figure).print_png(image)
    image.seek(0)
    return image


def draw_bars(axes, x, y, *, width=0.65, **style):
    """在已有坐标轴上绘制柱形，供独立图与子图共用。"""
    return axes.bar(x, y, width=width, **style)


def draw_line(axes, x, y, *, markers=True, marker="o", markersize=4, linewidth=1.8, **style):
    """在已有坐标轴上绘制带可选数据点的折线。"""
    return axes.plot(x, y, linewidth=linewidth, marker=marker if markers else None, markersize=markersize, **style)


def draw_scatter(axes, x, y, *, size=40, alpha=0.75, **style):
    """在已有坐标轴上绘制半透明散点。"""
    return axes.scatter(x, y, s=size, alpha=alpha, **style)


def set_chart_ticks(axes, ticks, font, rotation=None, *, max_labels=6, label_length=16, fontsize=8):
    """为分类或时间横轴抽取刻度，并保留最后一个值。"""
    if not ticks:
        return
    ticks = list(dict(ticks).items())
    step = max(1, ceil((len(ticks) - 1) / max(1, max_labels - 1)))
    visible = list(ticks[::step])
    if visible[-1] != ticks[-1]:
        visible.append(ticks[-1])
    degrees = (28 if len(visible) > 4 else 0) if rotation is None else rotation
    positions, labels = zip(*visible)
    axes.set_xticks(positions, [label[:label_length] for label in labels],
                    rotation=degrees, ha="right" if degrees else "center",
                    fontsize=fontsize, fontproperties=font, parse_math=False)
