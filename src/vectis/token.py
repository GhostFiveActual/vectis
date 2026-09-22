# GHOST FIVE // VECTIS
# Defines immutable VECTIS tokens with deterministic source spans.
"""Token primitives shared by VECTIS compiler stages."""

from dataclasses import dataclass

from vectis.source_span import SourceSpan


@dataclass(frozen=True, slots=True)
class Token:
    """A lexical token with its exact source location."""

    type: str
    value: str
    span: SourceSpan

    def __post_init__(self) -> None:
        if not isinstance(self.type, str) or not self.type:
            raise ValueError("token type must be a non-empty string")

        if not isinstance(self.value, str):
            raise ValueError("token value must be a string")

        if not isinstance(self.span, SourceSpan):
            raise ValueError("token span must be a SourceSpan")
