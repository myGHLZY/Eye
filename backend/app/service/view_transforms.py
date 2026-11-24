from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from operator import eq, ge, gt, le, lt, ne

from sqlalchemy import and_, case, func, literal, or_, select, true, union_all
from sqlalchemy.types import Boolean, Date, DateTime, String, Time

from app.service.chart_support import AGGREGATIONS, NUMERIC_TYPES
from app.service.view_fields import ViewError, select_column, unique_alias, view_list, view_object
from app.service.view_formula import MAX_OPERANDS, arithmetic, compile_formula


def _choice(value, options, message):
    if not isinstance(value, str) or value not in options:
        raise ViewError(message)
    return value


def _number(value):
    """解析字段常量并保留十进制精度。"""
    if type(value) not in (str, int, float) or len(str(value)) > 64:
        raise ViewError("请输入有效的数值。")
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        raise ViewError("请输入有效的数值。") from None
    if not number.is_finite() or (number and not -30 <= number.adjusted() <= 60):
        raise ViewError("数值超出可用范围。")
    return number or Decimal(0)


def _numeric_column(source, name):
    field = select_column(source, name)
    if not isinstance(field.type, NUMERIC_TYPES):
        raise ViewError("请选择数值字段。")
    return field


def _columns(source, names, minimum=0, maximum=16):
    """读取指定长度的字段清单，拒绝重复项。"""
    if not isinstance(names, list) or not minimum <= len(names) <= maximum:
        raise ViewError("字段数量不符合要求。")
    columns = [select_column(source, name) for name in names]
    if len({field.name for field in columns}) != len(columns):
        raise ViewError("字段不能重复选择。")
    return columns


def _names(source):
    return {col.name.casefold() for col in source.c}


COMPARISONS = {"eq": eq, "ne": ne, "gt": gt, "gte": ge, "lt": lt, "lte": le}
FILTER_OPERATORS = (*COMPARISONS, "contains", "isNull", "notNull")


def _filter_value(field, value):
    """按来源字段类型读取筛选值。"""
    if isinstance(field.type, NUMERIC_TYPES):
        return _number(value)
    if not isinstance(value, str) or len(value) > 512:
        raise ViewError("请输入有效的筛选值。")
    for data_type, parser in ((DateTime, datetime), (Date, date), (Time, time)):
        if isinstance(field.type, data_type):
            try:
                parsed = parser.fromisoformat(value.strip())
                if getattr(parsed, "tzinfo", None) is not None:
                    raise ValueError()
                return parsed
            except ValueError:
                raise ViewError("请输入有效的日期或时间，例如 2024-01-01 08:00:00。") from None
    if isinstance(field.type, Boolean):
        if value.lower() not in ("1", "0", "true", "false"):
            raise ViewError("布尔字段请输入 1 或 0。")
        return value.lower() in ("1", "true")
    return value


def _filter_condition(source, item):
    field = select_column(source, item.get("field"))
    op = _choice(item.get("operator"), FILTER_OPERATORS, "请选择筛选条件。")
    if op == "isNull":
        return field.is_(None)
    if op == "notNull":
        return field.is_not(None)
    if op == "contains":
        value = item.get("value")
        if not isinstance(field.type, String) or not isinstance(value, str) or len(value) > 512:
            raise ViewError("包含条件仅用于文本字段。")
        return field.contains(value, autoescape=True)
    return COMPARISONS[op](field, _filter_value(field, item.get("value")))


def build_filter(source, spec):
    """按所有或任一条件筛选来源行。"""
    match = _choice(spec.get("match"), ("all", "any"), "请选择条件匹配方式。")
    conditions = view_list(spec.get("conditions"), 16, "请添加 1 至 16 个筛选条件。")
    combine = and_ if match == "all" else or_
    return select(source).where(combine(*(_filter_condition(source, item) for item in conditions)))


def build_project(source, spec):
    """按配置顺序保留并重命名字段。"""
    columns = view_list(spec.get("columns"), 64, "请选择要保留的字段。")
    aliases = set()
    return select(*[
        select_column(source, item.get("name")).label(unique_alias(item.get("alias"), aliases))
        for item in columns
    ])


def _operand(source, raw):
    operand = view_object(raw)
    kind = _choice(operand.get("kind"), ("field", "number"), "请选择字段或固定数值。")
    if kind == "field":
        return _numeric_column(source, operand.get("value"))
    return literal(_number(operand.get("value")))


