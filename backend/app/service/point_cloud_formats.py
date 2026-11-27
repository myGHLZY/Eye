import csv
import struct
from itertools import chain, islice

import numpy as np

MAX_SOURCE_POINTS = 8_000_000
MAX_LINE_BYTES = 64 * 1024
MAX_HEADER_BYTES = 64 * 1024
BATCH_SIZE = 32_768
XYZ = ("x", "y", "z")
RGB_NAMES = (("red", "green", "blue"), ("r", "g", "b"))
TEXT_FORMATS = frozenset(("xyz", "xyzrgb", "pts", "csv", "tsv", "txt", "asc"))
FORMATS = TEXT_FORMATS | {"ply", "pcd", "las", "laz"}
PLY_TYPES = {
    "char": "i1", "int8": "i1", "uchar": "u1", "uint8": "u1",
    "short": "i2", "int16": "i2", "ushort": "u2", "uint16": "u2",
    "int": "i4", "int32": "i4", "uint": "u4", "uint32": "u4",
    "float": "f4", "float32": "f4", "double": "f8", "float64": "f8",
}


class PointCloudError(ValueError):
    pass


class PointCloudLimitError(PointCloudError):
    pass


def ensure_point_limit(count):
    if count > MAX_SOURCE_POINTS:
        raise PointCloudLimitError(f"文件最多可包含 {MAX_SOURCE_POINTS:,} 个点。")


def _line(stream):
    line = stream.readline(MAX_LINE_BYTES + 1)
    if len(line) > MAX_LINE_BYTES:
        raise PointCloudError("点云文件有一行超过 64 KiB，请检查文件格式。")
    return line


def _header_lines(stream):
    while stream.tell() <= MAX_HEADER_BYTES:
        line = _line(stream)
        if not line or stream.tell() > MAX_HEADER_BYTES:
            break
        yield line.decode("ascii").split()
    raise PointCloudError("点云文件头部不完整或超过 64 KiB。")


def _read_exact(stream, size):
    data = stream.read(size)
    if len(data) != size:
        raise PointCloudError("点云数据不完整，请检查文件是否上传完整。")
    return data


def _rgb_fields(names):
    names = set(names)
    return next((fields for fields in RGB_NAMES if all(name in names for name in fields)), ())


def _record_batch(records, rgb, packed):
    points = np.column_stack([records[name] for name in XYZ]).astype(np.float64, copy=False)
    if rgb:
        columns = [records[name] for name in rgb]
        dtype = columns[0].dtype
        scale = {1: 255, 2: 65535}.get(dtype.itemsize, 0) if dtype.kind == "u" else 0
        return points, np.column_stack(columns), scale
    if packed:
        values = records[packed]
        bits = values.view("<u4") if values.dtype.kind == "f" else values.astype(np.uint32, copy=False)
        colors = np.column_stack([(bits >> shift) & 255 for shift in (16, 8, 0)])
        return points, colors, 255
    return points, None, 255


def _record_fields(layout, allow_packed):
    names = {name: (dtype, count) for name, dtype, count in layout}
    if len(names) != len(layout) or any(name not in names or names[name][1] != 1 for name in XYZ):
        raise PointCloudError("点云应包含互不重复的 X、Y、Z 坐标字段。")
    rgb = _rgb_fields(name for name, (_, count) in names.items() if count == 1)
    packed = next((
        name for name in ("rgb", "rgba")
        if name in names and names[name][1] == 1 and names[name][0].itemsize == 4
    ), None) if allow_packed and not rgb else None
    return (*XYZ, *rgb, *((packed,) if packed else ())), rgb, packed


