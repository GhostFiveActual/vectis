# GHOST FIVE // VECTIS
# Resolves editor workspaces with unsaved overlays and deterministic symbol navigation.
"""Overlay-aware VECTIS workspace loading and deterministic symbol navigation."""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from pathlib import Path
import re
from typing import Mapping
from urllib.parse import unquote, urlparse

from vectis.ast import (
    ActionStatement,
    AnalyzeDeclaration,
    CallExpression,
    FunctionDeclaration,
    ImportStatement,
    LetDeclaration,
    NamespaceDeclaration,
    Node,
    Program,
    Reference,
    SourceDeclaration,
    Statement,
)
from vectis.diagnostic import DiagnosticError
from vectis.evaluator import BUILTINS
from vectis.function_identity import (
    ModuleFunctionId,
    ModuleFunctionScope,
)
from vectis.lexer import KEYWORDS, Lexer
from vectis.lsp_position import (
    contains_lsp_position,
    source_span_to_lsp_range,
)
from vectis.modules import (
    ModuleError,
    module_root_for,
    resolve_module_function_scope,
)
from vectis.parser import parse
from vectis.source_span import SourceSpan


_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True, slots=True)
class WorkspaceProgram:
    """Resolved module graph built from open buffers and disk fallback."""

    program: Program
    entry: Path
    root: Path
    modules: tuple[Path, ...]
    programs: tuple[tuple[Path, Program], ...]
    sources: tuple[tuple[Path, str], ...]
    function_scope: ModuleFunctionScope


@dataclass(frozen=True, slots=True)
class FunctionOccurrence:
    """One exact user-function declaration or call token."""

    name: str
    path: Path
    span: SourceSpan
    declaration: bool
    symbol: ModuleFunctionId


@dataclass(frozen=True, slots=True)
class ValueOccurrence:
    """One exact executable value declaration or reference token."""

    name: str
    path: Path
    span: SourceSpan
    declaration: bool


def uri_path(uri: str) -> Path | None:
    """Convert one file URI into a local path when possible."""
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        return None

    raw = unquote(parsed.path)
    if parsed.netloc:
        raw = f"//{parsed.netloc}{raw}"

    import os

    if (
        os.name == "nt"
        and len(raw) >= 3
        and raw[0] == "/"
        and raw[2] == ":"
    ):
        raw = raw[1:]

    return Path(raw)


def path_uri(path: Path) -> str:
    """Return a canonical file URI."""
    return path.expanduser().resolve().as_uri()


def overlay_map(
    documents: Mapping[str, str],
) -> dict[Path, str]:
    """Convert open LSP documents into canonical path overlays."""
    result: dict[Path, str] = {}
    for uri, source in documents.items():
        path = uri_path(uri)
        if path is None:
            continue
        result[path.expanduser().resolve()] = source
    return result


