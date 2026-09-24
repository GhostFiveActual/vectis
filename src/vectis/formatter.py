# GHOST FIVE // VECTIS
# Formats VECTIS source into the canonical project style.
"""Canonical source formatter for VECTIS."""

from __future__ import annotations

import json

from vectis.ast import (
    ActionStatement,
    AnalyzeDeclaration,
    AssertStatement,
    BinaryExpression,
    Block,
    BooleanLiteral,
    CallExpression,
    CitationsStatement,
    ConfidenceStatement,
    Expression,
    FunctionDeclaration,
    ImportStatement,
    IndexAccess,
    LetDeclaration,
    ListLiteral,
    MemberAccess,
    Mission,
    NumberLiteral,
    ObjectLiteral,
    Program,
    PublishStatement,
    Reference,
    RequestStatement,
    RequireStatement,
    SourceDeclaration,
    Stage,
    Statement,
    StringLiteral,
    UnaryExpression,
    WhenStatement,
)


def format_expression(expression: Expression) -> str:
    if isinstance(expression, StringLiteral):
        return json.dumps(expression.value, ensure_ascii=False)
    if isinstance(expression, NumberLiteral):
        return str(expression.value)
    if isinstance(expression, BooleanLiteral):
        return "true" if expression.value else "false"
    if isinstance(expression, Reference):
        return expression.name
    if isinstance(expression, ListLiteral):
        return "[" + ", ".join(
            format_expression(item)
            for item in expression.items
        ) + "]"
    if isinstance(expression, ObjectLiteral):
        parts = []
        for key, item in expression.entries:
            rendered_key = (
                key
                if key.isidentifier()
                else json.dumps(key, ensure_ascii=False)
            )
            parts.append(
                f"{rendered_key}: {format_expression(item)}"
            )
        return "{" + ", ".join(parts) + "}"
    if isinstance(expression, MemberAccess):
        return (
            f"{format_expression(expression.target)}"
            f".{expression.member}"
        )
    if isinstance(expression, IndexAccess):
        return (
            f"{format_expression(expression.target)}"
            f"[{format_expression(expression.index)}]"
        )
    if isinstance(expression, CallExpression):
        arguments = ", ".join(
            format_expression(item) for item in expression.arguments
        )
        return f"{expression.name}({arguments})"
    if isinstance(expression, UnaryExpression):
        return f"{expression.operator}{format_expression(expression.operand)}"
    if isinstance(expression, BinaryExpression):
        return (
            f"({format_expression(expression.left)} "
            f"{expression.operator} "
            f"{format_expression(expression.right)})"
        )
    raise TypeError(f"Unsupported expression: {type(expression).__name__}")


def _format_block(block: Block, level: int) -> list[str]:
    lines = ["{"]
    for statement in block.statements:
        lines.extend(_format_statement(statement, level + 1))
    lines.append("    " * level + "}")
    return lines


def _format_statement(statement: Statement, level: int) -> list[str]:
    indent = "    " * level

    if isinstance(statement, ImportStatement):
        return [
            f"{indent}import "
            f"{json.dumps(statement.path, ensure_ascii=False)};"
        ]
    if isinstance(statement, FunctionDeclaration):
        annotations = (
            statement.parameter_types
            if statement.parameter_types
            else tuple(None for _parameter in statement.parameters)
        )
        parameters = ", ".join(
            (
                name
                if annotation is None
                else f"{name}: {annotation}"
            )
            for name, annotation in zip(
                statement.parameters,
                annotations,
                strict=True,
            )
        )
        result = (
            ""
            if statement.return_type is None
            else f": {statement.return_type}"
        )
        return [
            (
                f"{indent}function {statement.name}"
                f"({parameters}){result} {{"
            ),
            (
                f"{indent}    return "
                f"{format_expression(statement.body)};"
            ),
            f"{indent}}}",
        ]
    if isinstance(statement, Mission):
        lines = [f"{indent}mission {json.dumps(statement.name)} {{"]
        for item in statement.body.statements:
            lines.extend(_format_statement(item, level + 1))
        lines.append(f"{indent}}}")
        return lines
    if isinstance(statement, Stage):
        lines = [f"{indent}stage {json.dumps(statement.name)} {{"]
        for item in statement.body.statements:
            lines.extend(_format_statement(item, level + 1))
        lines.append(f"{indent}}}")
        return lines
    if isinstance(statement, SourceDeclaration):
        return [f"{indent}source {statement.name} {format_expression(statement.value)};"]
    if isinstance(statement, LetDeclaration):
        return [f"{indent}let {statement.name} {format_expression(statement.value)};"]
    if isinstance(statement, AnalyzeDeclaration):
        suffix = "" if statement.value is None else f" {format_expression(statement.value)}"
        return [f"{indent}analyze {statement.name}{suffix};"]
    if isinstance(statement, ActionStatement):
        return [
            (
                f"{indent}action {statement.name} "
                f"{json.dumps(statement.operation, ensure_ascii=False)} "
                f"using {json.dumps(statement.capability, ensure_ascii=False)} "
                f"{format_expression(statement.arguments)};"
            )
        ]
    if isinstance(statement, RequireStatement):
        return [f"{indent}require {format_expression(statement.capability)};"]
    if isinstance(statement, RequestStatement):
        return [f"{indent}request {format_expression(statement.capability)};"]
    if isinstance(statement, AssertStatement):
        message = (
            ""
            if statement.message is None
            else f", {json.dumps(statement.message, ensure_ascii=False)}"
        )
        return [
            f"{indent}assert {format_expression(statement.condition)}{message};"
        ]
    if isinstance(statement, PublishStatement):
        return [f"{indent}publish {format_expression(statement.value)};"]
    if isinstance(statement, ConfidenceStatement):
        return [f"{indent}confidence {format_expression(statement.value)};"]
    if isinstance(statement, CitationsStatement):
        values = ", ".join(format_expression(item) for item in statement.values)
        return [f"{indent}citations [{values}];"]
    if isinstance(statement, WhenStatement):
        lines = [f"{indent}when {format_expression(statement.condition)} {{"]
        for item in statement.body.statements:
            lines.extend(_format_statement(item, level + 1))
        if statement.otherwise is None:
            lines.append(f"{indent}}}")
            return lines
        lines.append(f"{indent}}} otherwise {{")
        for item in statement.otherwise.statements:
            lines.extend(_format_statement(item, level + 1))
        lines.append(f"{indent}}}")
        return lines

    raise TypeError(f"Unsupported statement: {type(statement).__name__}")


def format_program(program: Program) -> str:
    lines: list[str] = []
    for index, statement in enumerate(program.statements):
        if index:
            lines.append("")
        lines.extend(_format_statement(statement, 0))
    return "\n".join(lines) + ("\n" if lines else "")
