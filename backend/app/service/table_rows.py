import json
import re
from datetime import date, datetime
from decimal import Decimal
from math import isfinite

from sqlalchemy import MetaData, String, Table, bindparam, cast, func, inspect, null, select, type_coerce
from sqlalchemy.dialects import mysql
from sqlalchemy.exc import NoSuchTableError
from sqlalchemy.types import BINARY, VARBINARY, Boolean, Date, DateTime, Enum, Float, Integer, JSON, LargeBinary, Numeric, Time

from app.service.database_connection import database_engine_for_connection


class TableRowsError(ValueError):
    def __init__(self, message: str, code: str = "INVALID_TABLE_ROWS", status: int = 400):
        super().__init__(message)
        self.code = code
        self.status = status


def list_table_rows(name: str, connection_id: str | None, args) -> dict:
    page = _positive_int(args.get("page", "1"), "页码", 2_147_483_647)
    page_size = _positive_int(args.get("pageSize", "20"), "每页条数", 100)

    with database_engine_for_connection(connection_id) as engine, engine.begin() as connection:
        source = _table(connection, name)
        columns = [_column_info(source, field) for field in source.columns]
        fields = list(source.columns)
        key_fields = list(source.primary_key.columns)
        count_query = select(func.count()).select_from(source)
        row_query = select(*[_display_expression(field) for field in fields]).select_from(source)

        filter_field = args.get("filterColumn")
        if filter_field is not None:
            if filter_field not in source.c:
                raise TableRowsError("请选择当前表中的筛选字段。")
            condition = _filter(source.c[filter_field], args)
            count_query = count_query.where(condition)
            row_query = row_query.where(condition)
        elif "filterValue" in args or "filterNull" in args:
            raise TableRowsError("请先指定筛选字段。")

        total = connection.scalar(count_query)
        page = min(page, max(1, (total + page_size - 1) // page_size))
        order = key_fields or [
            field for field in fields
            if _kind(field) not in {"binary", "json", "unsupported"}
        ]
        result = connection.execute(
            row_query.order_by(*order).limit(page_size).offset((page - 1) * page_size)
        )
        rows = [
            {field.name: _json_value(value) for field, value in zip(fields, row)}
            for row in result
        ]

    return {
        "table": name,
        "columns": columns,
        "primaryKey": [field.name for field in key_fields],
        "canChangeRows": _usable_key(key_fields),
        "rows": rows,
        "page": page,
        "pageSize": page_size,
        "total": total,
    }


def mutate_table_rows(name: str, connection_id: str, method: str, payload) -> dict:
    if not isinstance(payload, dict):
        raise TableRowsError("请提交 JSON 对象。")

    with database_engine_for_connection(connection_id) as engine, engine.begin() as connection:
        source = _table(connection, name)
        if method == "POST":
            values = _write_values(source, payload.get("values"), creating=True)
            connection.execute(source.insert().values(values))
        else:
            conditions = _row_conditions(source, payload.get("key"))
            if method == "PATCH":
                values = _write_values(source, payload.get("values"), creating=False)
                statement = source.update().where(*conditions).values(values)
            else:
                statement = source.delete().where(*conditions)
            if connection.execute(statement).rowcount == 0:
                raise TableRowsError("这条记录已不存在，请刷新数据。", "TABLE_ROW_NOT_FOUND", 404)

    return {"status": "ok"}


def _positive_int(value: str, label: str, maximum: int) -> int:
    if not re.fullmatch(r"[0-9]{1,10}", value) or not 1 <= int(value) <= maximum:
        raise TableRowsError(f"{label}应为 1 至 {maximum} 的整数。")
    return int(value)


def _table(connection, name: str) -> Table:
    inspector = inspect(connection)
    if name not in inspector.get_table_names():
        raise NoSuchTableError(name)
    return Table(name, MetaData(), autoload_with=connection, resolve_fks=False)


def _column_info(source: Table, field) -> dict:
    kind = _kind(field)
    writable = kind != "unsupported" and field.computed is None
    generated_id = field is source.autoincrement_column
    has_default = field.server_default is not None or generated_id
    return {
        "name": field.name,
        "type": str(field.type),
        "kind": kind,
        "nullable": field.nullable,
        "hasDefault": has_default,
        "required": field.computed is None and not field.nullable and not has_default,
        "insertable": writable,
        "editable": writable and not generated_id,
        "filterable": kind not in {"json", "unsupported"},
        "options": field.type.enums if isinstance(field.type, Enum) else [],
    }


def _kind(field) -> str:
    value_type = field.type
    for types, kind in (
        ((Integer, Boolean, mysql.YEAR, mysql.BIT), "integer"),
        ((Float,), "float"),
        ((Numeric,), "decimal"),
        ((JSON,), "json"),
        ((DateTime,), "datetime"),
        ((Date,), "date"),
        ((Time,), "time"),
        ((LargeBinary, BINARY, VARBINARY), "binary"),
        ((Enum,), "enum"),
        ((String,), "text"),
    ):
        if isinstance(value_type, types):
            return kind
    return "unsupported"


def _display_expression(field):
    if isinstance(field.type, (Time, JSON, mysql.SET, Float)):
        return cast(field, String())
    if isinstance(field.type, Enum):
        return type_coerce(field, String())
    return field


def _json_value(value):
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray, memoryview)):
        return value.hex()
    if isinstance(value, Decimal) or (type(value) is int and abs(value) > 2**53 - 1):
        return str(value)
    return value