def load_workspace_program(
    path: Path,
    *,
    overlays: Mapping[Path, str] | None = None,
    root: Path | None = None,
) -> WorkspaceProgram:
    """Resolve one entry and its imports using open buffers before disk."""
    entry = path.expanduser().resolve()
    project_root = (
        root.expanduser().resolve()
        if root is not None
        else module_root_for(entry)
    )
    overlay_sources = {
        key.expanduser().resolve(): value
        for key, value in (overlays or {}).items()
    }

    if not _inside_root(entry, project_root):
        raise ValueError(
            "entry source must be inside the configured module root"
        )

    loaded: set[Path] = set()
    visiting: list[Path] = []
    ordered_modules: list[Path] = []
    program_by_path: dict[Path, Program] = {}
    resolved_imports: dict[
        Path,
        tuple[tuple[ImportStatement, Path], ...],
    ] = {}
    source_by_path: dict[Path, str] = {}
    imported_functions: list[FunctionDeclaration] = []
    entry_functions: list[FunctionDeclaration] = []
    entry_executable: list[Statement] = []
    entry_program: Program | None = None

    def source_for(module_path: Path) -> str:
        if module_path in overlay_sources:
            return overlay_sources[module_path]
        return module_path.read_text(encoding="utf-8")

    def exists(module_path: Path) -> bool:
        return (
            module_path in overlay_sources
            or module_path.is_file()
        )

    def resolve_import(
        statement: ImportStatement,
        importer: Path,
    ) -> Path:
        raw = Path(statement.path)

        if raw.is_absolute():
            raise ModuleError(
                "import path must be relative",
                span=statement.span,
            )

        candidate = (
            importer.parent / raw
        ).resolve()

        if not _inside_root(
            candidate,
            project_root,
        ):
            raise ModuleError(
                "import path escapes the module root",
                span=statement.span,
            )

        if candidate.suffix != ".vectis":
            raise ModuleError(
                "import path must reference a .vectis source file",
                span=statement.span,
            )

        if not exists(candidate):
            raise ModuleError(
                (
                    "imported module does not exist: "
                    f"{statement.path}"
                ),
                span=statement.span,
            )

        return candidate

    def visit(
        module_path: Path,
        *,
        is_entry: bool,
    ) -> None:
        nonlocal entry_program

        if module_path in loaded:
            return

        if module_path in visiting:
            start = visiting.index(module_path)
            cycle = [
                *visiting[start:],
                module_path,
            ]
            rendered = " -> ".join(
                str(item.relative_to(project_root))
                for item in cycle
            )
            current = program_by_path.get(
                visiting[-1]
            )
            if current is None:
                current = parse(
                    source_for(module_path),
                    file=str(module_path),
                )
            raise ModuleError(
                (
                    "import cycle is not allowed: "
                    + rendered
                ),
                span=current.span,
            )

        source = source_for(module_path)
        program = parse(
            source,
            file=str(module_path),
        )
        source_by_path[module_path] = source
        program_by_path[module_path] = program

        if is_entry:
            entry_program = program

        visiting.append(module_path)

        imports = tuple(
            statement
            for statement in program.statements
            if isinstance(
                statement,
                ImportStatement,
            )
        )

        resolved = tuple(
            (
                statement,
                resolve_import(
                    statement,
                    module_path,
                ),
            )
            for statement in imports
        )
        resolved_imports[module_path] = resolved

        for _statement, target in resolved:
            visit(
                target,
                is_entry=False,
            )

        declarations = tuple(
            statement
            for statement in program.statements
            if not isinstance(
                statement,
                (ImportStatement, NamespaceDeclaration),
            )
        )

        if is_entry:
            for statement in declarations:
                if isinstance(
                    statement,
                    FunctionDeclaration,
                ):
                    entry_functions.append(
                        statement
                    )
                else:
                    entry_executable.append(
                        statement
                    )
        else:
            invalid = next(
                (
                    statement
                    for statement in declarations
                    if not isinstance(
                        statement,
                        FunctionDeclaration,
                    )
                ),
                None,
            )
            if invalid is not None:
                raise ModuleError(
                    (
                        "imported modules may contain only imports, "
                        "one optional namespace declaration, and pure "
                        "function declarations"
                    ),
                    span=invalid.span,
                )

            imported_functions.extend(
                statement
                for statement in declarations
                if isinstance(
                    statement,
                    FunctionDeclaration,
                )
            )

        visiting.pop()
        loaded.add(module_path)
        ordered_modules.append(
            module_path
        )

    visit(entry, is_entry=True)

    if entry_program is None:
        raise RuntimeError(
            "workspace loader did not produce an entry program"
        )

    function_scope = resolve_module_function_scope(
        program_by_path,
        root=project_root,
        imports_by_path=resolved_imports,
    )

    merged = Program(
        span=entry_program.span,
        statements=tuple(
            [
                *imported_functions,
                *entry_functions,
                *entry_executable,
            ]
        ),
    )

    return WorkspaceProgram(
        program=merged,
        entry=entry,
        root=project_root,
        modules=tuple(ordered_modules),
        programs=tuple(
            (
                module_path,
                program_by_path[module_path],
            )
            for module_path in ordered_modules
        ),
        sources=tuple(
            (
                module_path,
                source_by_path[module_path],
            )
            for module_path in ordered_modules
        ),
        function_scope=function_scope,
    )


