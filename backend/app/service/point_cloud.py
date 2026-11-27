import csv
import struct
from base64 import b64encode
from pathlib import Path

import numpy as np

from app.service.point_cloud_formats import (
    FORMATS, PointCloudError, PointCloudLimitError, ensure_point_limit, point_batches,
)

MAX_FILE_BYTES = 128 * 1024**2
MAX_PREVIEW_POINTS = 200_000


class UnsupportedPointCloudFormat(PointCloudError):
    pass


def _base64(array):
    return b64encode(array.tobytes()).decode("ascii")


def preview_point_cloud(stream, filename):
    file_format = Path(filename).suffix.lower().removeprefix(".")
    if file_format not in FORMATS:
        raise UnsupportedPointCloudFormat("请选择 PLY、PCD、LAS、LAZ 或受支持的文本点云文件。")
    file_size = stream.seek(0, 2)
    if file_size > MAX_FILE_BYTES:
        raise PointCloudLimitError("单个点云文件最多支持 128 MiB。")
    stream.seek(0)

    try:
        return _preview(file_format, point_batches(stream, file_format))
    except PointCloudError:
        raise
    except (ValueError, KeyError, IndexError, OSError, EOFError, csv.Error, struct.error) as error:
        raise PointCloudError("无法解析点云，请检查文件内容与扩展名是否一致。") from error


def _preview(file_format, batches):
    low = np.full(3, np.inf)
    high = np.full(3, -np.inf)
    rng = np.random.default_rng(0)
    selected = np.empty((0, 3))
    selected_colors = None
    ranks = np.empty(0)
    input_count = valid_count = 0
    color_peak = 0.0
    color_scale = 255
    for points, colors, scale in batches:
        input_count += len(points)
        ensure_point_limit(input_count)
        valid = np.isfinite(points).all(axis=1)
        points = points[valid]
        if not len(points):
            continue

        valid_count += len(points)
        low = np.minimum(low, points.min(axis=0))
        high = np.maximum(high, points.max(axis=0))
        selected = np.concatenate((selected, points))
        ranks = np.concatenate((ranks, rng.random(len(points))))
        if colors is not None:
            colors = np.clip(np.nan_to_num(colors[valid]), 0, 65535)
            color_peak = max(color_peak, float(colors.max()))
            color_scale = scale
            selected_colors = colors if selected_colors is None else np.concatenate((selected_colors, colors))
        if len(selected) > MAX_PREVIEW_POINTS:
            indices = np.argpartition(ranks, MAX_PREVIEW_POINTS - 1)[:MAX_PREVIEW_POINTS]
            selected, ranks = selected[indices], ranks[indices]
            if selected_colors is not None:
                selected_colors = selected_colors[indices]

    if not valid_count:
        raise PointCloudError("文件中没有可绘制的有限坐标。")
    origin = np.where(low == high, low, low / 2 + high / 2)
    radius = float(np.maximum(high - origin, origin - low).max()) or 1.0
    normalized = ((selected - origin) / radius).astype("<f4")
    if selected_colors is not None:
        if color_scale == -1:
            color_scale = 255 if color_peak <= 255 else 65535
        elif color_scale == 0:
            color_scale = 1 if color_peak <= 1 else 255 if color_peak <= 255 else 65535
        selected_colors = np.rint(np.clip(selected_colors / color_scale, 0, 1) * 255).astype(np.uint8)

    return {
        "format": file_format,
        "inputCount": input_count,
        "pointCount": valid_count,
        "previewCount": len(selected),
        "bounds": {"min": low.tolist(), "max": high.tolist()},
        "origin": origin.tolist(),
        "scale": radius,
        "positions": _base64(normalized),
        "colors": _base64(selected_colors) if selected_colors is not None else None,
    }
