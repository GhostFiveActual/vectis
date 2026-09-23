\
# GHOST FIVE // VECTIS
# Encodes deterministic LSP semantic tokens from the canonical VECTIS lexer.
"""Full-document semantic tokens for VECTIS editor integrations."""

from __future__ import annotations

from dataclasses import dataclass

from vectis.diagnostic import DiagnosticError
from vectis.lexer import Lexer
from vectis.lsp_position import utf16_units


SEMANTIC_TOKEN_TYPES = (
    "keyword",
    "string",
    "number",
    "operator",
    "function",
    "parameter",
    "variable",
    "property",
)
SEMANTIC_TOKEN_MODIFIERS = (
    "declaration",
)
SEMANTIC_TOKEN_LEGEND = {
    "tokenTypes": list(SEMANTIC_TOKEN_TYPES),
    "tokenModifiers": list(SEMANTIC_TOKEN_MODIFIERS),
}

_TYPE_INDEX = {
    name: index
    for index, name in enumerate(
        SEMANTIC_TOKEN_TYPES
    )
}
_DECLARATION = 1 << SEMANTIC_TOKEN_MODIFIERS.index(
    "declaration"
)


@dataclass(frozen=True, slots=True)
class _FunctionRegion:
    parameters: frozenset[str]
    start_index: int
    end_index: int


def semantic_tokens(
    source: str,
    *,
    file: str = "<memory>",
) -> dict[str, object]:
    """Return deterministic full-document LSP semantic tokens."""
    try:
        tokens = Lexer(
            source,
            file=file,
        ).tokenize()
    except DiagnosticError:
        return {"data": []}

    function_names, parameter_declarations, regions = (
        _function_context(tokens)
    )
    lines = source.split("\n")
    encoded: list[int] = []
    previous_line = 0
    previous_start = 0

    for index, token in enumerate(tokens):
        classification = _classification(
            tokens,
            index,
            function_names=function_names,
            parameter_declarations=(
                parameter_declarations
            ),
            regions=regions,
        )
        if classification is None:
            continue

        token_type, modifiers = classification

        for (
            line,
            start,
            length,
        ) in _segments(
            lines,
            token.span,
        ):
            if length <= 0:
                continue

            delta_line = (
                line - previous_line
            )
            delta_start = (
                start
                if delta_line
                else start - previous_start
            )

            encoded.extend(
                (
                    delta_line,
                    delta_start,
                    length,
                    _TYPE_INDEX[token_type],
                    modifiers,
                )
            )
            previous_line = line
            previous_start = start

    return {"data": encoded}


def _classification(
    tokens: list[object],
    index: int,
    *,
    function_names: frozenset[int],
    parameter_declarations: frozenset[int],
    regions: tuple[_FunctionRegion, ...],
) -> tuple[str, int] | None:
    token = tokens[index]
    token_type = getattr(
        token,
        "type",
        None,
    )
    value = getattr(
        token,
        "value",
        None,
    )

    if token_type == "keyword":
        return ("keyword", 0)
    if token_type == "string":
        return ("string", 0)
    if token_type == "number":
        return ("number", 0)
    if token_type == "operator":
        return ("operator", 0)
    if token_type != "identifier":
        return None

    if value in {"true", "false"}:
        return ("keyword", 0)

    if index in function_names:
        return (
            "function",
            _DECLARATION,
        )

    if index in parameter_declarations:
        return (
            "parameter",
            _DECLARATION,
        )

    region = next(
        (
            item
            for item in regions
            if (
                item.start_index
                <= index
                <= item.end_index
                and value
                in item.parameters
            )
        ),
        None,
    )
    if region is not None:
        return ("parameter", 0)

    previous = (
        tokens[index - 1]
        if index > 0
        else None
    )
    following = (
        tokens[index + 1]
        if index + 1 < len(tokens)
        else None
    )

    if (
        getattr(
            previous,
            "type",
            None,
        )
        == "punctuation"
        and getattr(
            previous,
            "value",
            None,
        )
        == "."
    ):
        return ("property", 0)

    if (
        getattr(
            following,
            "type",
            None,
        )
        == "punctuation"
        and getattr(
            following,
            "value",
            None,
        )
        == ":"
    ):
        return (
            "property",
            _DECLARATION,
        )

    if (
        getattr(
            following,
            "type",
            None,
        )
        == "punctuation"
        and getattr(
            following,
            "value",
            None,
        )
        == "("
    ):
        return ("function", 0)

    if (
        getattr(
            previous,
            "type",
            None,
        )
        == "keyword"
        and getattr(
            previous,
            "value",
            None,
        )
        in {
            "source",
            "let",
            "analyze",
            "action",
        }
    ):
        return (
            "variable",
            _DECLARATION,
        )

    return ("variable", 0)