def navigation_workspace(
    target: Path,
    *,
    documents: Mapping[str, str],
) -> WorkspaceProgram:
    """Choose the widest open reachable workspace containing target."""
    canonical_target = (
        target.expanduser().resolve()
    )
    overlays = overlay_map(documents)
    candidates: list[WorkspaceProgram] = []

    for entry in sorted(
        overlays,
        key=lambda item: str(item),
    ):
        try:
            workspace = load_workspace_program(
                entry,
                overlays=overlays,
            )
        except (
            DiagnosticError,
            OSError,
            UnicodeError,
            ValueError,
        ):
            continue

        if canonical_target in workspace.modules:
            candidates.append(workspace)

    if candidates:
        candidates.sort(
            key=lambda item: (
                -len(item.modules),
                str(item.entry),
            )
        )
        return candidates[0]

    return load_workspace_program(
        canonical_target,
        overlays=overlays,
    )


def function_definition(
    workspace: WorkspaceProgram,
    *,
    path: Path,
    line: int,
    character: int,
) -> dict[str, object] | None:
    """Return the declaration location for the function under the cursor."""
    symbol = _function_symbol_at(
        workspace,
        path=path,
        line=line,
        character=character,
    )
    if symbol is None:
        return None

    declaration = next(
        (
            item
            for item in function_occurrences(
                workspace
            )
            if (
                item.symbol == symbol
                and item.declaration
            )
        ),
        None,
    )
    if declaration is None:
        return None
    return _location(workspace, declaration)


def function_references(
    workspace: WorkspaceProgram,
    *,
    path: Path,
    line: int,
    character: int,
    include_declaration: bool,
) -> list[dict[str, object]]:
    """Return deterministic reachable references for one user function."""
    symbol = _function_symbol_at(
        workspace,
        path=path,
        line=line,
        character=character,
    )
    if symbol is None:
        return []

    return [
        _location(workspace, item)
        for item in function_occurrences(
            workspace
        )
        if (
            item.symbol == symbol
            and (
                include_declaration
                or not item.declaration
            )
        )
    ]


def function_rename(
    workspace: WorkspaceProgram,
    *,
    path: Path,
    line: int,
    character: int,
    new_name: str,
) -> dict[str, object] | None:
    """Return a WorkspaceEdit for one reachable user-function symbol."""
    if not valid_function_name(new_name):
        raise ValueError(
            "new function name must be an unused VECTIS identifier"
        )

    symbol = _function_symbol_at(
        workspace,
        path=path,
        line=line,
        character=character,
    )
    if symbol is None:
        return None

    occurrences = [
        item
        for item in function_occurrences(
            workspace
        )
        if item.symbol == symbol
    ]
    if not occurrences:
        return None

    existing = {
        item.name
        for item in function_occurrences(
            workspace
        )
        if (
            item.declaration
            and item.symbol.module == symbol.module
        )
    }
    if (
        new_name != symbol.name
        and new_name in existing
    ):
        raise ValueError(
            (
                "new function name conflicts with an "
                "existing user function in the same module"
            )
        )

    changes: dict[
        str,
        list[dict[str, object]],
    ] = {}
    source_map = dict(workspace.sources)

    for item in occurrences:
        uri = path_uri(item.path)
        changes.setdefault(
            uri,
            [],
        ).append(
            {
                "range": _lsp_range(
                    source_map[item.path],
                    item.span,
                ),
                "newText": new_name,
            }
        )

    return {
        "changes": {
            uri: changes[uri]
            for uri in sorted(changes)
        }
    }


def valid_function_name(name: str) -> bool:
    """Return whether a rename target is valid for user functions."""
    return (
        isinstance(name, str)
        and bool(_IDENTIFIER.fullmatch(name))
        and name not in KEYWORDS
        and name not in BUILTINS
    )