def _filter(field, args):
    if _kind(field) in {"json", "unsupported"}:
        raise TableRowsError("此字段类型暂不支持筛选。")
    if args.get("filterNull") == "1" and "filterValue" not in args:
        return field.is_(None)
    if "filterValue" not in args or "filterNull" in args:
        raise TableRowsError("请填写筛选值，或选择仅查 NULL。")
    return _match(field, args["filterValue"])


def _row_conditions(source: Table, key) -> list:
    key_fields = list(source.primary_key.columns)
    if not _usable_key(key_fields):
        raise TableRowsError("当前表没有可用于定位记录的主键。", "TABLE_ROW_KEY_REQUIRED", 409)
    if not isinstance(key, dict) or key.keys() != {field.name for field in key_fields}:
        raise TableRowsError("请提供该记录完整的原始主键。")
    return [_match(field, key[field.name]) for field in key_fields]


def _usable_key(fields) -> bool:
    return bool(fields) and all(_kind(field) not in {"float", "json", "unsupported"} for field in fields)


def _match(field, value):
    comparison = _display_expression(field) if isinstance(field.type, Float) else field
    return comparison == _value_expression(field, value)


def _write_values(source: Table, values, *, creating: bool) -> dict:
    if not isinstance(values, dict) or (not creating and not values):
        raise TableRowsError("请提交需要保存的字段。")

    permission = "insertable" if creating else "editable"
    if creating:
        for field in source.columns:
            if _column_info(source, field)["required"] and field.name not in values:
                raise TableRowsError(f"请填写字段「{field.name}」。")

    entries = {}
    for name, value in values.items():
        if name not in source.c:
            raise TableRowsError(f"字段「{name}」不在当前表中。")
        field = source.c[name]
        info = _column_info(source, field)
        if not info[permission]:
            raise TableRowsError(f"字段「{name}」由数据库管理或暂不支持写入。")
        entries[field] = _value_expression(field, value)
    return entries


def _value_expression(field, value):
    if value is None:
        if not field.nullable:
            raise TableRowsError(f"字段「{field.name}」不允许为 NULL。")
        return null()
    try:
        kind = _kind(field)
        converted = _convert_value(kind, field, value)
        parameter = bindparam(None, converted)
        return func.unhex(parameter) if kind == "binary" else parameter
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise TableRowsError(f"字段「{field.name}」的值与类型 {field.type} 不匹配。") from None


def _convert_value(kind: str, field, value):
    if type(value) not in (str, int, float):
        raise ValueError
    if kind == "integer":
        if not re.fullmatch(r"[+-]?[0-9]{1,20}", str(value)):
            raise ValueError
        return int(value)
    if kind in {"decimal", "float"}:
        number = str(value)
        pattern = r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)"
        if kind == "float":
            pattern += r"(?:[eE][+-]?[0-9]+)?"
        if len(number) > 128 or not re.fullmatch(pattern, number):
            raise ValueError
        if kind == "decimal":
            return Decimal(number)
        if not isfinite(float(number)):
            raise ValueError
        return number
    if not isinstance(value, str):
        raise ValueError
    if kind == "binary":
        if not re.fullmatch(r"(?:[0-9a-fA-F]{2})*", value):
            raise ValueError
        return value
    if kind == "json":
        json.loads(value)
    if kind == "enum" and value not in field.type.enums and value != "":
        raise ValueError
    if kind in {"date", "datetime", "time"}:
        date_pattern = r"[0-9]{4}-[0-9]{2}-[0-9]{2}"
        time_pattern = r"[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?"
        patterns = {
            "date": date_pattern,
            "datetime": date_pattern + r"[ T]" + time_pattern,
            "time": r"-?[0-9]{2,3}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?",
        }
        if not re.fullmatch(patterns[kind], value):
            raise ValueError
        return value.replace("T", " ")
    return value
