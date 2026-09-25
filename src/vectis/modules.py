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
    NamespaceDeclaration,
    Node,
    Program,
    Statement,
)
from vectis.diagnostic import (
    DiagnosticCode,
    DiagnosticError,
    error_diagnostic,
)
from vectis.evaluator import BUILTINS
from vectis.function_identity import (
    FunctionSelectorBinding,
    ModuleFunctionId,
    ModuleFunctionScope,
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
    function_scope: ModuleFunctionScope


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


def resolve_module_function_scope(
    programs: Mapping[Path, Program],
    *,
    root: Path,
    imports_by_path: Mapping[
        Path,
        tuple[tuple[ImportStatement, Path], ...],
    ] | None = None,
) -> ModuleFunctionScope:
    """Resolve durable function identity across one loaded module graph."""
    resolved_imports = imports_by_path or {}
    namespace_by_path: dict[Path, tuple[str, SourceSpan]] = {}

    for module_path, program in programs.items():
        namespaces = tuple(
            statement
            for statement in program.statements
            if isinstance(statement, NamespaceDeclaration)
        )
        module_label = module_path.relative_to(root).as_posix()
        if len(namespaces) > 1:
            raise ModuleError(
                (
                    "duplicate namespace declaration in module "
                    f"{module_label}"
                ),
                span=namespaces[1].span,
            )
        if namespaces:
            declaration = namespaces[0]
            if not program.statements or program.statements[0] is not declaration:
                raise ModuleError(
                    (
                        "namespace declaration must be the first "
                        f"statement in module {module_label}"
                    ),
                    span=declaration.span,
                )
            namespace_by_path[module_path] = (
                declaration.name,
                declaration.span,
            )

    direct: dict[
        Path,
        dict[
            str,
            tuple[FunctionDeclaration, ModuleFunctionId],
        ],
    ] = {}
    declarations_by_name: dict[
        str,
        list[
            tuple[
                Path,
                FunctionDeclaration,
                ModuleFunctionId,
            ]
        ],
    ] = {}
    declaration_bindings: list[
        tuple[SourceSpan, ModuleFunctionId]
    ] = []

    def identity(
        module_path: Path,
        name: str,
    ) -> ModuleFunctionId:
        return ModuleFunctionId(
            module=module_path.relative_to(root).as_posix(),
            name=name,
        )

    for module_path, program in programs.items():
        module_declarations: dict[
            str,
            tuple[FunctionDeclaration, ModuleFunctionId],
        ] = {}
        for statement in program.statements:
            if not isinstance(statement, FunctionDeclaration):
                continue
            function_id = identity(
                module_path,
                statement.name,
            )
            declaration_bindings.append(
                (statement.span, function_id)
            )
            declarations_by_name.setdefault(
                statement.name,
                [],
            ).append(
                (
                    module_path,
                    statement,
                    function_id,
                )
            )
            module_declarations.setdefault(
                statement.name,
                (statement, function_id),
            )
        direct[module_path] = module_declarations

    selector_bindings: list[
        FunctionSelectorBinding
    ] = []

    for _importer, imports in resolved_imports.items():
        aliases: set[str] = set()
        for statement, target_path in imports:
            if statement.alias is not None:
                if statement.alias in aliases:
                    raise ModuleError(
                        (
                            "duplicate module alias in one module: "
                            f"{statement.alias}"
                        ),
                        span=statement.span,
                    )
                aliases.add(statement.alias)

            if statement.names is None:
                continue
            target_label = target_path.relative_to(root).as_posix()
            target_declarations = direct.get(target_path, {})
            for name in statement.names:
                target_pair = target_declarations.get(name)
                if target_pair is None:
                    raise ModuleError(
                        (
                            f"function {name!r} is not declared by "
                            f"module {target_label}"
                        ),
                        span=statement.span,
                    )
                target, function_id = target_pair
                if target.visibility == "private":
                    raise ModuleError(
                        (
                            f"function {name!r} is private to "
                            f"module {target_label}"
                        ),
                        span=statement.span,
                    )
                selector_bindings.append(
                    FunctionSelectorBinding(
                        span=statement.span,
                        name=name,
                        target=function_id,
                    )
                )

    public_surface_cache: dict[
        Path,
        frozenset[ModuleFunctionId],
    ] = {}

    def public_surface(
        module_path: Path,
    ) -> frozenset[ModuleFunctionId]:
        cached = public_surface_cache.get(module_path)
        if cached is not None:
            return cached

        seen: set[Path] = set()
        pending = [module_path]
        result: set[ModuleFunctionId] = set()

        while pending:
            current = pending.pop()
            if current in seen:
                continue
            seen.add(current)

            for declaration, function_id in direct.get(
                current,
                {},
            ).values():
                if declaration.visibility == "public":
                    result.add(function_id)

            for statement, target in resolved_imports.get(
                current,
                (),
            ):
                if statement.alias is None:
                    pending.append(target)

        frozen = frozenset(result)
        public_surface_cache[module_path] = frozen
        return frozen

    public_by_name: dict[
        str,
        set[ModuleFunctionId],
    ] = {}
    for name, declarations in declarations_by_name.items():
        for _path, declaration, function_id in declarations:
            if declaration.visibility == "public":
                public_by_name.setdefault(
                    name,
                    set(),
                ).add(function_id)

    graph_has_alias = any(
        statement.alias is not None
        for imports in resolved_imports.values()
        for statement, _target in imports
    )
    graph_has_namespace = bool(namespace_by_path)

    call_bindings: list[
        tuple[SourceSpan, ModuleFunctionId]
    ] = []

    for module_path, program in programs.items():
        local = direct.get(module_path, {})
        imports = resolved_imports.get(module_path, ())
        qualifiers: dict[
            str,
            tuple[
                Path,
                str,
                frozenset[str] | None,
                SourceSpan,
            ],
        ] = {}
        for statement, target_path in imports:
            if statement.alias is not None:
                selected = (
                    None
                    if statement.names is None
                    else frozenset(statement.names)
                )
                qualifiers[statement.alias] = (
                    target_path,
                    "alias",
                    selected,
                    statement.span,
                )

        for statement, target_path in imports:
            if statement.alias is not None:
                continue
            declared = namespace_by_path.get(target_path)
            if declared is None:
                continue
            namespace_name, _namespace_span = declared
            selected = (
                None
                if statement.names is None
                else frozenset(statement.names)
            )
            existing = qualifiers.get(namespace_name)
            if existing is not None:
                (
                    existing_target,
                    existing_kind,
                    existing_selected,
                    existing_span,
                ) = existing
                if (
                    existing_kind == "namespace"
                    and existing_target == target_path
                ):
                    merged_selected = (
                        None
                        if existing_selected is None or selected is None
                        else existing_selected | selected
                    )
                    qualifiers[namespace_name] = (
                        target_path,
                        "namespace",
                        merged_selected,
                        existing_span,
                    )
                    continue
                importer = module_path.relative_to(root).as_posix()
                raise ModuleError(
                    (
                        "duplicate module qualifier in module "
                        f"{importer}: {namespace_name}"
                    ),
                    span=statement.span,
                )
            qualifiers[namespace_name] = (
                target_path,
                "namespace",
                selected,
                statement.span,
            )

        legacy_selective_mode = any(
            statement.names is not None
            for statement, _target in imports
        )
        constrained_bare_mode = (
            graph_has_alias
            or legacy_selective_mode
        )
        allowed_bare: set[ModuleFunctionId] = set()

        if constrained_bare_mode:
            for statement, target_path in imports:
                if statement.alias is not None:
                    continue
                if statement.names is None:
                    allowed_bare.update(
                        public_surface(target_path)
                    )
                else:
                    for name in statement.names:
                        pair = direct.get(
                            target_path,
                            {},
                        ).get(name)
                        if pair is not None:
                            allowed_bare.add(pair[1])

        for node in _walk_nodes(program):
            if not isinstance(node, CallExpression):
                continue

            if node.qualifier is not None:
                qualified_import = qualifiers.get(node.qualifier)
                importer = module_path.relative_to(root).as_posix()
                if qualified_import is None:
                    if graph_has_namespace:
                        message = (
                            f"unknown module qualifier {node.qualifier!r} "
                            f"in module {importer}"
                        )
                    else:
                        message = (
                            f"unknown module alias {node.qualifier!r} "
                            f"in module {importer}"
                        )
                    raise ModuleError(
                        message,
                        span=node.span,
                    )

                (
                    target_path,
                    qualifier_kind,
                    selected_names,
                    _qualifier_span,
                ) = qualified_import
                target_label = target_path.relative_to(root).as_posix()
                pair = direct.get(
                    target_path,
                    {},
                ).get(node.name)
                if pair is None:
                    owner_kind = (
                        "aliased"
                        if qualifier_kind == "alias"
                        else "namespaced"
                    )
                    raise ModuleError(
                        (
                            f"function {node.name!r} is not declared by "
                            f"{owner_kind} module {target_label}"
                        ),
                        span=node.span,
                    )

                target, function_id = pair
                if target.visibility == "private":
                    raise ModuleError(
                        (
                            f"function {node.name!r} is private to "
                            f"module {target_label}"
                        ),
                        span=node.span,
                    )

                if (
                    selected_names is not None
                    and node.name not in selected_names
                ):
                    qualifier_label = (
                        "module alias"
                        if qualifier_kind == "alias"
                        else "module namespace"
                    )
                    raise ModuleError(
                        (
                            f"function {node.name!r} is not selected by "
                            f"{qualifier_label} {node.qualifier!r}"
                        ),
                        span=node.span,
                    )

                call_bindings.append(
                    (node.span, function_id)
                )
                continue

            if node.name in BUILTINS:
                continue

            local_pair = local.get(node.name)
            if local_pair is not None:
                call_bindings.append(
                    (node.span, local_pair[1])
                )
                continue

            if constrained_bare_mode:
                candidates = sorted(
                    function_id
                    for function_id in allowed_bare
                    if function_id.name == node.name
                )
            else:
                candidates = sorted(
                    public_by_name.get(
                        node.name,
                        set(),
                    )
                )

            if len(candidates) == 1:
                call_bindings.append(
                    (node.span, candidates[0])
                )
                continue

            if len(candidates) > 1:
                importer = module_path.relative_to(root).as_posix()
                rendered = ", ".join(
                    item.label
                    for item in candidates
                )
                raise ModuleError(
                    (
                        f"function {node.name!r} is ambiguous in "
                        f"module {importer}; candidates: {rendered}"
                    ),
                    span=node.span,
                )

            targets = declarations_by_name.get(
                node.name,
                (),
            )
            if len(targets) != 1:
                continue

            target_path, target, function_id = targets[0]
            if (
                target_path != module_path
                and target.visibility == "private"
            ):
                owner = target_path.relative_to(root).as_posix()
                raise ModuleError(
                    (
                        f"function {node.name!r} is private to "
                        f"module {owner}"
                    ),
                    span=node.span,
                )

            if (
                constrained_bare_mode
                and function_id not in allowed_bare
            ):
                importer = module_path.relative_to(root).as_posix()
                if (
                    legacy_selective_mode
                    and not graph_has_alias
                ):
                    raise ModuleError(
                        (
                            f"function {node.name!r} is not selected by "
                            f"imports in module {importer}"
                        ),
                        span=node.span,
                    )
                raise ModuleError(
                    (
                        f"function {node.name!r} is not available as "
                        f"a bare call in module {importer}"
                    ),
                    span=node.span,
                )

    return ModuleFunctionScope(
        declarations=tuple(declaration_bindings),
        calls=tuple(call_bindings),
        selectors=tuple(selector_bindings),
    )


def validate_module_function_visibility(
    programs: Mapping[Path, Program],
    *,
    root: Path,
    imports_by_path: Mapping[
        Path,
        tuple[tuple[ImportStatement, Path], ...],
    ] | None = None,
) -> None:
    """Reject inaccessible or ambiguous cross-module function calls."""
    resolve_module_function_scope(
        programs,
        root=root,
        imports_by_path=imports_by_path,
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
            if not isinstance(
                statement,
                (ImportStatement, NamespaceDeclaration),
            )
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
        ordered_modules.append(module_path)

    visit(entry, is_entry=True)

    if entry_program is None:
        raise RuntimeError("module loader did not produce an entry program")

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

    return ModuleLoadResult(
        program=merged,
        entry=entry,
        root=project_root,
        modules=tuple(ordered_modules),
        function_scope=function_scope,
    )
