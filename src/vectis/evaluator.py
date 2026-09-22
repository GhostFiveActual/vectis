# GHOST FIVE // VECTIS
# Evaluates deterministic VECTIS expressions and pure built in functions.
"""Deterministic pure expression evaluation for VECTIS."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Callable, Mapping, TypeAlias

from vectis.ast import (
    BinaryExpression,
    BooleanLiteral,
    CallExpression,
    Expression,
    IndexAccess,
    ListLiteral,
    MemberAccess,
    NumberLiteral,
    ObjectLiteral,
    Reference,
    StringLiteral,
    UnaryExpression,
)

Scalar: TypeAlias = str | int | float | bool | None
Value: TypeAlias = (
    Scalar
    | tuple["Value", ...]
    | dict[str, "Value"]
)
BuiltinHandler = Callable[[tuple[Value, ...]], Value]


class EvaluationError(ValueError):
    """Raised when a deterministic expression cannot be evaluated."""


def is_value(value: object) -> bool:
    """Return whether a runtime object belongs to the VECTIS value model."""
    if isinstance(value, (str, int, float, bool, type(None))):
        return True
    if isinstance(value, tuple):
        return all(is_value(item) for item in value)
    if isinstance(value, dict):
        return all(
            isinstance(key, str)
            and is_value(item)
            for key, item in value.items()
        )
    return False


@dataclass(frozen=True, slots=True)
class BuiltinFunction:
    name: str
    description: str
    min_args: int
    max_args: int | None
    handler: BuiltinHandler

    def validate_arity(self, count: int) -> None:
        if count < self.min_args:
            raise EvaluationError(
                f"{self.name}() expects at least {self.min_args} arguments"
            )
        if self.max_args is not None and count > self.max_args:
            raise EvaluationError(
                f"{self.name}() expects at most {self.max_args} arguments"
            )


def _require_text(value: Value, name: str) -> str:
    if not isinstance(value, str):
        raise EvaluationError(f"{name}() expects string arguments")
    return value


def _require_number(value: Value, name: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EvaluationError(f"{name}() expects numeric arguments")
    return value


def _upper(args: tuple[Value, ...]) -> Value:
    return _require_text(args[0], "upper").upper()


def _lower(args: tuple[Value, ...]) -> Value:
    return _require_text(args[0], "lower").lower()


def _trim(args: tuple[Value, ...]) -> Value:
    return _require_text(args[0], "trim").strip()


def _length(args: tuple[Value, ...]) -> Value:
    return len(_require_text(args[0], "length"))


def _stable_text(value: Value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (tuple, dict)):
        return json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    return str(value)


def _concat(args: tuple[Value, ...]) -> Value:
    return "".join(_stable_text(item) for item in args)


def _contains(args: tuple[Value, ...]) -> Value:
    return _require_text(args[1], "contains") in _require_text(
        args[0], "contains"
    )


def _starts_with(args: tuple[Value, ...]) -> Value:
    return _require_text(args[0], "starts_with").startswith(
        _require_text(args[1], "starts_with")
    )


def _ends_with(args: tuple[Value, ...]) -> Value:
    return _require_text(args[0], "ends_with").endswith(
        _require_text(args[1], "ends_with")
    )


def _capitalize(args: tuple[Value, ...]) -> Value:
    return _require_text(args[0], "capitalize").capitalize()


def _title(args: tuple[Value, ...]) -> Value:
    return _require_text(args[0], "title").title()


def _replace(args: tuple[Value, ...]) -> Value:
    text = _require_text(args[0], "replace")
    old = _require_text(args[1], "replace")
    new = _require_text(args[2], "replace")
    return text.replace(old, new)


def _repeat(args: tuple[Value, ...]) -> Value:
    text = _require_text(args[0], "repeat")
    count = _require_number(args[1], "repeat")
    if not isinstance(count, int):
        raise EvaluationError("repeat() count must be an integer")
    if not 0 <= count <= 1000:
        raise EvaluationError("repeat() count must be between 0 and 1000")
    return text * count


def _clamp(args: tuple[Value, ...]) -> Value:
    value = _require_number(args[0], "clamp")
    low = _require_number(args[1], "clamp")
    high = _require_number(args[2], "clamp")
    if low > high:
        raise EvaluationError("clamp() minimum cannot exceed maximum")
    return max(low, min(value, high))


def _between(args: tuple[Value, ...]) -> Value:
    value = _require_number(args[0], "between")
    low = _require_number(args[1], "between")
    high = _require_number(args[2], "between")
    if low > high:
        raise EvaluationError("between() minimum cannot exceed maximum")
    return low <= value <= high


def _if_else(args: tuple[Value, ...]) -> Value:
    condition = args[0]
    if not isinstance(condition, bool):
        raise EvaluationError("if_else() condition must be boolean")
    return args[1] if condition else args[2]


def _all_true(args: tuple[Value, ...]) -> Value:
    if not all(isinstance(item, bool) for item in args):
        raise EvaluationError("all_true() expects boolean arguments")
    return all(args)


def _any_true(args: tuple[Value, ...]) -> Value:
    if not all(isinstance(item, bool) for item in args):
        raise EvaluationError("any_true() expects boolean arguments")
    return any(args)


def _count_true(args: tuple[Value, ...]) -> Value:
    if not all(isinstance(item, bool) for item in args):
        raise EvaluationError("count_true() expects boolean arguments")
    return sum(1 for item in args if item)


def _average(args: tuple[Value, ...]) -> Value:
    values = tuple(_require_number(item, "average") for item in args)
    return sum(values) / len(values)


def _percent(args: tuple[Value, ...]) -> Value:
    value = _require_number(args[0], "percent")
    total = _require_number(args[1], "percent")
    if total == 0:
        raise EvaluationError("percent() total must not be zero")
    return (value / total) * 100


def _coalesce(args: tuple[Value, ...]) -> Value:
    for item in args:
        if item is not None:
            return item
    return None


def _abs(args: tuple[Value, ...]) -> Value:
    return abs(_require_number(args[0], "abs"))


def _round(args: tuple[Value, ...]) -> Value:
    value = _require_number(args[0], "round")
    if len(args) == 1:
        return round(value)
    digits = _require_number(args[1], "round")
    if not isinstance(digits, int):
        raise EvaluationError("round() digits must be an integer")
    return round(value, digits)


def _min(args: tuple[Value, ...]) -> Value:
    values = tuple(_require_number(item, "min") for item in args)
    return min(values)


def _max(args: tuple[Value, ...]) -> Value:
    values = tuple(_require_number(item, "max") for item in args)
    return max(values)


def _string(args: tuple[Value, ...]) -> Value:
    return _stable_text(args[0])


def _number(args: tuple[Value, ...]) -> Value:
    value = args[0]
    if isinstance(value, bool):
        raise EvaluationError("number() does not convert booleans")
    if isinstance(value, (int, float)):
        return value
    text = _require_text(value, "number").strip()
    try:
        return float(text) if "." in text else int(text)
    except ValueError as exc:
        raise EvaluationError(f"number() cannot parse {text!r}") from exc


def _boolean(args: tuple[Value, ...]) -> Value:
    value = args[0]
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "1", "on"}:
            return True
        if lowered in {"false", "no", "0", "off", ""}:
            return False
    raise EvaluationError(f"boolean() cannot convert {value!r}")


def _list(args: tuple[Value, ...]) -> Value:
    return tuple(args)


def _object(args: tuple[Value, ...]) -> Value:
    if len(args) % 2 != 0:
        raise EvaluationError(
            "object() expects alternating string keys and values"
        )

    result: dict[str, Value] = {}
    for index in range(0, len(args), 2):
        key = _require_text(args[index], "object")
        if key in result:
            raise EvaluationError(
                f"object() duplicate key {key!r}"
            )
        result[key] = args[index + 1]
    return result


_MISSING = object()


def _get(args: tuple[Value, ...]) -> Value:
    container = args[0]
    key = args[1]
    default: Value | object = args[2] if len(args) == 3 else _MISSING

    if isinstance(container, dict):
        text_key = _require_text(key, "get")
        if text_key in container:
            return container[text_key]
    elif isinstance(container, tuple):
        index = _require_number(key, "get")
        if not isinstance(index, int):
            raise EvaluationError("get() list index must be an integer")
        if 0 <= index < len(container):
            return container[index]
    else:
        raise EvaluationError(
            "get() expects an object or list as its first argument"
        )

    if default is not _MISSING:
        return default
    raise EvaluationError(f"get() key or index not found: {key!r}")


def _has(args: tuple[Value, ...]) -> Value:
    container = args[0]
    key = args[1]

    if isinstance(container, dict):
        return _require_text(key, "has") in container
    if isinstance(container, tuple):
        index = _require_number(key, "has")
        if not isinstance(index, int):
            raise EvaluationError("has() list index must be an integer")
        return 0 <= index < len(container)
    raise EvaluationError(
        "has() expects an object or list as its first argument"
    )


def _keys(args: tuple[Value, ...]) -> Value:
    value = args[0]
    if not isinstance(value, dict):
        raise EvaluationError("keys() expects an object")
    return tuple(value.keys())


def _values(args: tuple[Value, ...]) -> Value:
    value = args[0]
    if not isinstance(value, dict):
        raise EvaluationError("values() expects an object")
    return tuple(value.values())


def _size(args: tuple[Value, ...]) -> Value:
    value = args[0]
    if not isinstance(value, (str, tuple, dict)):
        raise EvaluationError(
            "size() expects a string, list, or object"
        )
    return len(value)


def _all(args: tuple[Value, ...]) -> Value:
    value = args[0]
    if not isinstance(value, tuple):
        raise EvaluationError("all() expects a list")
    if not all(isinstance(item, bool) for item in value):
        raise EvaluationError("all() expects a list of booleans")
    return all(value)


def _any(args: tuple[Value, ...]) -> Value:
    value = args[0]
    if not isinstance(value, tuple):
        raise EvaluationError("any() expects a list")
    if not all(isinstance(item, bool) for item in value):
        raise EvaluationError("any() expects a list of booleans")
    return any(value)


BUILTINS: dict[str, BuiltinFunction] = {
    item.name: item
    for item in (
        BuiltinFunction("upper", "Uppercase a string.", 1, 1, _upper),
        BuiltinFunction("lower", "Lowercase a string.", 1, 1, _lower),
        BuiltinFunction("trim", "Trim surrounding whitespace.", 1, 1, _trim),
        BuiltinFunction("length", "Return string length.", 1, 1, _length),
        BuiltinFunction("concat", "Concatenate values using stable text serialization.", 1, None, _concat),
        BuiltinFunction("contains", "Test whether text contains a substring.", 2, 2, _contains),
        BuiltinFunction("starts_with", "Test a string prefix.", 2, 2, _starts_with),
        BuiltinFunction("ends_with", "Test a string suffix.", 2, 2, _ends_with),
        BuiltinFunction("capitalize", "Capitalize text.", 1, 1, _capitalize),
        BuiltinFunction("title", "Convert text to title case.", 1, 1, _title),
        BuiltinFunction("replace", "Replace text deterministically.", 3, 3, _replace),
        BuiltinFunction("repeat", "Repeat text a bounded number of times.", 2, 2, _repeat),
        BuiltinFunction("clamp", "Clamp a number to an inclusive range.", 3, 3, _clamp),
        BuiltinFunction("between", "Test an inclusive numeric range.", 3, 3, _between),
        BuiltinFunction("if_else", "Select one of two deterministic values.", 3, 3, _if_else),
        BuiltinFunction("all_true", "Return true when every boolean argument is true.", 1, None, _all_true),
        BuiltinFunction("any_true", "Return true when any boolean argument is true.", 1, None, _any_true),
        BuiltinFunction("count_true", "Count true boolean arguments.", 1, None, _count_true),
        BuiltinFunction("average", "Return the arithmetic mean of numeric arguments.", 1, None, _average),
        BuiltinFunction("percent", "Return value as a percentage of total.", 2, 2, _percent),
        BuiltinFunction("coalesce", "Return the first non-null value.", 1, None, _coalesce),
        BuiltinFunction("abs", "Return absolute numeric value.", 1, 1, _abs),
        BuiltinFunction("round", "Round a number, optionally to digits.", 1, 2, _round),
        BuiltinFunction("min", "Return the minimum numeric value.", 1, None, _min),
        BuiltinFunction("max", "Return the maximum numeric value.", 1, None, _max),
        BuiltinFunction("string", "Convert a value to stable text.", 1, 1, _string),
        BuiltinFunction("number", "Convert text to a number.", 1, 1, _number),
        BuiltinFunction("boolean", "Convert a scalar to boolean.", 1, 1, _boolean),
        BuiltinFunction("list", "Create an immutable ordered list value.", 0, None, _list),
        BuiltinFunction("object", "Create an object from alternating string keys and values.", 0, None, _object),
        BuiltinFunction("get", "Read an object key or list index, optionally with a default.", 2, 3, _get),
        BuiltinFunction("has", "Test whether an object key or list index exists.", 2, 2, _has),
        BuiltinFunction("keys", "Return object keys in deterministic construction order.", 1, 1, _keys),
        BuiltinFunction("values", "Return object values in deterministic construction order.", 1, 1, _values),
        BuiltinFunction("size", "Return the size of a string, list, or object.", 1, 1, _size),
        BuiltinFunction("all", "Return true when every boolean in a list is true.", 1, 1, _all),
        BuiltinFunction("any", "Return true when any boolean in a list is true.", 1, 1, _any),
    )
}


def builtin_manifest() -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "name": item.name,
            "description": item.description,
            "min_args": item.min_args,
            "max_args": item.max_args,
        }
        for item in sorted(BUILTINS.values(), key=lambda item: item.name)
    )


def evaluate_expression(
    expression: Expression,
    values: Mapping[str, Value] | None = None,
) -> Value:
    """Evaluate one pure expression using an explicit value environment."""
    env = values or {}

    if isinstance(expression, StringLiteral):
        return expression.value
    if isinstance(expression, NumberLiteral):
        return expression.value
    if isinstance(expression, BooleanLiteral):
        return expression.value
    if isinstance(expression, ListLiteral):
        return tuple(
            evaluate_expression(item, env)
            for item in expression.items
        )
    if isinstance(expression, ObjectLiteral):
        result: dict[str, Value] = {}
        for key, item in expression.entries:
            if key in result:
                raise EvaluationError(
                    f"Duplicate object member {key!r}"
                )
            result[key] = evaluate_expression(
                item,
                env,
            )
        return result
    if isinstance(expression, MemberAccess):
        target = evaluate_expression(
            expression.target,
            env,
        )
        if not isinstance(target, dict):
            raise EvaluationError(
                "member access expects an object value"
            )
        if expression.member not in target:
            raise EvaluationError(
                f"Object member {expression.member!r} does not exist"
            )
        return target[expression.member]
    if isinstance(expression, IndexAccess):
        target = evaluate_expression(
            expression.target,
            env,
        )
        index = evaluate_expression(
            expression.index,
            env,
        )
        if isinstance(target, tuple):
            if isinstance(index, bool) or not isinstance(index, int):
                raise EvaluationError(
                    "list index must be an integer"
                )
            if not -len(target) <= index < len(target):
                raise EvaluationError(
                    f"list index out of range: {index}"
                )
            return target[index]
        if isinstance(target, dict):
            if not isinstance(index, str):
                raise EvaluationError(
                    "object index must be a string"
                )
            if index not in target:
                raise EvaluationError(
                    f"Object member {index!r} does not exist"
                )
            return target[index]
        raise EvaluationError(
            "index access expects a list or object value"
        )
    if isinstance(expression, Reference):
        if expression.name not in env:
            raise EvaluationError(
                f"Reference {expression.name!r} has no runtime value"
            )
        return env[expression.name]
    if isinstance(expression, CallExpression):
        function = BUILTINS.get(expression.name)
        if function is None:
            raise EvaluationError(
                f"Unknown built-in function {expression.name!r}"
            )
        function.validate_arity(len(expression.arguments))
        arguments = tuple(
            evaluate_expression(argument, env)
            for argument in expression.arguments
        )
        return function.handler(arguments)
    if isinstance(expression, UnaryExpression):
        value = evaluate_expression(expression.operand, env)
        if expression.operator == "!":
            if not isinstance(value, bool):
                raise EvaluationError("'!' expects a boolean operand")
            return not value
        if expression.operator in {"+", "-"}:
            number = _require_number(value, expression.operator)
            return +number if expression.operator == "+" else -number
        raise EvaluationError(f"Unsupported unary operator {expression.operator!r}")
    if isinstance(expression, BinaryExpression):
        left = evaluate_expression(expression.left, env)
        right = evaluate_expression(expression.right, env)
        operator = expression.operator

        if operator == "&&":
            if not isinstance(left, bool) or not isinstance(right, bool):
                raise EvaluationError("'&&' expects boolean operands")
            return left and right
        if operator == "||":
            if not isinstance(left, bool) or not isinstance(right, bool):
                raise EvaluationError("'||' expects boolean operands")
            return left or right
        if operator in {"==", "!="}:
            result = left == right
            return result if operator == "==" else not result
        if operator in {">", ">=", "<", "<="}:
            scalar_comparable = (
                isinstance(left, str)
                and isinstance(right, str)
            )
            numeric_comparable = (
                isinstance(left, (int, float))
                and not isinstance(left, bool)
                and isinstance(right, (int, float))
                and not isinstance(right, bool)
            )
            if not (scalar_comparable or numeric_comparable):
                raise EvaluationError(
                    f"{operator!r} expects string or numeric operands"
                )
            if operator == ">":
                return left > right
            if operator == ">=":
                return left >= right
            if operator == "<":
                return left < right
            return left <= right
        if operator == "+":
            if isinstance(left, str) and isinstance(right, str):
                return left + right
            return _require_number(left, "+") + _require_number(right, "+")
        if operator == "-":
            return _require_number(left, "-") - _require_number(right, "-")
        if operator == "*":
            return _require_number(left, "*") * _require_number(right, "*")
        if operator == "/":
            divisor = _require_number(right, "/")
            if divisor == 0:
                raise EvaluationError("division by zero")
            return _require_number(left, "/") / divisor
        if operator == "%":
            divisor = _require_number(right, "%")
            if divisor == 0:
                raise EvaluationError("modulo by zero")
            return _require_number(left, "%") % divisor

        raise EvaluationError(f"Unsupported binary operator {operator!r}")

    raise EvaluationError(
        f"Unsupported expression type {type(expression).__name__}"
    )
