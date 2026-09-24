# GHOST FIVE // VECTIS
# Resolves deterministic, filesystem-bounded VECTIS source modules for compilation.
"""Module loading for multi-file VECTIS projects."""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from pathlib import Path
from typing import Mapping

from vectis.ast import (
    CallExpression,
    FunctionDeclaration,
    ImportStatement,
    Node,
    Program,
    Statement,
)
from vectis.diagnostic import (
    DiagnosticCode,
    DiagnosticError,
    error_diagnostic,
)
from vectis.parser import parse
from vectis.source_span import SourceSpan


class ModuleError(DiagnosticError):
    """Raised when a deterministic source module cannot be resolved."""

    def __init__(
        self,
        message: str,
        *,
        span: SourceSpan,
    ) -> None:
        super().__init__(
            error_diagnostic(
                code=DiagnosticCode.SEM_IMPORT_RESOLUTION,
                message=message,
                span=span,
            )
        )


@dataclass(frozen=True, slots=True)
class ModuleLoadResult:
    """Resolved module graph and flattened compilation program."""

    program: Program
    entry: Path
    root: Path
    modules: tuple[Path, ...]


def _inside_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def module_root_for(path: Path) -> Path:
    """Return the nearest VECTIS project root or the source directory."""
    source = path.expanduser().resolve()
    start = source.parent if source.suffix else source

    for candidate in (start, *start.parents):
        if (candidate / "vectis.toml").is_file():
            return candidate

    return source.parent if source.suffix else source


def _walk_nodes(value: object):
    if isinstance(value, Node):
        yield value
        if is_dataclass(value):
            for field in fields(value):
                yield from _walk_nodes(getattr(value, field.name))
        return
    if isinstance(value, tuple):
        for item in value:
            yield from _walk_nodes(item)


def validate_module_function_visibility(
    programs: Mapping[Path, Program],
    *,
    root: Path,
    imports_by_path: Mapping[
        Path,
        tuple[tuple[ImportStatement, Path], ...],
    ] | None = None,
) -> None:
    """Reject private or unselected cross-module function calls."""
    resolved_imports = imports_by_path or {}
    declarations: dict[
        str,
        list[tuple[Path, FunctionDeclaration]],
    ] = {}
    direct: dict[
        Path,
        dict[str, FunctionDeclaration],
    ] = {}
    local_names: dict[Path, set[str]] = {}

    for module_path, program in programs.items():
        names: set[str] = set()
        module_declarations: dict[str, FunctionDeclaration] = {}
        for statement in program.statements:
            if not isinstance(statement, FunctionDeclaration):
                continue
            names.add(statement.name)
            module_declarations[statement.name] = statement
            declarations.setdefault(statement.name, []).append(
                (module_path, statement)
            )
        local_names[module_path] = names
        direct[module_path] = module_declarations

    for _importer, imports in resolved_imports.items():
        for statement, target_path in imports:
            if statement.names is None:
                continue
            target_label = target_path.relative_to(root).as_posix()
            target_declarations = direct.get(target_path, {})
            for name in statement.names:
                target = target_declarations.get(name)
                if target is None:
                    raise ModuleError(
                        (
                            f"function {name!r} is not declared by "
                            f"module {target_label}"
                        ),
                        span=statement.span,
                    )
                if target.visibility == "private":
                    raise ModuleError(
                        (
                            f"function {name!r} is private to "
                            f"module {target_label}"
                        ),
                        span=statement.span,
                    )

    public_surface_cache: dict[
        Path,
        frozenset[tuple[Path, str]],
    ] = {}

    def public_surface(
        module_path: Path,
    ) -> frozenset[tuple[Path, str]]:
        cached = public_surface_cache.get(module_path)
        if cached is not None:
            return cached

        seen: set[Path] = set()
        pending = [module_path]
        result: set[tuple[Path, str]] = set()

        while pending:
            current = pending.pop()
            if current in seen:
                continue
            seen.add(current)

            for name, declaration in direct.get(current, {}).items():
                if declaration.visibility == "public":
                    result.add((current, name))

            for _statement, target in resolved_imports.get(
                current,
                (),
            ):
                pending.append(target)

        frozen = frozenset(result)
        public_surface_cache[module_path] = frozen
        return frozen

    for module_path, program in programs.items():
        local = local_names[module_path]
        imports = resolved_imports.get(module_path, ())
        selective_mode = any(
            statement.names is not None
            for statement, _target in imports
        )
        allowed: set[tuple[Path, str]] = set()

        if selective_mode:
            for statement, target_path in imports:
                if statement.names is None:
                    allowed.update(public_surface(target_path))
                else:
                    allowed.update(
                        (target_path, name)
                        for name in statement.names
                    )

        for node in _walk_nodes(program):
            if not isinstance(node, CallExpression):
                continue
            if node.name in local:
                continue

            targets = declarations.get(node.name, ())
            if len(targets) != 1:
                continue

            target_path, target = targets[0]
            if target_path == module_path:
                continue

            if target.visibility == "private":
                owner = target_path.relative_to(root).as_posix()
                raise ModuleError(
                    (
                        f"function {node.name!r} is private to "
                        f"module {owner}"
                    ),
                    span=node.span,
                )

            if (
                selective_mode
                and (target_path, node.name) not in allowed
            ):
                importer = module_path.relative_to(root).as_posix()
                raise ModuleError(
                    (
                        f"function {node.name!r} is not selected by "
                        f"imports in module {importer}"
                    ),
                    span=node.span,
                )


