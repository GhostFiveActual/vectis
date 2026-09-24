# GHOST FIVE // VECTIS
# Builds deterministic LSP signature help from canonical language metadata.
"""Signature help for built-in and user-defined VECTIS pure functions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from vectis.ast import FunctionDeclaration
from vectis.diagnostic import DiagnosticError
from vectis.evaluator import builtin_manifest
from vectis.lexer import Lexer
from vectis.lsp_position import lsp_position_to_offset
from vectis.lsp_workspace import WorkspaceProgram


@dataclass(slots=True)
class _Frame:
    delimiter: str
    index: int
    commas: int = 0


def signature_help(
    source: str,
    *,
    line: int,
    character: int,
    workspace: WorkspaceProgram | None = None,
    supplemental_sources: Iterable[str] = (),
) -> dict[str, object] | None:
    """Return LSP SignatureHelp for the active pure-function call."""
    offset = _position_offset(
        source,
        line,
        character,
    )
    if offset is None:
        return None

    active = _active_call(
        source,
        offset,
    )
    if active is None:
        return None

    name, argument_index = active

    builtin = next(
        (
            item
            for item in builtin_manifest()
            if item["name"] == name
        ),
        None,
    )
    if builtin is not None:
        return _builtin_help(
            builtin,
            argument_index,
        )

    signature = _workspace_signature(
        workspace,
        name,
    )
    if signature is None:
        for candidate in (
            source,
            *tuple(supplemental_sources),
        ):
            signature = _source_signature(
                candidate,
                name,
            )
            if signature is not None:
                break

    if signature is None:
        return None

    parameters, parameter_types, return_type = signature
    return _user_help(
        name,
        parameters,
        argument_index,
        parameter_types=parameter_types,
        return_type=return_type,
    )


def _position_offset(
    source: str,
    line: int,
    character: int,
) -> int | None:
    return lsp_position_to_offset(
        source,
        line,
        character,
    )


def _active_call(
    source: str,
    offset: int,
) -> tuple[str, int] | None:
    frames: list[_Frame] = []
    in_string = False
    escaped = False
    in_comment = False
    index = 0
    matching = {
        ")": "(",
        "]": "[",
        "}": "{",
    }

    while index < offset:
        char = source[index]

        if in_comment:
            if char == "\n":
                in_comment = False
            index += 1
            continue

        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue

        if (
            char == "/"
            and index + 1 < offset
            and source[index + 1] == "/"
        ):
            in_comment = True
            index += 2
            continue

        if char == '"':
            in_string = True
            index += 1
            continue

        if char in "([{":
            frames.append(
                _Frame(
                    delimiter=char,
                    index=index,
                )
            )
            index += 1
            continue

        if char in ")]}":
            expected = matching[char]
            if (
                frames
                and frames[-1].delimiter == expected
            ):
                frames.pop()
            index += 1
            continue

        if (
            char == ","
            and frames
            and frames[-1].delimiter == "("
        ):
            frames[-1].commas += 1

        index += 1

    frame = next(
        (
            item
            for item in reversed(frames)
            if item.delimiter == "("
        ),
        None,
    )
    if frame is None:
        return None

    import re

    match = re.search(
        r"([A-Za-z_][A-Za-z0-9_]*)\s*$",
        source[: frame.index],
    )
    if match is None:
        return None

    return (
        match.group(1),
        frame.commas,
    )


def _workspace_signature(
    workspace: WorkspaceProgram | None,
    name: str,
) -> tuple[
    tuple[str, ...],
    tuple[str | None, ...],
    str | None,
] | None:
    if workspace is None:
        return None

    declaration = next(
        (
            statement
            for statement in workspace.program.statements
            if (
                isinstance(
                    statement,
                    FunctionDeclaration,
                )
                and statement.name == name
            )
        ),
        None,
    )
    if declaration is None:
        return None

    parameter_types = (
        declaration.parameter_types
        if declaration.parameter_types
        else tuple(None for _parameter in declaration.parameters)
    )
    return (
        declaration.parameters,
        parameter_types,
        declaration.return_type,
    )


def _consume_type_annotation(
    tokens: list[object],
    cursor: int,
) -> tuple[str, int] | None:
    if (
        cursor >= len(tokens)
        or getattr(tokens[cursor], "type", None) != "identifier"
    ):
        return None

    name = str(getattr(tokens[cursor], "value", ""))
    cursor += 1

    if (
        cursor < len(tokens)
        and getattr(tokens[cursor], "type", None) == "punctuation"
        and getattr(tokens[cursor], "value", None) == "["
    ):
        nested = _consume_type_annotation(tokens, cursor + 1)
        if nested is None:
            return None
        item, cursor = nested
        if not (
            cursor < len(tokens)
            and getattr(tokens[cursor], "type", None) == "punctuation"
            and getattr(tokens[cursor], "value", None) == "]"
        ):
            return None
        return f"{name}[{item}]", cursor + 1

    if (
        name == "object"
        and cursor + 1 < len(tokens)
        and getattr(tokens[cursor], "type", None) == "punctuation"
        and getattr(tokens[cursor], "value", None) == "{"
        and getattr(tokens[cursor + 1], "type", None) == "identifier"
    ):
        cursor += 1
        fields: list[str] = []
        if (
            cursor < len(tokens)
            and getattr(tokens[cursor], "type", None) == "punctuation"
            and getattr(tokens[cursor], "value", None) == "}"
        ):
            return f"{name}{{}}", cursor + 1

        while cursor < len(tokens):
            if getattr(tokens[cursor], "type", None) != "identifier":
                return None
            field_name = str(getattr(tokens[cursor], "value", ""))
            cursor += 1
            if not (
                cursor < len(tokens)
                and getattr(tokens[cursor], "type", None) == "punctuation"
                and getattr(tokens[cursor], "value", None) == ":"
            ):
                return None
            nested = _consume_type_annotation(tokens, cursor + 1)
            if nested is None:
                return None
            field_type, cursor = nested
            fields.append(f"{field_name}:{field_type}")

            if (
                cursor < len(tokens)
                and getattr(tokens[cursor], "type", None) == "punctuation"
                and getattr(tokens[cursor], "value", None) == "}"
            ):
                return f"{name}{{{','.join(fields)}}}", cursor + 1
            if not (
                cursor < len(tokens)
                and getattr(tokens[cursor], "type", None) == "punctuation"
                and getattr(tokens[cursor], "value", None) == ","
            ):
                return None
            cursor += 1

        return None

    return name, cursor


def _source_signature(
    source: str,
    name: str,
) -> tuple[
    tuple[str, ...],
    tuple[str | None, ...],
    str | None,
] | None:
    try:
        tokens = Lexer(source).tokenize()
    except DiagnosticError:
        return None

    for index in range(len(tokens)):
        if not (
            tokens[index].type == "keyword"
            and tokens[index].value == "function"
        ):
            continue

        if index + 2 >= len(tokens):
            continue

        function_name = tokens[index + 1]
        opening = tokens[index + 2]
        if not (
            function_name.type == "identifier"
            and function_name.value == name
            and opening.type == "punctuation"
            and opening.value == "("
        ):
            continue

        parameters: list[str] = []
        parameter_types: list[str | None] = []
        cursor = index + 3
        valid = True

        while cursor < len(tokens):
            token = tokens[cursor]
            if token.type == "punctuation" and token.value == ")":
                cursor += 1
                break
            if token.type != "identifier":
                valid = False
                break

            parameters.append(token.value)
            cursor += 1
            annotation = None

            if (
                cursor < len(tokens)
                and tokens[cursor].type == "punctuation"
                and tokens[cursor].value == ":"
            ):
                parsed = _consume_type_annotation(tokens, cursor + 1)
                if parsed is None:
                    valid = False
                    break
                annotation, cursor = parsed

            parameter_types.append(annotation)

            if (
                cursor < len(tokens)
                and tokens[cursor].type == "punctuation"
                and tokens[cursor].value == ","
            ):
                cursor += 1
                continue
            if (
                cursor < len(tokens)
                and tokens[cursor].type == "punctuation"
                and tokens[cursor].value == ")"
            ):
                cursor += 1
                break
            valid = False
            break

        if not valid or len(parameters) != len(parameter_types):
            continue

        return_type = None
        if (
            cursor < len(tokens)
            and tokens[cursor].type == "punctuation"
            and tokens[cursor].value == ":"
        ):
            parsed = _consume_type_annotation(tokens, cursor + 1)
            if parsed is None:
                continue
            return_type, cursor = parsed

        return (
            tuple(parameters),
            tuple(parameter_types),
            return_type,
        )

    return None


def _builtin_help(
    builtin: dict[str, object],
    argument_index: int,
) -> dict[str, object]:
    name = str(builtin["name"])
    minimum = int(builtin["min_args"])
    maximum_raw = builtin["max_args"]
    maximum = (
        int(maximum_raw)
        if maximum_raw is not None
        else None
    )

    labels: list[str] = []
    if maximum is None:
        labels.extend(
            f"arg{index + 1}"
            for index in range(minimum)
        )
        labels.append("...")
    else:
        for index in range(maximum):
            label = f"arg{index + 1}"
            if index >= minimum:
                label = f"[{label}]"
            labels.append(label)

    signature: dict[str, object] = {
        "label": (
            f"{name}({', '.join(labels)})"
        ),
        "documentation": str(
            builtin["description"]
        ),
        "parameters": [
            {"label": label}
            for label in labels
        ],
    }

    result: dict[str, object] = {
        "signatures": [signature],
        "activeSignature": 0,
    }

    if labels:
        if maximum is None:
            active_parameter = min(
                argument_index,
                len(labels) - 1,
            )
        else:
            active_parameter = min(
                argument_index,
                maximum - 1,
            )
        result["activeParameter"] = (
            active_parameter
        )

    return result


def _user_help(
    name: str,
    parameters: tuple[str, ...],
    argument_index: int,
    *,
    parameter_types: tuple[str | None, ...],
    return_type: str | None,
) -> dict[str, object]:
    labels = tuple(
        (
            parameter
            if annotation is None
            else f"{parameter}: {annotation}"
        )
        for parameter, annotation in zip(
            parameters,
            parameter_types,
            strict=True,
        )
    )
    result_suffix = (
        ""
        if return_type is None
        else f": {return_type}"
    )
    documentation = "User-defined pure VECTIS function."
    if return_type is not None:
        documentation += f" Declared return type: {return_type}."

    signature: dict[str, object] = {
        "label": f"{name}({', '.join(labels)}){result_suffix}",
        "documentation": documentation,
        "parameters": [
            {"label": label}
            for label in labels
        ],
    }

    result: dict[str, object] = {
        "signatures": [signature],
        "activeSignature": 0,
    }
    if parameters:
        result["activeParameter"] = min(
            argument_index,
            len(parameters) - 1,
        )
    return result
