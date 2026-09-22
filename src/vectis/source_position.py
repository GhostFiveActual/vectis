# GHOST FIVE // VECTIS
# Represents one exact source position used by VECTIS diagnostics.
"""Source positions used by the VECTIS compiler."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourcePosition:
    """A 1-based position in a VECTIS source file."""

    line: int
    column: int
    file: str

    def __post_init__(self) -> None:
        if self.line < 1:
            raise ValueError("line must be >= 1")

        if self.column < 1:
            raise ValueError("column must be >= 1")

        if not isinstance(self.file, str) or not self.file:
            raise ValueError("file must be a non-empty string")