def load_program_file(
    path: Path,
    *,
    root: Path | None = None,
) -> ModuleLoadResult:
    """Load an entry source and all pure-function imports deterministically."""
    entry = path.expanduser().resolve()
    project_root = (
        root.expanduser().resolve()
        if root is not None
        else module_root_for(entry)
    )

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
    imported_functions: list[FunctionDeclaration] = []
    entry_functions: list[FunctionDeclaration] = []
    entry_executable: list[Statement] = []
    entry_program: Program | None = None

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

        candidate = (importer.parent / raw).resolve()

        if not _inside_root(candidate, project_root):
            raise ModuleError(
                "import path escapes the module root",
                span=statement.span,
            )

        if candidate.suffix != ".vectis":
            raise ModuleError(
                "import path must reference a .vectis source file",
                span=statement.span,
            )

        if not candidate.is_file():
            raise ModuleError(
                f"imported module does not exist: {statement.path}",
                span=statement.span,
            )

        return candidate

    def visit(module_path: Path, *, is_entry: bool) -> None:
        nonlocal entry_program

        if module_path in loaded:
            return

        if module_path in visiting:
            cycle_start = visiting.index(module_path)
            cycle = [
                *visiting[cycle_start:],
                module_path,
            ]
            rendered = " -> ".join(
                str(item.relative_to(project_root))
                for item in cycle
            )
            span = (
                entry_program.span
                if entry_program is not None
                else parse(
                    module_path.read_text(encoding="utf-8"),
                    file=str(module_path),
                ).span
            )
            raise ModuleError(
                f"import cycle is not allowed: {rendered}",
                span=span,
            )

        source = module_path.read_text(encoding="utf-8")
        program = parse(
            source,
            file=str(module_path),
        )
        program_by_path[module_path] = program

        if is_entry:
            entry_program = program

        visiting.append(module_path)

        imports = tuple(
            statement
            for statement in program.statements
            if isinstance(statement, ImportStatement)
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
            if not isinstance(statement, ImportStatement)
        )

        if is_entry:
            for statement in declarations:
                if isinstance(statement, FunctionDeclaration):
                    entry_functions.append(statement)
                else:
                    entry_executable.append(statement)
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
                        "imported modules may contain only imports "
                        "and pure function declarations"
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
        ordered_modules.append(module_path)

    visit(entry, is_entry=True)

    if entry_program is None:
        raise RuntimeError("module loader did not produce an entry program")

    validate_module_function_visibility(
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

    return ModuleLoadResult(
        program=merged,
        entry=entry,
        root=project_root,
        modules=tuple(ordered_modules),
    )