def function_occurrences(
    workspace: WorkspaceProgram,
) -> tuple[FunctionOccurrence, ...]:
    """Return exact declaration and call token occurrences."""
    source_map = dict(
        workspace.sources
    )
    result: list[FunctionOccurrence] = []

    for path, program in workspace.programs:
        source = source_map[path]
        tokens = Lexer(
            source,
            file=str(path),
        ).tokenize()

        for node in _walk(program):
            if isinstance(node, ImportStatement):
                if node.names is not None:
                    for name in node.names:
                        symbol = (
                            workspace.function_scope.selector_target(
                                node.span,
                                name,
                            )
                        )
                        if symbol is None:
                            continue
                        span = _identifier_span(
                            tokens,
                            node.span,
                            name,
                        )
                        if span is not None:
                            result.append(
                                FunctionOccurrence(
                                    name=name,
                                    path=path,
                                    span=span,
                                    declaration=False,
                                    symbol=symbol,
                                )
                            )
                continue

            if isinstance(
                node,
                FunctionDeclaration,
            ):
                symbol = (
                    workspace.function_scope.declaration_id(
                        node.span
                    )
                )
                if symbol is None:
                    continue
                span = _identifier_span(
                    tokens,
                    node.span,
                    node.name,
                )
                if span is not None:
                    result.append(
                        FunctionOccurrence(
                            name=node.name,
                            path=path,
                            span=span,
                            declaration=True,
                            symbol=symbol,
                        )
                    )
                continue

            if isinstance(
                node,
                CallExpression,
            ):
                if node.name in BUILTINS and node.qualifier is None:
                    continue
                symbol = (
                    workspace.function_scope.call_target(
                        node.span
                    )
                )
                if symbol is None:
                    continue
                span = (
                    _qualified_call_name_span(
                        tokens,
                        node.span,
                        qualifier=node.qualifier,
                        name=node.name,
                    )
                    if node.qualifier is not None
                    else _identifier_span(
                        tokens,
                        node.span,
                        node.name,
                    )
                )
                if span is not None:
                    result.append(
                        FunctionOccurrence(
                            name=node.name,
                            path=path,
                            span=span,
                            declaration=False,
                            symbol=symbol,
                        )
                    )

    unique = {
        (
            item.symbol.module,
            item.symbol.name,
            item.name,
            str(item.path),
            item.span.start.line,
            item.span.start.column,
            item.span.end.line,
            item.span.end.column,
            item.declaration,
        ): item
        for item in result
    }

    return tuple(
        sorted(
            unique.values(),
            key=lambda item: (
                str(item.path),
                item.span.start.line,
                item.span.start.column,
                not item.declaration,
            ),
        )
    )


def symbol_definition(
    workspace: WorkspaceProgram,
    *,
    path: Path,
    line: int,
    character: int,
) -> dict[str, object] | None:
    """Return the definition for the supported symbol under the cursor."""
    if _function_symbol_at(
        workspace,
        path=path,
        line=line,
        character=character,
    ) is not None:
        return function_definition(
            workspace,
            path=path,
            line=line,
            character=character,
        )
    return value_definition(
        workspace,
        path=path,
        line=line,
        character=character,
    )


def symbol_references(
    workspace: WorkspaceProgram,
    *,
    path: Path,
    line: int,
    character: int,
    include_declaration: bool,
) -> list[dict[str, object]]:
    """Return references for the supported symbol under the cursor."""
    if _function_symbol_at(
        workspace,
        path=path,
        line=line,
        character=character,
    ) is not None:
        return function_references(
            workspace,
            path=path,
            line=line,
            character=character,
            include_declaration=include_declaration,
        )
    return value_references(
        workspace,
        path=path,
        line=line,
        character=character,
        include_declaration=include_declaration,
    )


def symbol_rename(
    workspace: WorkspaceProgram,
    *,
    path: Path,
    line: int,
    character: int,
    new_name: str,
) -> dict[str, object] | None:
    """Return a WorkspaceEdit for the supported symbol under the cursor."""
    if _function_symbol_at(
        workspace,
        path=path,
        line=line,
        character=character,
    ) is not None:
        return function_rename(
            workspace,
            path=path,
            line=line,
            character=character,
            new_name=new_name,
        )
    return value_rename(
        workspace,
        path=path,
        line=line,
        character=character,
        new_name=new_name,
    )


def value_definition(
    workspace: WorkspaceProgram,
    *,
    path: Path,
    line: int,
    character: int,
) -> dict[str, object] | None:
    """Return the unique executable value declaration under the cursor."""
    name = _value_name_at(
        workspace,
        path=path,
        line=line,
        character=character,
    )
    if name is None:
        return None

    declarations = [
        item
        for item in value_occurrences(workspace)
        if item.name == name and item.declaration
    ]
    if len(declarations) != 1:
        return None
    return _location(workspace, declarations[0])


