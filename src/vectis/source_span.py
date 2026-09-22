# GHOST FIVE // VECTIS
# Represents a source range used by tokens, syntax nodes, and diagnostics.
"""Source spans used by VECTIS diagnostics and tokens."""

from dataclasses import dataclass

from vectis.source_position import SourcePosition


@dataclass(frozen=True, slots=True)
class SourceSpan:
    """A closed source range between two positions."""

    start: SourcePosition
    end: SourcePosition

    def __post_init__(self) -> None:
        if not isinstance(self.start, SourcePosition):
            raise ValueError("start must be a SourcePosition")

        if not isinstance(self.end, SourcePosition):
            raise ValueError("end must be a SourcePosition")

        if self.start.file != self.end.file:
            raise ValueError(
                "source span positions must reference the same file"
            )

        if (
            self.end.line,
            self.end.column,
        ) < (
            self.start.line,
            self.start.column,
        ):
            raise ValueError(
                "source span end must not precede start"
            )

    @property
    def file(self) -> str:
        """Return the source file shared by both positions."""
        return self.start.file