def _operand_expression(source, operands):
    """按先乘除、后加减的顺序组合多项计算。"""
    total = None
    additive = "add"
    term = _operand(source, operands[0])
    for argument in operands[1:]:
        operator = _choice(argument.get("operator"), ("add", "subtract", "multiply", "divide"), "请选择计算运算符。")
        operand = _operand(source, argument)
        if operator in ("multiply", "divide"):
            term = arithmetic(operator, term, operand)
        else:
            total = term if total is None else arithmetic(additive, total, term)
            additive = operator
            term = operand
    return term if total is None else arithmetic(additive, total, term)


def build_compute(source, spec):
    """用多项配置或公式计算一个新数值列。"""
    alias = unique_alias(spec.get("alias"), _names(source))
    mode = _choice(spec.get("inputMode", "fields"), ("fields", "formula"), "请选择计算配置方式。")
    if mode == "formula":
        expression = compile_formula(spec.get("expression"), lambda name: _numeric_column(source, name), _number)
    elif "operands" in spec:
        operands = view_list(spec["operands"], MAX_OPERANDS, f"请选择 2 至 {MAX_OPERANDS} 个字段或数值。")
        if len(operands) < 2:
            raise ViewError("请至少选择两个字段或数值。")
        expression = _operand_expression(source, operands)
    else:
        left, right = (_operand(source, spec.get(key)) for key in ("left", "right"))
        operator = _choice(spec.get("operator"), ("add", "subtract", "multiply", "divide"), "请选择计算运算符。")
        expression = arithmetic(operator, left, right)
    return select(source, expression.label(alias))


def _boundary_text(number):
    value = format(number, "f")
    return value.rstrip("0").rstrip(".") if "." in value else value


def build_bin(source, spec):
    """将数值按左闭右开的自定义区间归类。"""
    field = _numeric_column(source, spec.get("field"))
    alias = unique_alias(spec.get("alias"), _names(source))
    boundaries = spec.get("boundaries")
    if not isinstance(boundaries, list) or not 1 <= len(boundaries) <= 16:
        raise ViewError("请设置 1 至 16 个分界值。")
    bounds = [_number(value) for value in boundaries]
    if any(left >= right for left, right in zip(bounds, bounds[1:])):
        raise ViewError("分界值须按从小到大填写，并且不能重复。")
    labels = [_boundary_text(value) for value in bounds]
    intervals = [f"< {labels[0]}", *(f"[{lo}, {hi})" for lo, hi in zip(labels, labels[1:]))]
    expression = case((field.is_(None), None), *((field < bound, label) for bound, label in zip(bounds, intervals)),
                      else_=f"≥ {labels[-1]}")
    return select(source, expression.label(alias))


def _field_family(field):
    if isinstance(field.type, NUMERIC_TYPES):
        return "number"
    if isinstance(field.type, String):
        return "text"
    return type(field.type)


def build_unpivot(source, spec):
    """为每个保留行展开选中的宽表列，原空值也保留。"""
    keys = _columns(source, spec.get("keys"), maximum=64)
    outputs = view_list(spec.get("columns"), 16, "请选择 1 至 16 个展开字段。")
    fields = _columns(source, [item.get("name") for item in outputs], minimum=1)
    if set(field.name for field in fields) & {key.name for key in keys}:
        raise ViewError("保留字段和展开字段须不同。")
    if len({_field_family(field) for field in fields}) != 1:
        raise ViewError("请展开类型相近的字段，例如全部选择数值字段。")
    names = {key.name.casefold() for key in keys}
    category_alias = unique_alias(spec.get("categoryAlias"), names)
    value_alias = unique_alias(spec.get("valueAlias"), names)
    labels = set()
    mapping = union_all(*[
        select(literal(index).label("position"), literal(str(unique_alias(item.get("alias"), labels))).label("category"))
        for index, item in enumerate(outputs)
    ]).subquery("unpivot_columns")
    value = case(dict(enumerate(fields)), value=mapping.c.position)
    return select(*keys, mapping.c.category.label(category_alias), value.label(value_alias)).select_from(
        source.join(mapping, true())
    )


