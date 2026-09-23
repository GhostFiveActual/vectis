# GHOST FIVE // VECTIS
# Converts canonical VECTIS source positions to and from UTF-16 LSP coordinates.
"""Shared UTF-16 position and source span conversion for editor integrations."""

from __future__ import annotations

from vectis.source_position import SourcePosition
from vectis.source_span import SourceSpan


def utf16_units(text: str) -> int:
    """Return the number of UTF-16 code units required for text."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    return len(text.encode("utf-16-le")) // 2


def lsp_character_to_index(text: str, character: int) -> int | None:
    """Translate a zero-based UTF-16 LSP character to a Python string index."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if not isinstance(character, int) or character < 0:
        return None

    units = 0
    for index, value in enumerate(text):
        width = utf16_units(value)
        if character < units + width:
            return index
        units += width
        if character == units:
            return index + 1
    return len(text)


def lsp_position_to_offset(
    source: str,
    line: int,
    character: int,
) -> int | None:
    """Translate one LSP position into a Python source-string offset."""
    if not isinstance(source, str):
        raise TypeError("source must be a string")
    if not isinstance(line, int) or line < 0:
        return None

    starts = [0]
    for index, value in enumerate(source):
        if value == "\n":
            starts.append(index + 1)

    if line >= len(starts):
        return None

    start = starts[line]
    newline = source.find("\n", start)
    end = len(source) if newline == -1 else newline
    if end > start and source[end - 1] == "\r":
        end -= 1

    local = lsp_character_to_index(
        source[start:end],
        character,
    )
    if local is None:
        return None
    return start + local


def source_position_to_lsp(
    source: str,
    position: SourcePosition,
) -> dict[str, int]:
    """Translate one canonical one-based source position to LSP coordinates."""
    if not isinstance(position, SourcePosition):
        raise TypeError("position must be a SourcePosition")

    lines = source.split("\n")
    line = position.line - 1
    if line < 0 or line >= len(lines):
        raise ValueError("source position line is outside source text")

    text = lines[line]
    if text.endswith("\r"):
        text = text[:-1]
    index = position.column - 1
    if index < 0 or index > len(text):
        raise ValueError("source position column is outside source text")

    return {
        "line": line,
        "character": utf16_units(text[:index]),
    }


def source_span_to_lsp_range(
    source: str,
    span: SourceSpan,
) -> dict[str, dict[str, int]]:
    """Translate one closed canonical source span to an end-exclusive LSP range."""
    if not isinstance(span, SourceSpan):
        raise TypeError("span must be a SourceSpan")

    lines = source.split("\n")
    start_line = span.start.line - 1
    end_line = span.end.line - 1
    if (
        start_line < 0
        or end_line < 0
        or start_line >= len(lines)
        or end_line >= len(lines)
    ):
        raise ValueError("source span line is outside source text")

    start_text = lines[start_line]
    end_text = lines[end_line]
    if start_text.endswith("\r"):
        start_text = start_text[:-1]
    if end_text.endswith("\r"):
        end_text = end_text[:-1]

    start_index = span.start.column - 1
    end_index = span.end.column
    if start_index < 0 or start_index > len(start_text):
        raise ValueError("source span start column is outside source text")
    if end_index < 0 or end_index > len(end_text) + 1:
        raise ValueError("source span end column is outside source text")
    end_index = min(end_index, len(end_text))

    return {
        "start": {
            "line": start_line,
            "character": utf16_units(start_text[:start_index]),
        },
        "end": {
            "line": end_line,
            "character": utf16_units(end_text[:end_index]),
        },
    }


def contains_lsp_position(
    source: str,
    span: SourceSpan,
    *,
    line: int,
    character: int,
) -> bool:
    """Return whether an LSP position falls inside a canonical closed span."""
    if not isinstance(line, int) or not isinstance(character, int):
        return False
    if line < 0 or character < 0:
        return False

    converted = source_span_to_lsp_range(source, span)
    start = (
        converted["start"]["line"],
        converted["start"]["character"],
    )
    end = (
        converted["end"]["line"],
        converted["end"]["character"],
    )
    position = (line, character)
    return start <= position < end


__all__ = [
    "contains_lsp_position",
    "lsp_character_to_index",
    "lsp_position_to_offset",
    "source_position_to_lsp",
    "source_span_to_lsp_range",
    "utf16_units",
]