def _function_context(
    tokens: list[object],
) -> tuple[
    frozenset[int],
    frozenset[int],
    tuple[_FunctionRegion, ...],
]:
    function_names: set[int] = set()
    parameter_declarations: set[int] = set()
    regions: list[_FunctionRegion] = []

    index = 0
    while index < len(tokens):
        token = tokens[index]
        if not (
            getattr(
                token,
                "type",
                None,
            )
            == "keyword"
            and getattr(
                token,
                "value",
                None,
            )
            == "function"
        ):
            index += 1
            continue

        name_index = index + 1
        opening_index = index + 2

        if (
            opening_index >= len(tokens)
            or getattr(
                tokens[name_index],
                "type",
                None,
            )
            != "identifier"
            or getattr(
                tokens[opening_index],
                "type",
                None,
            )
            != "punctuation"
            or getattr(
                tokens[opening_index],
                "value",
                None,
            )
            != "("
        ):
            index += 1
            continue

        function_names.add(
            name_index
        )
        parameters: set[str] = set()
        cursor = opening_index + 1
        closing_index = None
        expect_parameter = True

        while cursor < len(tokens):
            current = tokens[cursor]
            current_type = getattr(
                current,
                "type",
                None,
            )
            current_value = getattr(
                current,
                "value",
                None,
            )

            if (
                current_type
                == "punctuation"
                and current_value
                == ")"
            ):
                closing_index = cursor
                break

            if expect_parameter:
                if (
                    current_type
                    != "identifier"
                ):
                    break
                parameter_declarations.add(
                    cursor
                )
                parameters.add(
                    str(current_value)
                )
                expect_parameter = False
                cursor += 1
                continue

            if (
                current_type
                == "punctuation"
                and current_value
                == ","
            ):
                expect_parameter = True
                cursor += 1
                continue

            break

        if closing_index is None:
            index += 1
            continue

        body_open = closing_index + 1
        if not (
            body_open < len(tokens)
            and getattr(
                tokens[body_open],
                "type",
                None,
            )
            == "punctuation"
            and getattr(
                tokens[body_open],
                "value",
                None,
            )
            == "{"
        ):
            index += 1
            continue

        depth = 0
        body_close = len(tokens) - 1

        for cursor in range(
            body_open,
            len(tokens),
        ):
            current = tokens[cursor]
            if getattr(
                current,
                "type",
                None,
            ) != "punctuation":
                continue

            current_value = getattr(
                current,
                "value",
                None,
            )
            if current_value == "{":
                depth += 1
            elif current_value == "}":
                depth -= 1
                if depth == 0:
                    body_close = cursor
                    break

        regions.append(
            _FunctionRegion(
                parameters=frozenset(
                    parameters
                ),
                start_index=body_open + 1,
                end_index=max(
                    body_open,
                    body_close - 1,
                ),
            )
        )
        index = body_close + 1

    return (
        frozenset(function_names),
        frozenset(
            parameter_declarations
        ),
        tuple(regions),
    )


def _segments(
    lines: list[str],
    span: object,
):
    start_line = (
        span.start.line - 1
    )
    end_line = (
        span.end.line - 1
    )

    for line in range(
        start_line,
        end_line + 1,
    ):
        if (
            line < 0
            or line >= len(lines)
        ):
            continue

        text = lines[line]
        if text.endswith("\r"):
            text = text[:-1]

        start_index = (
            span.start.column - 1
            if line == start_line
            else 0
        )
        end_index = (
            span.end.column
            if line == end_line
            else len(text)
        )

        start_index = max(
            0,
            min(
                start_index,
                len(text),
            ),
        )
        end_index = max(
            start_index,
            min(
                end_index,
                len(text),
            ),
        )

        segment = text[
            start_index:end_index
        ]
        if not segment:
            continue

        yield (
            line,
            utf16_units(
                text[:start_index]
            ),
            utf16_units(
                segment
            ),
        )
