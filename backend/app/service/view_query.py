from sqlalchemy import String, and_, case, cast, column, func, inspect, select, table
from sqlalchemy.sql import quoted_name

from app.service.chart_support import AGGREGATIONS, NUMERIC_TYPES
from app.service.database_catalog import reflect_source
from app.service.view_fields import ViewError, select_column, unique_alias, view_list, view_object, view_text
from app.service.view_transforms import VIEW_TRANSFORMS

MAX_DRAFTS = 10
MAX_PIVOT_COLUMNS = 16
MAX_CATEGORY_LENGTH = 256


class ViewQueryBuilder:
    """将连接、转宽表和中间草稿转换为 SQLAlchemy 查询。"""

    def __init__(self, connection, drafts):
        self.inspector = inspect(connection)
        self.drafts = {
            view_text(item.get("id"), "中间表配置无效。"): view_object(item.get("spec"))
            for item in view_list(drafts, MAX_DRAFTS, "中间表配置无效。")
        } if drafts != [] else {}
        if len(self.drafts) != len(drafts):
            raise ViewError("中间表标识重复。")
        self.catalog = {}
        self.resolved = {}
        self.active = set()

    def source(self, value, alias):
        """从当前库或草稿解析来源，并为当前步骤分配别名。"""
        value = view_text(value, "请选择数据源。", 74)
        kind, _, name = value.partition(":")
        if kind == "draft" and name in self.drafts:
            if name in self.active:
                raise ViewError("中间表不能循环引用。")
            if name not in self.resolved:
                self.active.add(name)
                try:
                    self.resolved[name] = self.build(self.drafts[name])
                finally:
                    self.active.remove(name)
            return self.resolved[name].subquery(alias)
        if kind != "db":
            raise ViewError("数据源已不存在，请重新选择。")
        name = view_text(name, "请选择有效的数据源。")
        if name not in self.catalog:
            fields = reflect_source(self.inspector, name)
            self.catalog[name] = table(quoted_name(name, True), *[
                column(quoted_name(field["name"], True), field["type"]) for field in fields
            ])
        return self.catalog[name].alias(alias)

    def build(self, spec):
        """按构建方式生成完整 SELECT。"""
        spec = view_object(spec)
        if spec.get("mode") == "join":
            return self._build_join(spec)
        if spec.get("mode") == "pivot":
            return self._build_pivot(spec)
        for mode, transform in VIEW_TRANSFORMS.items():
            if spec.get("mode") == mode:
                return transform(self.source(spec.get("source"), "input_data"), spec)
        raise ViewError("请选择一种视图构建方式。")

    def _build_join(self, spec):
        """按选定字段构建内连接或左连接并设置输出列名。"""
        left = self.source(spec.get("left"), "left_data")
        right = self.source(spec.get("right"), "right_data")
        join_type = spec.get("joinType")
        if join_type not in ("inner", "left"):
            raise ViewError("请选择内连接或左连接。")
        conditions = view_list(spec.get("conditions"), 8, "请至少添加一个连接条件。")
        keys = [select_column(left, item.get("left")) == select_column(right, item.get("right")) for item in conditions]
        outputs = view_list(spec.get("columns"), 64, "请选择要保留的输出字段。")
        selected, aliases = [], set()
        sources = {"left": left, "right": right}
        for field in outputs:
            side = view_text(field.get("side"), "请选择输出字段的来源。")
            if side not in sources:
                raise ViewError("请选择输出字段的来源。")
            value = select_column(sources[side], field.get("name"))
            selected.append(value.label(unique_alias(field.get("alias"), aliases)))
        return select(*selected).select_from(left.join(right, and_(*keys), isouter=join_type == "left"))

    def _build_pivot(self, spec):
        """按选中的类别值建立条件聚合列。"""
        source = self.source(spec.get("source"), "pivot_data")
        row = select_column(source, spec.get("row"))
        category = cast(select_column(source, spec.get("category")), String)
        if spec["row"] == spec["category"]:
            raise ViewError("行字段和列类别字段需要不同。")
        mode = spec.get("aggregation")
        if mode not in ("count", "sum", "average", "max", "min"):
            raise ViewError("请选择有效的聚合方式。")
        metric = 1
        if mode != "count":
            metric = select_column(source, spec.get("metric"))
            if not isinstance(metric.type, NUMERIC_TYPES):
                raise ViewError("所选聚合方式需要数值字段。")
        aggregate = AGGREGATIONS[mode][1]
        options = view_list(spec.get("columns"), MAX_PIVOT_COLUMNS, "请选择 1 至 16 个类别值。")
        columns, aliases, values = [], {row.name.casefold()}, set()
        for item in options:
            value = item.get("value")
            if not isinstance(value, str) or len(value) > MAX_CATEGORY_LENGTH or value in values:
                raise ViewError("列类别值无效或重复，请重新选择。")
            values.add(value)
            expression = case((category == value, metric))
            result = aggregate(expression) if mode == "count" else aggregate(expression, type_=metric.type)
            columns.append(result.label(unique_alias(item.get("alias"), aliases)))
        return select(row, *columns).where(row.is_not(None)).group_by(row)
