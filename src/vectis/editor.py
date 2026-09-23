# GHOST FIVE // VECTIS
# Builds deterministic editor intelligence from the VECTIS language registries and AST.
"""Editor-facing completion, hover, and document symbol helpers."""

from __future__ import annotations

import re

from vectis.actions import standard_action_manifest
from vectis.ast import (
    ActionStatement,
    AnalyzeDeclaration,
    Block,
    FunctionDeclaration,
    LetDeclaration,
    Mission,
    Program,
    SourceDeclaration,
    Stage,
    WhenStatement,
)
from vectis.evaluator import builtin_manifest
from vectis.lexer import KEYWORDS
from vectis.lsp_position import (
    lsp_character_to_index,
    source_span_to_lsp_range,
)
from vectis.parser import parse


_KEYWORD_HELP = {
    "mission": "Declare an executable VECTIS mission.",
    "stage": "Group mission statements under a named stage.",
    "source": "Declare an explicit source value.",
    "let": "Declare a deterministic computed value.",
    "analyze": "Declare an analysis value in the execution graph.",
    "when": "Execute a deterministic conditional branch.",
    "otherwise": "Declare the alternate branch of a when statement.",
    "publish": "Publish a value as a mission result.",
    "request": "Request a named capability without granting it.",
    "require": "Require a named capability for execution.",
    "assert": "Require a condition to be true, optionally with an explanation.",
    "citations": "Attach citation values to the execution plan.",
    "confidence": "Attach a confidence value to the execution plan.",
    "function": "Declare an authority-free deterministic pure function.",
    "return": "Return the expression value of a pure function.",
    "import": "Import pure declarations from a project-bounded VECTIS module.",
    "action": "Invoke an explicitly registered external operation.",
    "using": "Name the capability required by an action.",
}


def completion_items() -> list[dict[str, object]]:
    """Return stable LSP completion items from canonical VECTIS registries."""
    items: list[dict[str, object]] = []

    for keyword in sorted(KEYWORDS):
        items.append(
            {
                "label": keyword,
                "kind": 14,
                "detail": "VECTIS keyword",
                "documentation": _KEYWORD_HELP.get(
                    keyword,
                    "VECTIS language keyword.",
                ),
            }
        )

    for builtin in builtin_manifest():
        max_args = builtin["max_args"]
        arity = (
            f'{builtin["min_args"]}+ arguments'
            if max_args is None
            else (
                f'{builtin["min_args"]} arguments'
                if builtin["min_args"] == max_args
                else f'{builtin["min_args"]}-{max_args} arguments'
            )
        )
        items.append(
            {
                "label": builtin["name"],
                "kind": 3,
                "detail": f"VECTIS built-in function, {arity}",
                "documentation": builtin["description"],
                "insertText": f'{builtin["name"]}(',
            }
        )

    for action in standard_action_manifest():
        items.append(
            {
                "label": action["operation"],
                "kind": 12,
                "detail": (
                    "VECTIS standard action "
                    f'using capability {action["capability"]}'
                ),
                "documentation": (
                    "External work remains unavailable until the host "
                    "explicitly configures and grants this capability."
                ),
            }
        )

    return sorted(items, key=lambda item: str(item["label"]))


def _word_at(source: str, line: int, character: int) -> str | None:
    """Return the identifier-like token beneath one zero-based LSP position."""
    lines = source.splitlines()
    if line < 0 or line >= len(lines):
        return None

    text = lines[line]
    character_index = lsp_character_to_index(
        text,
        character,
    )
    if character_index is None:
        return None
    character = character_index

    for match in re.finditer(
        r"[A-Za-z_][A-Za-z0-9_]*"
        r"(?:\.[A-Za-z_][A-Za-z0-9_]*)*",
        text,
    ):
        if match.start() <= character <= match.end():
            return match.group(0)
    return None