def value_references(
    workspace: WorkspaceProgram,
    *,
    path: Path,
    line: int,
    character: int,
    include_declaration: bool,
) -> list[dict[str, object]]:
    """Return deterministic references for one executable value."""
    name = _value_name_at(
        workspace,
        path=path,
        line=line,
        character=character,
    )
    if name is None:
        return []

    occurrences = [
        item
        for item in value_occurrences(workspace)
        if item.name == name
    ]
    declarations = [
        item for item in occurrences if item.declaration
    ]
    if len(declarations) != 1:
        return []

    return [
        _location(workspace, item)
        for item in occurrences
        if include_declaration or not item.declaration
    ]


def value_rename(
    workspace: WorkspaceProgram,
    *,
    path: Path,
    line: int,
    character: int,
    new_name: str,
) -> dict[str, object] | None:
    """Return a WorkspaceEdit for one executable value symbol."""
    name = _value_name_at(
        workspace,
        path=path,
        line=line,
        character=character,
    )
    if name is None:
        return None

    if not valid_value_name(new_name):
        raise ValueError(
            "new value name must be a non-reserved VECTIS identifier"
        )

    occurrences = [
        item
        for item in value_occurrences(workspace)
        if item.name == name
    ]
    declarations = [
        item for item in occurrences if item.declaration
    ]
    if len(declarations) != 1:
        return None

    existing = {
        item.name
        for item in value_occurrences(workspace)
        if item.declaration
    }
    if new_name != name and new_name in existing:
        raise ValueError(
            "new value name conflicts with an existing executable value"
        )

    changes: dict[str, list[dict[str, object]]] = {}
    source_map = dict(workspace.sources)
    for item in occurrences:
        uri = path_uri(item.path)
        changes.setdefault(uri, []).append(
            {
                "range": _lsp_range(
                    source_map[item.path],
                    item.span,
                ),
                "newText": new_name,
            }
        )

    return {
        "changes": {
            uri: changes[uri]
            for uri in sorted(changes)
        }
    }


def valid_value_name(name: str) -> bool:
    """Return whether a rename target is valid for executable values."""
    return (
        isinstance(name, str)
        and bool(_IDENTIFIER.fullmatch(name))
        and name not in KEYWORDS
        and name not in {"true", "false"}
    )


def value_occurrences(
    workspace: WorkspaceProgram,
) -> tuple[ValueOccurrence, ...]:
    """Return entry-source executable value declarations and references."""
    source_map = dict(workspace.sources)
    program_map = dict(workspace.programs)
    program = program_map.get(workspace.entry)
    source = source_map.get(workspace.entry)
    if program is None or source is None:
        return ()

    tokens = Lexer(
        source,
        file=str(workspace.entry),
    ).tokenize()
    result: list[ValueOccurrence] = []
    declaration_types = (
        SourceDeclaration,
        LetDeclaration,
        AnalyzeDeclaration,
        ActionStatement,
    )

    for statement in program.statements:
        if isinstance(statement, FunctionDeclaration):
            continue

        for node in _walk(statement):
            if isinstance(node, declaration_types):
                span = _identifier_span(
                    tokens,
                    node.span,
                    node.name,
                )
                if span is not None:
                    result.append(
                        ValueOccurrence(
                            name=node.name,
                            path=workspace.entry,
                            span=span,
                            declaration=True,
                        )
                    )
                continue

            if isinstance(node, Reference):
                result.append(
                    ValueOccurrence(
                        name=node.name,
                        path=workspace.entry,
                        span=node.span,
                        declaration=False,
                    )
                )

    unique = {
        (
            item.name,
            str(item.path),
            item.span.start.line,
            item.span.start.column,
            item.span.end.line,
            item.span.end.column,
            item.declaration,
        ): item
        for item in result
    }

    return tuple(
        sorted(
            unique.values(),
            key=lambda item: (
                str(item.path),
                item.span.start.line,
                item.span.start.column,
                not item.declaration,
            ),
        )
    )


def _value_name_at(
    workspace: WorkspaceProgram,
    *,
    path: Path,
    line: int,
    character: int,
) -> str | None:
    canonical = path.expanduser().resolve()
    source_map = dict(workspace.sources)
    for item in value_occurrences(workspace):
        if item.path != canonical:
            continue
        if _contains_lsp_position(
            source_map[item.path],
            item.span,
            line=line,
            character=character,
        ):
            return item.name
    return None

