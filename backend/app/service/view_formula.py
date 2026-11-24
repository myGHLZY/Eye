from ast import Add, BinOp, Div, Mult, Name, Sub, UAdd, UnaryOp, USub, parse
from operator import add, mul, sub
from re import compile

from sqlalchemy import func, literal

from app.service.view_fields import ViewError

MAX_OPERANDS = 32
MAX_FORMULA_LENGTH = 1200
MAX_TOKENS = 200
TOKEN = compile(r"\s*(?:(?P<quoted>`(?:``|[^`])+`)|"
                r"(?P<number>(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?)|"
                r"(?P<field>[^\W\d]\w*)|(?P<symbol>[()+*/-]))")
AST_OPERATORS = {Add: "add", Sub: "subtract", Mult: "multiply", Div: "divide"}
OPERATORS = {"add": add, "subtract": sub, "multiply": mul}


def arithmetic(operator, left, right):
    """构建四则运算，除数为零时返回空值。"""
    if operator == "divide":
        return left / func.nullif(right, 0)
    if operator not in OPERATORS:
        raise ViewError("请选择有效的计算运算符。")
    return OPERATORS[operator](left, right)


def _expression(node, operands):
    """将受限的语法树转换为 SQLAlchemy 表达式。"""
    if isinstance(node, Name):
        return operands[node.id]
    if isinstance(node, UnaryOp) and isinstance(node.op, (UAdd, USub)):
        value = _expression(node.operand, operands)
        return -value if isinstance(node.op, USub) else value
    if isinstance(node, BinOp) and type(node.op) in AST_OPERATORS:
        return arithmetic(AST_OPERATORS[type(node.op)], _expression(node.left, operands), _expression(node.right, operands))
    raise ViewError("公式只支持字段、数字、括号和加减乘除。")


def compile_formula(expression, resolve_field, parse_number):
    """解析用户公式，并把全部数据项映射为已验证的字段或绑定值。"""
    if not isinstance(expression, str) or not expression.strip() or len(expression) > MAX_FORMULA_LENGTH:
        raise ViewError(f"请输入有效的公式（最多 {MAX_FORMULA_LENGTH} 个字符）。")
    expression = expression.strip()
    tokens, operands = [], {}
    position = 0
    while position < len(expression):
        if len(tokens) >= MAX_TOKENS:
            raise ViewError("公式过长，请减少括号或运算符。")
        token = TOKEN.match(expression, position)
        if token is None:
            raise ViewError("公式只支持字段、数字、括号和加减乘除。")
        position = token.end()
        kind = token.lastgroup
        value = token[kind]
        if kind == "symbol":
            tokens.append(value)
        else:
            if len(operands) >= MAX_OPERANDS:
                raise ViewError(f"公式最多支持 {MAX_OPERANDS} 个字段或数值。")
            key = f"arg_{len(operands)}"
            if kind == "quoted":
                value = value[1:-1].replace("``", "`")
            operands[key] = literal(parse_number(value)) if kind == "number" else resolve_field(value)
            tokens.append(key)
    try:
        tree = parse(" ".join(tokens), mode="eval")
    except (SyntaxError, RecursionError):
        raise ViewError("公式有误，请检查运算符和括号。") from None
    return _expression(tree.body, operands)