def hover_info(
    source: str,
    *,
    line: int,
    character: int,
) -> dict[str, object] | None:
    """Return deterministic markdown hover information for one source position."""
    word = _word_at(source, line, character)
    if word is None:
        return None

    if word in KEYWORDS:
        return {
            "contents": {
                "kind": "markdown",
                "value": (
                    f"**{word}** — VECTIS keyword\n\n"
                    + _KEYWORD_HELP.get(
                        word,
                        "VECTIS language keyword.",
                    )
                ),
            }
        }

    builtins = {
        item["name"]: item
        for item in builtin_manifest()
    }
    builtin = builtins.get(word)
    if builtin is not None:
        max_args = builtin["max_args"]
        signature = (
            f'{word}({builtin["min_args"]}+ args)'
            if max_args is None
            else (
                f'{word}({builtin["min_args"]} args)'
                if builtin["min_args"] == max_args
                else f'{word}({builtin["min_args"]}..{max_args} args)'
            )
        )
        return {
            "contents": {
                "kind": "markdown",
                "value": (
                    f"**{signature}**\n\n"
                    f'{builtin["description"]}\n\n'
                    "Pure and deterministic."
                ),
            }
        }

    actions = {
        item["operation"]: item
        for item in standard_action_manifest()
    }
    action = actions.get(word)
    if action is not None:
        input_schema = action["input"]
        fields = input_schema.get("fields", [])
        field_summary = ", ".join(
            (
                f'{field["name"]}: '
                f'{field["schema"]["type"]}'
                + (
                    ""
                    if field["required"]
                    else "?"
                )
            )
            for field in fields
        )
        result_type = action["result"]["type"]
        return {
            "contents": {
                "kind": "markdown",
                "value": (
                    f"**{word}** — standard VECTIS action\n\n"
                    f'{action["description"]}\n\n'
                    f'Requires capability **{action["capability"]}**.\n\n'
                    f"Input: `{field_summary}`\n\n"
                    f"Result: `{result_type}`\n\n"
                    "The operation has no authority unless explicitly "
                    "registered and granted by the host."
                ),
            }
        }

    return None


def _range(
    source: str,
    node: object,
) -> dict[str, dict[str, int]]:
    return source_span_to_lsp_range(
        source,
        node.span,
    )


def _symbol(
    *,
    name: str,
    kind: int,
    source: str,
    node: object,
    children: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    item: dict[str, object] = {
        "name": name,
        "kind": kind,
        "range": _range(source, node),
        "selectionRange": _range(source, node),
    }
    if children:
        item["children"] = children
    return item


def _block_symbols(
    source: str,
    block: Block,
) -> list[dict[str, object]]:
    symbols: list[dict[str, object]] = []
    for statement in block.statements:
        if isinstance(statement, Stage):
            symbols.append(
                _symbol(
                    name=statement.name,
                    kind=3,
                    source=source,
                    node=statement,
                    children=_block_symbols(source, statement.body),
                )
            )
        elif isinstance(
            statement,
            (
                SourceDeclaration,
                LetDeclaration,
                AnalyzeDeclaration,
                ActionStatement,
            ),
        ):
            symbols.append(
                _symbol(
                    name=statement.name,
                    kind=13,
                    source=source,
                    node=statement,
                )
            )
        elif isinstance(statement, WhenStatement):
            symbols.extend(_block_symbols(source, statement.body))
            if statement.otherwise is not None:
                symbols.extend(
                    _block_symbols(source, statement.otherwise)
                )
    return symbols


def document_symbols(
    source: str,
    *,
    file: str,
) -> list[dict[str, object]]:
    """Return hierarchical document symbols for valid VECTIS source."""
    program: Program = parse(source, file=file)
    symbols: list[dict[str, object]] = []

    for statement in program.statements:
        if isinstance(statement, FunctionDeclaration):
            symbols.append(
                _symbol(
                    name=statement.name,
                    kind=12,
                    source=source,
                    node=statement,
                )
            )
        elif isinstance(statement, Mission):
            symbols.append(
                _symbol(
                    name=statement.name,
                    kind=2,
                    source=source,
                    node=statement,
                    children=_block_symbols(source, statement.body),
                )
            )

    return symbols
