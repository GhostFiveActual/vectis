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


@dataclass(frozen=True, slots=True)
class TypeContract:
    """One canonical compile-time type contract."""

    name: str
    item: "TypeContract | None" = None

    def __post_init__(self) -> None:
        if self.name not in SUPPORTED_TYPE_NAMES:
            raise ValueError(f"unsupported type contract: {self.name}")
        if self.item is not None and self.name != "list":
            raise ValueError("only list contracts may contain an item contract")

    def render(self) -> str:
        if self.item is None:
            return self.name
        return f"{self.name}[{self.item.render()}]"


@dataclass(frozen=True, slots=True)
class _TypeShape:
    name: str
    item: "_TypeShape | None" = None


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
        item = None
        if self._consume("["):
            item = self._parse_shape()
            if item is None or not self._consume("]"):
                return None
        return _TypeShape(name=name, item=item)

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
    if shape.item is not None and shape.name != "list":
        return None
    item = None
    if shape.item is not None:
        item = _supported_contract(shape.item)
        if item is None:
            return None
    return TypeContract(name=shape.name, item=item)


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
