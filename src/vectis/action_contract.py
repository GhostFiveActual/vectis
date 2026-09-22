# GHOST FIVE // VECTIS
# Defines deterministic input and result schemas for explicit action operations.
"""Typed action contracts for VECTIS."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from vectis.evaluator import Value


class ActionContractError(ValueError):
    """Raised when an action value violates its declared contract."""


class ActionValueType(str, Enum):
    """Value categories understood by action contracts."""

    ANY = "any"
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    LIST = "list"
    OBJECT = "object"


@dataclass(frozen=True, slots=True)
class ValueSchema:
    """Recursive schema for one VECTIS action value."""

    value_type: ActionValueType = ActionValueType.ANY
    item: "ValueSchema | None" = None
    fields: tuple["FieldSchema", ...] = ()
    values: "ValueSchema | None" = None
    allow_extra_fields: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.value_type, ActionValueType):
            raise TypeError(
                "ValueSchema.value_type must be ActionValueType"
            )
        if self.item is not None and not isinstance(
            self.item,
            ValueSchema,
        ):
            raise TypeError(
                "ValueSchema.item must be ValueSchema or None"
            )
        if not isinstance(self.fields, tuple) or not all(
            isinstance(field, FieldSchema)
            for field in self.fields
        ):
            raise TypeError(
                "ValueSchema.fields must contain FieldSchema values"
            )
        if self.values is not None and not isinstance(
            self.values,
            ValueSchema,
        ):
            raise TypeError(
                "ValueSchema.values must be ValueSchema or None"
            )
        if not isinstance(self.allow_extra_fields, bool):
            raise TypeError(
                "ValueSchema.allow_extra_fields must be bool"
            )
        if (
            self.value_type is not ActionValueType.LIST
            and self.item is not None
        ):
            raise ValueError(
                "Only list schemas may declare item"
            )
        if (
            self.value_type is not ActionValueType.OBJECT
            and (self.fields or self.values is not None)
        ):
            raise ValueError(
                "Only object schemas may declare fields or values"
            )

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "type": self.value_type.value,
        }
        if self.item is not None:
            payload["items"] = self.item.to_dict()
        if self.fields:
            payload["fields"] = [
                field.to_dict()
                for field in self.fields
            ]
            payload["allow_extra_fields"] = (
                self.allow_extra_fields
            )
        elif self.value_type is ActionValueType.OBJECT:
            payload["allow_extra_fields"] = (
                self.allow_extra_fields
            )
        if self.values is not None:
            payload["values"] = self.values.to_dict()
        return payload


@dataclass(frozen=True, slots=True)
class FieldSchema:
    """Named object member contract."""

    name: str
    schema: ValueSchema
    required: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError(
                "FieldSchema.name must be a non-empty string"
            )
        if not isinstance(self.schema, ValueSchema):
            raise TypeError(
                "FieldSchema.schema must be ValueSchema"
            )
        if not isinstance(self.required, bool):
            raise TypeError(
                "FieldSchema.required must be bool"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "required": self.required,
            "schema": self.schema.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class ActionContract:
    """Input, result, and authority contract for one operation."""

    operation: str
    capability: str
    input_schema: ValueSchema
    result_schema: ValueSchema
    description: str

    def __post_init__(self) -> None:
        if not isinstance(self.operation, str) or not self.operation:
            raise ValueError(
                "ActionContract.operation must be non-empty"
            )
        if not isinstance(self.capability, str) or not self.capability:
            raise ValueError(
                "ActionContract.capability must be non-empty"
            )
        if not isinstance(self.input_schema, ValueSchema):
            raise TypeError(
                "ActionContract.input_schema must be ValueSchema"
            )
        if not isinstance(self.result_schema, ValueSchema):
            raise TypeError(
                "ActionContract.result_schema must be ValueSchema"
            )
        if not isinstance(self.description, str) or not self.description:
            raise ValueError(
                "ActionContract.description must be non-empty"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "operation": self.operation,
            "capability": self.capability,
            "description": self.description,
            "input": self.input_schema.to_dict(),
            "result": self.result_schema.to_dict(),
        }


ANY = ValueSchema()
STRING = ValueSchema(ActionValueType.STRING)
NUMBER = ValueSchema(ActionValueType.NUMBER)
BOOLEAN = ValueSchema(ActionValueType.BOOLEAN)
STRING_LIST = ValueSchema(
    ActionValueType.LIST,
    item=STRING,
)
STRING_MAP = ValueSchema(
    ActionValueType.OBJECT,
    values=STRING,
    allow_extra_fields=True,
)


def object_schema(
    *fields: FieldSchema,
    allow_extra_fields: bool = False,
) -> ValueSchema:
    """Create a fixed object schema with deterministic field order."""
    return ValueSchema(
        ActionValueType.OBJECT,
        fields=tuple(fields),
        allow_extra_fields=allow_extra_fields,
    )


STANDARD_ACTION_CONTRACTS: tuple[ActionContract, ...] = (
    ActionContract(
        operation="filesystem.read_text",
        capability="filesystem",
        description=(
            "Read UTF-8 text inside an explicitly configured "
            "filesystem root."
        ),
        input_schema=object_schema(
            FieldSchema("path", STRING),
        ),
        result_schema=STRING,
    ),
    ActionContract(
        operation="filesystem.write_text",
        capability="filesystem",
        description=(
            "Write UTF-8 text inside an explicitly configured "
            "filesystem root."
        ),
        input_schema=object_schema(
            FieldSchema("path", STRING),
            FieldSchema("content", STRING),
        ),
        result_schema=object_schema(
            FieldSchema("path", STRING),
            FieldSchema("written", BOOLEAN),
            FieldSchema("characters", NUMBER),
        ),
    ),
    ActionContract(
        operation="process.run",
        capability="process",
        description=(
            "Run one allowlisted executable with structured "
            "arguments."
        ),
        input_schema=object_schema(
            FieldSchema("executable", STRING),
            FieldSchema(
                "arguments",
                STRING_LIST,
                required=False,
            ),
            FieldSchema(
                "timeout",
                NUMBER,
                required=False,
            ),
        ),
        result_schema=object_schema(
            FieldSchema("argv", STRING_LIST),
            FieldSchema("returncode", NUMBER),
            FieldSchema("stdout", STRING),
            FieldSchema("stderr", STRING),
        ),
    ),
    ActionContract(
        operation="http.request",
        capability="http",
        description=(
            "Perform one bounded HTTP request through the "
            "configured adapter."
        ),
        input_schema=object_schema(
            FieldSchema("method", STRING),
            FieldSchema("url", STRING),
            FieldSchema(
                "headers",
                STRING_MAP,
                required=False,
            ),
            FieldSchema(
                "timeout",
                NUMBER,
                required=False,
            ),
            FieldSchema(
                "body",
                STRING,
                required=False,
            ),
            FieldSchema(
                "json",
                ANY,
                required=False,
            ),
        ),
        result_schema=object_schema(
            FieldSchema("url", STRING),
            FieldSchema("status", NUMBER),
            FieldSchema("reason", STRING),
            FieldSchema(
                "headers",
                ValueSchema(
                    ActionValueType.LIST,
                    item=object_schema(
                        FieldSchema("name", STRING),
                        FieldSchema("value", STRING),
                    ),
                ),
            ),
            FieldSchema("body", STRING),
            FieldSchema("ok", BOOLEAN),
        ),
    ),
)

_STANDARD_BY_OPERATION = {
    contract.operation: contract
    for contract in STANDARD_ACTION_CONTRACTS
}


def standard_action_contract(
    operation: str,
) -> ActionContract | None:
    """Return the standard contract for one operation."""
    if not isinstance(operation, str) or not operation:
        raise ValueError(
            "operation must be a non-empty string"
        )
    return _STANDARD_BY_OPERATION.get(operation)


def standard_action_manifest(
) -> tuple[dict[str, object], ...]:
    """Return serializable standard contracts in stable order."""
    return tuple(
        contract.to_dict()
        for contract in STANDARD_ACTION_CONTRACTS
    )


def validate_value(
    schema: ValueSchema,
    value: Value,
    *,
    path: str,
) -> None:
    """Validate one runtime value against a recursive schema."""
    if not isinstance(schema, ValueSchema):
        raise TypeError("schema must be ValueSchema")
    _validate_value(
        schema,
        value,
        path=path,
    )


def _validate_value(
    schema: ValueSchema,
    value: Value,
    *,
    path: str,
) -> None:
    expected = schema.value_type

    if expected is ActionValueType.ANY:
        return
    if expected is ActionValueType.STRING:
        if not isinstance(value, str):
            _mismatch(path, "string", value)
        return
    if expected is ActionValueType.NUMBER:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
        ):
            _mismatch(path, "number", value)
        return
    if expected is ActionValueType.BOOLEAN:
        if not isinstance(value, bool):
            _mismatch(path, "boolean", value)
        return
    if expected is ActionValueType.LIST:
        if not isinstance(value, tuple):
            _mismatch(path, "list", value)
        if schema.item is not None:
            for index, item in enumerate(value):
                _validate_value(
                    schema.item,
                    item,
                    path=f"{path}[{index}]",
                )
        return
    if expected is ActionValueType.OBJECT:
        if not isinstance(value, dict):
            _mismatch(path, "object", value)

        fields = {
            field.name: field
            for field in schema.fields
        }
        for field in schema.fields:
            if (
                field.required
                and field.name not in value
            ):
                raise ActionContractError(
                    f"{path} requires field {field.name!r}"
                )

        if fields and not schema.allow_extra_fields:
            unknown = sorted(
                set(value) - set(fields)
            )
            if unknown:
                raise ActionContractError(
                    f"{path} contains unsupported field(s): "
                    + ", ".join(unknown)
                )

        for name, item in value.items():
            field = fields.get(name)
            if field is not None:
                _validate_value(
                    field.schema,
                    item,
                    path=f"{path}.{name}",
                )
            elif schema.values is not None:
                _validate_value(
                    schema.values,
                    item,
                    path=f"{path}.{name}",
                )
        return

    raise AssertionError(
        f"Unhandled action value type: {expected}"
    )


def _mismatch(
    path: str,
    expected: str,
    value: object,
) -> None:
    actual = (
        "boolean"
        if isinstance(value, bool)
        else "number"
        if isinstance(value, (int, float))
        else "string"
        if isinstance(value, str)
        else "object"
        if isinstance(value, dict)
        else "list"
        if isinstance(value, tuple)
        else "null"
        if value is None
        else type(value).__name__
    )
    raise ActionContractError(
        f"{path} must be {expected}, not {actual}"
    )


__all__ = [
    "ActionContract",
    "ActionContractError",
    "ActionValueType",
    "FieldSchema",
    "STANDARD_ACTION_CONTRACTS",
    "ValueSchema",
    "standard_action_contract",
    "standard_action_manifest",
    "validate_value",
]
