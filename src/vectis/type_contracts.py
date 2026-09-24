# GHOST FIVE // VECTIS
# Parses deterministic pure-function type contract labels.
"""Pure-function type contract parsing for VECTIS."""

from __future__ import annotations

from dataclasses import dataclass


SUPPORTED_TYPE_NAMES = frozenset(
    {
        "string",
        "number",
        "boolean",
        "list",
        "object",
        "any",
    }
)


def _is_identifier(value: str) -> bool:
    if not value:
        return False
    if not (value[0].isalpha() or value[0] == "_"):
        return False
    return all(
        char.isalnum() or char == "_"
        for char in value[1:]
    )


@dataclass(frozen=True, slots=True)
class TypeContract:
    """One canonical compile-time type contract."""

    name: str
    item: "TypeContract | None" = None
    fields: tuple[tuple[str, "TypeContract"], ...] = ()

    def __post_init__(self) -> None:
        if self.name not in SUPPORTED_TYPE_NAMES:
            raise ValueError(f"unsupported type contract: {self.name}")
        if self.item is not None and not isinstance(self.item, TypeContract):
            raise TypeError("TypeContract.item must be TypeContract or None")
        if self.item is not None and self.name != "list":
            raise ValueError("only list contracts may contain an item contract")
        if self.fields and self.name != "object":
            raise ValueError("only object contracts may contain field contracts")
        if self.item is not None and self.fields:
            raise ValueError("type contract cannot contain list and object members")
        if not isinstance(self.fields, tuple):
            raise TypeError("TypeContract.fields must be tuple")

        seen: set[str] = set()
        for field_name, field_contract in self.fields:
            if not _is_identifier(field_name):
                raise ValueError("object contract field must be an identifier")
            if field_name in seen:
                raise ValueError(
                    f"duplicate object contract field: {field_name}"
                )
            if not isinstance(field_contract, TypeContract):
                raise TypeError(
                    "object contract fields must contain TypeContract values"
                )
            seen.add(field_name)

    def render(self) -> str:
        if self.item is not None:
            return f"{self.name}[{self.item.render()}]"
        if self.fields:
            rendered = ",".join(
                f"{name}:{contract.render()}"
                for name, contract in self.fields
            )
            return f"{self.name}{{{rendered}}}"
        return self.name

    def field(self, name: str) -> "TypeContract | None":
        for field_name, contract in self.fields:
            if field_name == name:
                return contract
        return None


@dataclass(frozen=True, slots=True)
class _TypeShape:
    name: str
    item: "_TypeShape | None" = None
    fields: tuple[tuple[str, "_TypeShape"], ...] | None = None


class _ShapeParser:
    def __init__(self, source: str) -> None:
        self.source = source
        self.index = 0

    def parse(self) -> _TypeShape | None:
        shape = self._parse_shape()
        if shape is None or self.index != len(self.source):
            return None
        return shape

    def _parse_shape(self) -> _TypeShape | None:
        name = self._identifier()
        if name is None:
            return None

        if self._consume("["):
            item = self._parse_shape()
            if item is None or not self._consume("]"):
                return None
            return _TypeShape(name=name, item=item)

        if self._consume("{"):
            fields: list[tuple[str, _TypeShape]] = []
            if self._consume("}"):
                return _TypeShape(name=name, fields=())

            while True:
                field_name = self._identifier()
                if field_name is None or not self._consume(":"):
                    return None
                field_contract = self._parse_shape()
                if field_contract is None:
                    return None
                fields.append((field_name, field_contract))

                if self._consume("}"):
                    break
                if not self._consume(","):
                    return None

            return _TypeShape(name=name, fields=tuple(fields))

        return _TypeShape(name=name)

    def _identifier(self) -> str | None:
        if self.index >= len(self.source):
            return None
        first = self.source[self.index]
        if not (first.isalpha() or first == "_"):
            return None
        start = self.index
        self.index += 1
        while self.index < len(self.source):
            char = self.source[self.index]
            if not (char.isalnum() or char == "_"):
                break
            self.index += 1
        return self.source[start:self.index]

    def _consume(self, value: str) -> bool:
        if self.source.startswith(value, self.index):
            self.index += len(value)
            return True
        return False


def is_type_contract_shape(source: str) -> bool:
    """Return whether source is a syntactically canonical type label."""
    if not isinstance(source, str) or not source:
        return False
    return _ShapeParser(source).parse() is not None


def _supported_contract(shape: _TypeShape) -> TypeContract | None:
    if shape.name not in SUPPORTED_TYPE_NAMES:
        return None

    if shape.item is not None:
        if shape.name != "list" or shape.fields is not None:
            return None
        item = _supported_contract(shape.item)
        if item is None:
            return None
        return TypeContract(name="list", item=item)

    if shape.fields is not None:
        if shape.name != "object" or not shape.fields:
            return None

        names = [name for name, _contract in shape.fields]
        if len(names) != len(set(names)):
            return None

        fields: list[tuple[str, TypeContract]] = []
        for field_name, field_shape in shape.fields:
            field_contract = _supported_contract(field_shape)
            if field_contract is None:
                return None
            fields.append((field_name, field_contract))
        return TypeContract(name="object", fields=tuple(fields))

    return TypeContract(name=shape.name)


def parse_type_contract(source: str) -> TypeContract | None:
    """Parse one supported type contract or return None when unsupported."""
    if not isinstance(source, str) or not source:
        return None
    shape = _ShapeParser(source).parse()
    if shape is None:
        return None
    return _supported_contract(shape)


__all__ = [
    "SUPPORTED_TYPE_NAMES",
    "TypeContract",
    "is_type_contract_shape",
    "parse_type_contract",
]
