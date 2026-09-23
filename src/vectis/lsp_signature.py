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

    parameters = _workspace_parameters(
        workspace,
        name,
    )
    if parameters is None:
        for candidate in (
            source,
            *tuple(supplemental_sources),
        ):
            parameters = _source_parameters(
                candidate,
                name,
            )
            if parameters is not None:
                break

    if parameters is None:
        return None

    return _user_help(
        name,
        parameters,
        argument_index,
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


def _workspace_parameters(
    workspace: WorkspaceProgram | None,
    name: str,
) -> tuple[str, ...] | None:
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
    return (
        declaration.parameters
        if declaration is not None
        else None
    )


def _source_parameters(
    source: str,
    name: str,
) -> tuple[str, ...] | None:
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
        cursor = index + 3
        expect_parameter = True

        while cursor < len(tokens):
            token = tokens[cursor]

            if (
                token.type == "punctuation"
                and token.value == ")"
            ):
                return tuple(parameters)

            if expect_parameter:
                if token.type != "identifier":
                    break
                parameters.append(token.value)
                expect_parameter = False
                cursor += 1
                continue

            if (
                token.type == "punctuation"
                and token.value == ","
            ):
                expect_parameter = True
                cursor += 1
                continue

            break

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
) -> dict[str, object]:
    signature: dict[str, object] = {
        "label": (
            f"{name}({', '.join(parameters)})"
        ),
        "documentation": (
            "User-defined pure VECTIS function."
        ),
        "parameters": [
            {"label": parameter}
            for parameter in parameters
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
