# GHOST FIVE // VECTIS
# Resolves deterministic, filesystem-bounded VECTIS source modules for compilation.
"""Module loading for multi-file VECTIS projects."""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
import os
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
from vectis.package_manifest import (
    PackageManifest,
    PackageManifestError,
    load_package_manifest,
    package_entry_path,
)
from vectis.package_reference import (
    PackageReferenceError,
    resolve_package_reference,
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


def module_label_for(path: Path, root: Path) -> str:
    """Return a deterministic composition-relative source label."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return Path(os.path.relpath(path, root)).as_posix()


def module_root_for(path: Path) -> Path:
    """Return the nearest VECTIS project root or the source directory."""
    source = path.expanduser().resolve()
    start = source.parent if source.suffix else source

    for candidate in (start, *start.parents):
        if (candidate / "vectis.toml").is_file():
            return candidate

    return source.parent if source.suffix else source


def validate_package_composition(
    programs: Mapping[Path, Program],
    *,
    root: Path,
    imports_by_path: Mapping[
        Path,
        tuple[tuple[ImportStatement, Path], ...],
    ],
    manifest: PackageManifest,
) -> None:
    """Enforce direct package dependency contracts for loaded package closures."""
    for declaration in manifest.packages:
        entry_path = package_entry_path(
            root,
            declaration,
        )
        if entry_path not in programs:
            continue

        seen: set[Path] = set()
        pending = [entry_path]
        while pending:
            module_path = pending.pop()
            if module_path in seen:
                continue
            seen.add(module_path)

            for statement, target_path in imports_by_path.get(
                module_path,
                (),
            ):
                if statement.package:
                    if declaration.dependency(statement.path) is None:
                        owner = declaration.name
                        raise ModuleError(
                            (
                                f"package {owner!r} imports package "
                                f"{statement.path!r} without a dependency contract"
                            ),
                            span=statement.span,
                        )
                    continue
                pending.append(target_path)


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
    module_labels: Mapping[Path, str] | None = None,
) -> ModuleFunctionScope:
    """Resolve durable function identity across one loaded module graph."""
    resolved_imports = imports_by_path or {}
    explicit_labels = module_labels or {}

    def label(module_path: Path) -> str:
        return explicit_labels.get(
            module_path,
            module_label_for(module_path, root),
        )
    namespace_by_path: dict[Path, tuple[str, SourceSpan]] = {}

    for module_path, program in programs.items():
        namespaces = tuple(
            statement
            for statement in program.statements
            if isinstance(statement, NamespaceDeclaration)
        )
        module_label = label(module_path)
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
            module=label(module_path),
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
            target_label = label(target_path)
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
                if statement.alias is None and not statement.package:
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
    graph_has_package = any(
        statement.package
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
            if statement.alias is None:
                continue
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

        def register_qualifier(
            name: str,
            *,
            target_path: Path,
            kind: str,
            selected: frozenset[str] | None,
            span: SourceSpan,
        ) -> None:
            existing = qualifiers.get(name)
            if existing is not None:
                (
                    existing_target,
                    existing_kind,
                    existing_selected,
                    existing_span,
                ) = existing
                if (
                    existing_kind == kind
                    and existing_target == target_path
                    and kind in {"namespace", "package"}
                ):
                    merged_selected = (
                        None
                        if existing_selected is None or selected is None
                        else existing_selected | selected
                    )
                    qualifiers[name] = (
                        target_path,
                        kind,
                        merged_selected,
                        existing_span,
                    )
                    return
                importer = label(module_path)
                raise ModuleError(
                    (
                        "duplicate module qualifier in module "
                        f"{importer}: {name}"
                    ),
                    span=span,
                )
            qualifiers[name] = (
                target_path,
                kind,
                selected,
                span,
            )

        for statement, target_path in imports:
            if statement.alias is not None:
                continue
            selected = (
                None
                if statement.names is None
                else frozenset(statement.names)
            )
            if statement.package:
                register_qualifier(
                    statement.path,
                    target_path=target_path,
                    kind="package",
                    selected=selected,
                    span=statement.span,
                )
                continue

            declared = namespace_by_path.get(target_path)
            if declared is None:
                continue
            namespace_name, _namespace_span = declared
            register_qualifier(
                namespace_name,
                target_path=target_path,
                kind="namespace",
                selected=selected,
                span=statement.span,
            )

        legacy_selective_mode = any(
            statement.names is not None
            for statement, _target in imports
        )
        constrained_bare_mode = (
            graph_has_alias
            or graph_has_package
            or legacy_selective_mode
        )
        allowed_bare: set[ModuleFunctionId] = set()

        if constrained_bare_mode:
            for statement, target_path in imports:
                if statement.alias is not None or statement.package:
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
                importer = label(module_path)
                if qualified_import is None:
                    if graph_has_namespace or graph_has_package:
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
                target_label = label(target_path)
                pair = direct.get(
                    target_path,
                    {},
                ).get(node.name)
                if pair is None:
                    if qualifier_kind == "package":
                        message = (
                            f"function {node.name!r} is not exported by "
                            f"package {node.qualifier!r}"
                        )
                    else:
                        owner_kind = (
                            "aliased"
                            if qualifier_kind == "alias"
                            else "namespaced"
                        )
                        message = (
                            f"function {node.name!r} is not declared by "
                            f"{owner_kind} module {target_label}"
                        )
                    raise ModuleError(
                        message,
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
                    qualifier_label = {
                        "alias": "module alias",
                        "namespace": "module namespace",
                        "package": "package import",
                    }[qualifier_kind]
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
                importer = label(module_path)
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
                owner = label(target_path)
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
                importer = label(module_path)
                if (
                    legacy_selective_mode
                    and not graph_has_alias
                    and not graph_has_package
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

    manifests_by_root: dict[Path, PackageManifest] = {}
    project_root_by_path: dict[Path, Path] = {
        entry: project_root,
    }

    def project_packages(owner_root: Path) -> PackageManifest:
        cached = manifests_by_root.get(owner_root)
        if cached is not None:
            return cached
        manifest = load_package_manifest(
            owner_root,
            require=True,
        )
        manifests_by_root[owner_root] = manifest
        return manifest

    def resolve_import(
        statement: ImportStatement,
        importer: Path,
    ) -> tuple[Path, Path]:
        importer_root = project_root_by_path.get(importer)
        if importer_root is None:
            raise RuntimeError(
                "module project root was not registered"
            )

        if statement.package:
            try:
                reference = resolve_package_reference(
                    importer_root,
                    statement.path,
                    manifest=project_packages(importer_root),
                )
            except (PackageManifestError, PackageReferenceError) as exc:
                raise ModuleError(
                    str(exc),
                    span=statement.span,
                ) from exc

            manifests_by_root.setdefault(
                reference.project_root,
                reference.manifest,
            )
            try:
                candidate = package_entry_path(
                    reference.project_root,
                    reference.declaration,
                )
            except PackageManifestError as exc:
                raise ModuleError(
                    str(exc),
                    span=statement.span,
                ) from exc

            if not _inside_root(
                candidate,
                reference.project_root,
            ):
                raise ModuleError(
                    "package entry escapes its owning project root",
                    span=statement.span,
                )

            if not candidate.is_file():
                raise ModuleError(
                    (
                        "package entry does not exist: "
                        f"{reference.declaration.entry}"
                    ),
                    span=statement.span,
                )

            return candidate, reference.project_root

        raw = Path(statement.path)

        if raw.is_absolute():
            raise ModuleError(
                "import path must be relative",
                span=statement.span,
            )

        candidate = (importer.parent / raw).resolve()

        if not _inside_root(candidate, importer_root):
            raise ModuleError(
                "import path escapes the owning project root",
                span=statement.span,
            )
        candidate_project_root = module_root_for(candidate)
        if (
            (candidate_project_root / "vectis.toml").is_file()
            and candidate_project_root != importer_root
        ):
            raise ModuleError(
                "import path crosses a project boundary; use a package import",
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

        return candidate, importer_root

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
                module_label_for(item, project_root)
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

        resolved_items: list[tuple[ImportStatement, Path]] = []
        for statement in imports:
            target, target_root = resolve_import(
                statement,
                module_path,
            )
            existing_root = project_root_by_path.get(target)
            if existing_root is not None and existing_root != target_root:
                raise ModuleError(
                    "one source module resolved to multiple project roots",
                    span=statement.span,
                )
            project_root_by_path[target] = target_root
            resolved_items.append((statement, target))
        resolved = tuple(resolved_items)
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

    for owner_root in sorted(
        manifests_by_root,
        key=lambda item: module_label_for(item, project_root),
    ):
        validate_package_composition(
            program_by_path,
            root=owner_root,
            imports_by_path=resolved_imports,
            manifest=manifests_by_root[owner_root],
        )

    if entry_program is None:
        raise RuntimeError("module loader did not produce an entry program")

    module_labels = {
        module_path: module_label_for(module_path, project_root)
        for module_path in program_by_path
    }
    function_scope = resolve_module_function_scope(
        program_by_path,
        root=project_root,
        imports_by_path=resolved_imports,
        module_labels=module_labels,
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