def _function_symbol_at(
    workspace: WorkspaceProgram,
    *,
    path: Path,
    line: int,
    character: int,
) -> ModuleFunctionId | None:
    canonical = path.expanduser().resolve()
    source_map = dict(workspace.sources)
    for item in function_occurrences(
        workspace
    ):
        if item.path != canonical:
            continue
        if _contains_lsp_position(
            source_map[item.path],
            item.span,
            line=line,
            character=character,
        ):
            return item.symbol
    return None


def _qualified_call_name_span(
    tokens: list[object],
    outer: SourceSpan,
    *,
    qualifier: str,
    name: str,
) -> SourceSpan | None:
    """Return the member token span for one qualified call."""
    for index in range(len(tokens) - 3):
        alias = tokens[index]
        dot = tokens[index + 1]
        member = tokens[index + 2]
        opening = tokens[index + 3]
        if not (
            getattr(alias, "type", None) == "identifier"
            and getattr(alias, "value", None) == qualifier
            and getattr(dot, "type", None) == "punctuation"
            and getattr(dot, "value", None) == "."
            and getattr(member, "type", None) == "identifier"
            and getattr(member, "value", None) == name
            and getattr(opening, "type", None) == "punctuation"
            and getattr(opening, "value", None) == "("
        ):
            continue
        member_span = getattr(member, "span", None)
        alias_span = getattr(alias, "span", None)
        if (
            isinstance(member_span, SourceSpan)
            and isinstance(alias_span, SourceSpan)
            and _span_inside(alias_span, outer)
            and _span_inside(member_span, outer)
        ):
            return member_span
    return None


def _identifier_span(
    tokens: list[object],
    outer: SourceSpan,
    name: str,
) -> SourceSpan | None:
    for token in tokens:
        if (
            getattr(token, "type", None)
            != "identifier"
            or getattr(
                token,
                "value",
                None,
            )
            != name
        ):
            continue
        span = getattr(
            token,
            "span",
            None,
        )
        if (
            isinstance(
                span,
                SourceSpan,
            )
            and _span_inside(
                span,
                outer,
            )
        ):
            return span
    return None


def _walk(value: object):
    if isinstance(value, Node):
        yield value

    if is_dataclass(value):
        for field in fields(value):
            if field.name == "span":
                continue
            yield from _walk(
                getattr(
                    value,
                    field.name,
                )
            )
        return

    if isinstance(
        value,
        (tuple, list),
    ):
        for item in value:
            yield from _walk(item)


def _position_key(
    line: int,
    column: int,
) -> tuple[int, int]:
    return (line, column)


def _span_inside(
    inner: SourceSpan,
    outer: SourceSpan,
) -> bool:
    return (
        _position_key(
            outer.start.line,
            outer.start.column,
        )
        <= _position_key(
            inner.start.line,
            inner.start.column,
        )
        and _position_key(
            inner.end.line,
            inner.end.column,
        )
        <= _position_key(
            outer.end.line,
            outer.end.column,
        )
    )


def _contains_lsp_position(
    source: str,
    span: SourceSpan,
    *,
    line: int,
    character: int,
) -> bool:
    return contains_lsp_position(
        source,
        span,
        line=line,
        character=character,
    )


def _lsp_range(
    source: str,
    span: SourceSpan,
) -> dict[str, object]:
    return source_span_to_lsp_range(
        source,
        span,
    )


def _location(
    workspace: WorkspaceProgram,
    occurrence: FunctionOccurrence | ValueOccurrence,
) -> dict[str, object]:
    source_map = dict(workspace.sources)
    return {
        "uri": path_uri(
            occurrence.path
        ),
        "range": _lsp_range(
            source_map[occurrence.path],
            occurrence.span,
        ),
    }


def _inside_root(
    path: Path,
    root: Path,
) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


__all__ = [
    "FunctionOccurrence",
    "ValueOccurrence",
    "WorkspaceProgram",
    "function_definition",
    "function_occurrences",
    "function_references",
    "function_rename",
    "load_workspace_program",
    "navigation_workspace",
    "overlay_map",
    "path_uri",
    "symbol_definition",
    "symbol_references",
    "symbol_rename",
    "uri_path",
    "valid_function_name",
    "valid_value_name",
    "value_definition",
    "value_occurrences",
    "value_references",
    "value_rename",
]