def _read_records(stream, layout, count, encoding, *, allow_packed=False):
    if count < 0:
        raise PointCloudError("点云头部记录的点数无效。")
    ensure_point_limit(count)
    selected, rgb, packed = _record_fields(layout, allow_packed)
    if encoding == "ascii":
        offset = 0
        fields = {}
        for name, dtype, length in layout:
            fields[name] = (offset, dtype)
            offset += length
        columns, dtypes = zip(*(fields[name] for name in selected))
        dtype = np.dtype(list(zip(selected, dtypes)))
        for start in range(0, count, 4096):
            size = min(4096, count - start)
            lines = list(islice(_point_lines(stream), size))
            if len(lines) != size:
                raise PointCloudError("点云文件头部记录的点数与实际数据不符。")
            records = np.loadtxt(lines, dtype=dtype, usecols=columns, ndmin=1)
            yield _record_batch(records, rgb, packed)
        return

    if encoding == "binary_compressed":
        yield from _compressed_pcd(stream, layout, count, selected, rgb, packed)
        return

    dtype = np.dtype([(name, kind) if length == 1 else (name, kind, (length,))
                      for name, kind, length in layout])
    chunk_size = min(BATCH_SIZE, max(1, (4 * 1024**2) // dtype.itemsize))
    for start in range(0, count, chunk_size):
        size = min(chunk_size, count - start)
        records = np.frombuffer(_read_exact(stream, size * dtype.itemsize), dtype=dtype)
        yield _record_batch(records, rgb, packed)


def _compressed_pcd(stream, layout, count, selected, rgb, packed):
    import lzf

    compressed, uncompressed = struct.unpack("<II", _read_exact(stream, 8))
    unpadded = [field for field in layout if not field[0].startswith("__padding_")]
    if uncompressed != count * sum(kind.itemsize * length for _, kind, length in layout):
        layout = unpadded
    expected = count * sum(kind.itemsize * length for _, kind, length in layout)
    if not compressed or not uncompressed or expected != uncompressed:
        raise PointCloudError("压缩 PCD 的数据长度与文件头不一致。")
    if compressed > 128 * 1024**2 or uncompressed > 128 * 1024**2:
        raise PointCloudLimitError("压缩 PCD 的数据最多支持 128 MiB。")
    data = lzf.decompress(_read_exact(stream, compressed), uncompressed)
    if data is None or len(data) != uncompressed:
        raise PointCloudError("无法解压 PCD 的点数据。")
    fields = {}
    offset = 0
    for name, dtype, length in layout:
        if name in selected:
            fields[name] = np.frombuffer(data, dtype=dtype, count=count, offset=offset)
        offset += count * dtype.itemsize * length
    for start in range(0, count, BATCH_SIZE):
        records = {name: values[start:start + BATCH_SIZE] for name, values in fields.items()}
        yield _record_batch(records, rgb, packed)


def _ply_batches(stream):
    if _line(stream).strip() != b"ply":
        raise PointCloudError("文件缺少 PLY 标识。")
    count = None
    element = None
    encoding = None
    layout = []
    earlier_element = False
    types = {"ascii": "=", "binary_little_endian": "<", "binary_big_endian": ">"}
    for row in _header_lines(stream):
        if not row:
            continue
        key, *args = row
        if key == "end_header":
            break
        if key == "format" and len(args) == 2 and args[1] == "1.0":
            encoding = args[0]
        elif key == "element" and len(args) == 2:
            element = args[0]
            if element == "vertex":
                if count is not None or earlier_element:
                    raise PointCloudError("PLY 的顶点必须是第一组非空元素。")
                count = int(args[1])
            elif count is None and int(args[1]) != 0:
                earlier_element = True
        elif key == "property" and element == "vertex":
            if len(args) != 2 or args[0] not in PLY_TYPES:
                raise PointCloudError("PLY 顶点字段必须是数值标量。")
            layout.append((args[1].lower(), PLY_TYPES[args[0]], 1))
    if count is None or encoding not in types or not 3 <= len(layout) <= 128:
        raise PointCloudError("无效的 PLY 格式或顶点定义。")
    endian = types[encoding]
    fields = [(name, np.dtype(endian + dtype), length) for name, dtype, length in layout]
    yield from _read_records(stream, fields, count, "ascii" if encoding == "ascii" else "binary")


def _pcd_batches(stream):
    header = {}
    for row in _header_lines(stream):
        if not row or row[0].startswith("#"):
            continue
        key, *values = row
        key = key.upper()
        if key in header:
            raise PointCloudError("PCD 文件头包含重复的字段定义。")
        header[key] = values
        if key == "DATA":
            break

    names = header.get("FIELDS") or header.get("FIELD") or []
    sizes = [int(value) for value in header.get("SIZE", ())]
    types = header.get("TYPE", [])
    counts = [int(value) for value in header.get("COUNT", [1] * len(names))]
    if not 3 <= len(names) <= 128 or not len(names) == len(sizes) == len(types) == len(counts):
        raise PointCloudError("PCD 文件头的 FIELDS、SIZE、TYPE 或 COUNT 定义不完整。")
    layout = []
    for index, (name, size, kind, length) in enumerate(zip(names, sizes, types, counts)):
        kind = kind.upper()
        if not 1 <= length <= 512 or size not in ((4, 8) if kind == "F" else (1, 2, 4, 8)) or kind not in {"F", "I", "U"}:
            raise PointCloudError("PCD 包含不支持的数值字段类型。")
        field = f"__padding_{index}" if name == "_" else name.lower()
        layout.append((field, np.dtype(f"<{kind.lower()}{size}"), length))
    if sum(counts) > 1024:
        raise PointCloudError("PCD 单点的字段过多。")

    if "POINTS" in header:
        count, = map(int, header["POINTS"])
    else:
        width, = map(int, header.get("WIDTH", ()))
        height, = map(int, header.get("HEIGHT", ("1",)))
        count = width * height
    encoding, = header["DATA"]
    if encoding not in ("ascii", "binary", "binary_compressed"):
        raise PointCloudError("PCD 的 DATA 必须是 ascii、binary 或 binary_compressed。")
    yield from _read_records(stream, layout, count, encoding, allow_packed=True)


def _point_lines(stream):
    while line := _line(stream):
        stripped = line.strip()
        if stripped and not stripped.startswith((b"#", b"\xef\xbb\xbf#")):
            yield line


def _text_batches(stream, file_format):
    lines = _point_lines(stream)
    first = next(lines, b"").decode("utf-8-sig").rstrip("\r\n")
    if not first:
        return
    count = None
    if file_format == "pts" and first.strip().isdigit():
        count = int(first)
        ensure_point_limit(count)
        first = next(lines, b"").decode("utf-8").rstrip("\r\n")

    delimiter = next((sep for sep in (",", ";") if sep in first), "\t" if file_format == "tsv" else None)

    def split(line):
        return next(csv.reader([line], delimiter=delimiter, strict=True)) if delimiter else line.split()

    fields = split(first)
    names = [field.strip().lower() for field in fields]
    if len(fields) < 3:
        raise PointCloudError("文本点云每行至少需要 X、Y、Z 三列。")
    if all(name in names for name in XYZ):
        if any(names.count(name) != 1 for name in XYZ):
            raise PointCloudError("文本点云包含重复的坐标列名。")
        columns = [names.index(name) for name in (*XYZ, *_rgb_fields(names))]
    else:
        columns = [0, 1, 2]
        if len(fields) in (6, 7):
            columns.extend(range(len(fields) - 3, len(fields)))
        lines = chain((first.encode("utf-8"),), lines)

    seen = 0
    chunk = []
    for line in lines:
        values = split(line.decode("utf-8").rstrip("\r\n"))
        if len(values) != len(fields):
            raise PointCloudError(f"第 {seen + 1} 个点的列数与首行不一致。")
        try:
            chunk.append([float(values[index]) for index in columns])
        except ValueError:
            raise PointCloudError(f"第 {seen + 1} 个点的坐标或 RGB 不是数字。") from None
        seen += 1
        if len(chunk) == BATCH_SIZE:
            data = np.asarray(chunk, dtype=np.float64)
            yield data[:, :3], data[:, 3:] if len(columns) == 6 else None, 0
            chunk.clear()
    if count is not None and count != seen:
        raise PointCloudError("PTS 标注的点数与实际数据不符。")
    if chunk:
        data = np.asarray(chunk, dtype=np.float64)
        yield data[:, :3], data[:, 3:] if len(columns) == 6 else None, 0


def _las_batches(stream):
    import laspy
    import lazrs

    try:
        with laspy.open(stream, closefd=False, read_evlrs=False) as reader:
            count = reader.header.point_count
            ensure_point_limit(count)
            has_rgb = all(name in reader.header.point_format.dimension_names for name in RGB_NAMES[0])
            seen = 0
            for batch in reader.chunk_iterator(BATCH_SIZE):
                seen += len(batch)
                points = np.column_stack((np.asarray(batch.x), np.asarray(batch.y), np.asarray(batch.z)))
                colors = np.column_stack((batch.red, batch.green, batch.blue)) if has_rgb else None
                yield points, colors, -1
            if count != seen:
                raise PointCloudError("LAS/LAZ 标注的点数与实际数据不符。")
    except (laspy.errors.LaspyException, lazrs.LazrsError) as error:
        raise PointCloudError("无法读取 LAS/LAZ 的点数据，请检查文件格式。") from error


def point_batches(stream, file_format):
    if file_format in TEXT_FORMATS:
        return _text_batches(stream, file_format)
    return {"ply": _ply_batches, "pcd": _pcd_batches, "las": _las_batches, "laz": _las_batches}[file_format](stream)
