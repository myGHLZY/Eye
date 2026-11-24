from sqlalchemy.sql import quoted_name


class ViewError(ValueError):
    """将视图操作的关键错误返回给工作台。"""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def view_object(value):
    """读取工作台提交的对象。"""
    if not isinstance(value, dict):
        raise ViewError("视图配置无效。")
    return value


def view_text(value, message, limit=64):
    """验证名称和字段等短文本。"""
    if not isinstance(value, str) or not value.strip() or len(value) > limit or any(not c.isprintable() for c in value):
        raise ViewError(message)
    return value


def view_list(value, maximum, message):
    """验证工作台的有界列表。"""
    if not isinstance(value, list) or not 1 <= len(value) <= maximum:
        raise ViewError(message)
    return [view_object(item) for item in value]


def select_column(source, name):
    """只使用已反射或已构建查询中的字段。"""
    name = view_text(name, "请选择有效字段。")
    if name not in source.c:
        raise ViewError("所选字段已不存在，请刷新数据源。")
    return source.c[name]


def unique_alias(raw, aliases):
    """保证查询输出列名有效且唯一。"""
    name = view_text(raw, "输出列名须填写且最多 64 个字符。").strip()
    if name.casefold() in aliases:
        raise ViewError("输出列名有重复，请修改别名。")
    aliases.add(name.casefold())
    return quoted_name(name, True)