def _ordered(source, spec, direction):
    order = select_column(source, spec.get("order"))
    result = [order.desc() if direction == "desc" else order.asc()]
    if spec.get("tie"):
        tie = select_column(source, spec["tie"])
        if tie.name != order.name:
            result.append(tie.desc() if direction == "desc" else tie.asc())
    return result


def build_dedupe(source, spec):
    """删除完全重复行，或按组保留排序最新的一条。"""
    method = _choice(spec.get("method"), ("distinct", "latest"), "请选择去重方式。")
    if method == "distinct":
        return select(source).distinct()
    keys = _columns(source, spec.get("keys"), minimum=1)
    names = _names(source)
    index = 0
    while f"_eye_row_{index}" in names:
        index += 1
    internal = f"_eye_row_{index}"
    rank = func.row_number().over(partition_by=keys, order_by=_ordered(source, spec, "desc"))
    ranked = select(source, rank.label(internal)).subquery("latest_rows")
    return select(*(ranked.c[field.name] for field in source.c)).where(ranked.c[internal] == 1)


WINDOW_OPERATIONS = ("rank", "denseRank", "runningSum", "runningCount")


def _window_value(operation, keys, order, metric=None):
    """在明细行或汇总行上使用同一套窗口计算。"""
    options = {"partition_by": keys or None, "order_by": order}
    if operation == "runningSum":
        return func.sum(metric, type_=metric.type).over(**options, rows=(None, 0))
    if operation == "runningCount":
        return func.count().over(**options, rows=(None, 0))
    function = func.rank() if operation == "rank" else func.dense_rank()
    return function.over(**options)


def _build_grouped_window(source, spec, operation):
    """先 GROUP BY 成每组一行，再按需计算排名或累计。"""
    keys = _columns(source, spec.get("keys"), minimum=1)
    key_names = {key.name.casefold() for key in keys}
    aggregate = _choice(spec.get("aggregation"), ("sum", "average", "count", "min", "max"), "请选择汇总方式。")
    summary_alias = unique_alias(spec.get("summaryAlias"), key_names)
    if aggregate == "count":
        metric = func.count()
    else:
        field = _numeric_column(source, spec.get("metric"))
        metric = AGGREGATIONS[aggregate][1](field, type_=field.type)
    statement = select(*keys, metric.label(summary_alias)).group_by(*keys)
    if operation == "summary":
        return statement

    grouped = statement.subquery("grouped_data")
    direction = _choice(spec.get("direction"), ("asc", "desc"), "请选择排序方向。")
    name = spec.get("order") or summary_alias
    order_field = select_column(grouped, name)
    order = order_field.desc() if direction == "desc" else order_field.asc()
    partitions = _columns(grouped, spec.get("partitionKeys", []))
    if any(field.name == summary_alias for field in partitions):
        raise ViewError("分别计算字段须来自分组字段。")
    ordering = [order]
    if operation in ("runningSum", "runningCount"):
        ordering.extend(grouped.c[key.name].asc() for key in keys if key.name != name)
    alias = unique_alias(spec.get("alias"), key_names)
    value = _window_value(operation, partitions, ordering, grouped.c[summary_alias])
    return select(grouped, value.label(alias))


def build_window(source, spec):
    """根据粒度选择明细窗口计算或分组汇总。"""
    scope = _choice(spec.get("scope", "detail"), ("detail", "group"), "请选择计算粒度。")
    operations = (*WINDOW_OPERATIONS, "summary") if scope == "group" else WINDOW_OPERATIONS
    operation = _choice(spec.get("operation"), operations, "请选择排名或累计方式。")
    if scope == "group":
        return _build_grouped_window(source, spec, operation)

    direction = _choice(spec.get("direction"), ("asc", "desc"), "请选择排序方向。")
    keys = _columns(source, spec.get("keys"))
    alias = unique_alias(spec.get("alias"), _names(source))
    metric = _numeric_column(source, spec.get("metric")) if operation == "runningSum" else None
    ordering_spec = spec if operation in ("runningSum", "runningCount") else {"order": spec.get("order")}
    order = _ordered(source, ordering_spec, direction)
    return select(source, _window_value(operation, keys, order, metric).label(alias))


VIEW_TRANSFORMS = {
    "filter": build_filter,
    "project": build_project,
    "compute": build_compute,
    "bin": build_bin,
    "unpivot": build_unpivot,
    "dedupe": build_dedupe,
    "window": build_window,
}
