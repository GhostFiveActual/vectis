# GHOST FIVE // VECTIS
# Provides deterministic project-bounded browsing of VECTIS source modules.
"""Read-only project module browsing for VECTIS."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping

from vectis.ast import FunctionDeclaration, ImportStatement, NamespaceDeclaration
from vectis.diagnostic import DiagnosticError
from vectis.modules import module_root_for
from vectis.package_fingerprint import (
    PackageFingerprintError,
    package_fingerprint,
)
from vectis.package_manifest import (
    PackageManifestError,
    load_package_manifest,
    package_entry_path,
)
from vectis.parser import parse


MODULE_BROWSER_SCHEMA = "vectis.module-browser/v1"


def _inside_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _project_root(selection: Path) -> Path:
    selected = selection.expanduser().resolve()
    if selected.is_dir():
        return module_root_for(selected / "__vectis_browse__.vectis")
    return module_root_for(selected)


def _discover_modules(
    root: Path,
    overlays: Mapping[Path, str],
) -> tuple[tuple[Path, ...], tuple[dict[str, str], ...]]:
    paths: set[Path] = set()
    rejected: list[dict[str, str]] = []

    for directory, directory_names, file_names in os.walk(
        root,
        followlinks=False,
    ):
        current = Path(directory)
        safe_directories: list[str] = []
        for name in sorted(directory_names):
            candidate = current / name
            if candidate.is_symlink():
                rejected.append(
                    {
                        "path": _relative(candidate, root),
                        "reason": "symlink-directory",
                    }
                )
            else:
                safe_directories.append(name)
        directory_names[:] = safe_directories

        for name in sorted(file_names):
            if not name.endswith(".vectis"):
                continue
            candidate = current / name
            if candidate.is_symlink():
                rejected.append(
                    {
                        "path": _relative(candidate, root),
                        "reason": "symlink-source",
                    }
                )
                continue
            paths.add(candidate.resolve())

    for path in overlays:
        candidate = path.expanduser().resolve()
        if (
            candidate.suffix != ".vectis"
            or not _inside_root(candidate, root)
        ):
            continue
        if candidate.is_symlink():
            rejected.append(
                {
                    "path": _relative(candidate, root),
                    "reason": "symlink-source",
                }
            )
            continue
        paths.add(candidate)

    unique_rejected = {
        (item["path"], item["reason"]): item
        for item in rejected
    }
    return (
        tuple(sorted(paths, key=lambda item: _relative(item, root))),
        tuple(
            unique_rejected[key]
            for key in sorted(unique_rejected)
        ),
    )


def _safe_import_source(value: str) -> str:
    raw = Path(value)
    if raw.is_absolute():
        return "<absolute>"
    return value


def _resolve_import(
    *,
    importer: Path,
    value: str,
    root: Path,
    available: set[Path],
) -> tuple[str, str | None, str | None]:
    raw = Path(value)
    safe_source = _safe_import_source(value)

    if raw.is_absolute():
        return safe_source, None, "absolute-path"

    candidate = (importer.parent / raw).resolve(strict=False)
    if not _inside_root(candidate, root):
        return safe_source, None, "root-escape"

    target = _relative(candidate, root)
    if candidate.suffix != ".vectis":
        return safe_source, target, "invalid-extension"

    if candidate not in available:
        return safe_source, target, "missing"

    return safe_source, target, None


def _diagnostic_payload(exc: DiagnosticError) -> dict[str, object]:
    return {
        "code": exc.code,
        "severity": exc.severity,
        "message": exc.message,
        "line": exc.line,
        "column": exc.column,
    }


def _dependency_cycles(
    modules: tuple[str, ...],
    edges: tuple[tuple[str, str], ...],
) -> tuple[tuple[str, ...], ...]:
    graph = {name: [] for name in modules}
    for source, target in edges:
        graph.setdefault(source, []).append(target)
        graph.setdefault(target, [])
    for targets in graph.values():
        targets.sort()

    state: dict[str, int] = {}
    stack: list[str] = []
    found: set[tuple[str, ...]] = set()

    def canonical_cycle(cycle: list[str]) -> tuple[str, ...]:
        body = cycle[:-1]
        if not body:
            return tuple(cycle)
        rotations = [
            tuple(body[index:] + body[:index])
            for index in range(len(body))
        ]
        best = min(rotations)
        return (*best, best[0])

    def visit(name: str) -> None:
        state[name] = 1
        stack.append(name)
        for target in graph.get(name, ()):
            target_state = state.get(target, 0)
            if target_state == 0:
                visit(target)
            elif target_state == 1:
                start = stack.index(target)
                found.add(
                    canonical_cycle(
                        [*stack[start:], target]
                    )
                )
        stack.pop()
        state[name] = 2

    for name in sorted(graph):
        if state.get(name, 0) == 0:
            visit(name)

    return tuple(sorted(found))


def browse_project_modules(
    path: str | Path,
    *,
    overlays: Mapping[Path, str] | None = None,
) -> dict[str, object]:
    """Return a deterministic, project-relative source module catalog."""
    selection = Path(path)
    root = _project_root(selection)
    if not root.is_dir():
        raise ValueError("module browser project root does not exist")

    overlay_sources = {
        key.expanduser().resolve(): value
        for key, value in (overlays or {}).items()
    }
    module_paths, rejected = _discover_modules(
        root,
        overlay_sources,
    )
    available = set(module_paths)

    package_manifest = None
    package_diagnostics: list[dict[str, object]] = []
    try:
        package_manifest = load_package_manifest(root)
    except PackageManifestError as exc:
        package_diagnostics.append(
            {
                "code": "SEM006",
                "severity": "error",
                "message": str(exc),
                "line": 1,
                "column": 1,
            }
        )

    package_by_name = (
        {
            item.name: item
            for item in package_manifest.packages
        }
        if package_manifest is not None
        else {}
    )

    for declaration in package_by_name.values():
        candidate = package_entry_path(
            root,
            declaration,
        )
        if candidate not in available:
            package_diagnostics.append(
                {
                    "code": "SEM006",
                    "severity": "error",
                    "message": (
                        f"package {declaration.name!r} entry is missing: "
                        f"{declaration.entry}"
                    ),
                    "line": 1,
                    "column": 1,
                }
            )

    modules: list[dict[str, object]] = []
    resolved_edges: set[tuple[str, str]] = set()
    path_edges: set[tuple[str, str]] = set()
    package_imports_by_module: dict[str, set[str]] = {}

    for module_path in module_paths:
        relative = _relative(module_path, root)
        source = overlay_sources.get(module_path)
        if source is None:
            source = module_path.read_text(encoding="utf-8")

        try:
            program = parse(
                source,
                file=relative,
            )
        except DiagnosticError as exc:
            modules.append(
                {
                    "path": relative,
                    "status": "invalid",
                    "kind": "unknown",
                    "importable": False,
                    "imports": [],
                    "namespace": None,
                    "functions": [],
                    "executable_statement_count": 0,
                    "diagnostics": [
                        _diagnostic_payload(exc)
                    ],
                    "overlay": module_path in overlay_sources,
                }
            )
            continue

        imports: list[dict[str, object]] = []
        diagnostics: list[dict[str, object]] = []
        functions: list[dict[str, object]] = []
        executable_count = 0
        namespace_name: str | None = None
        namespaces = tuple(
            statement
            for statement in program.statements
            if isinstance(statement, NamespaceDeclaration)
        )
        if len(namespaces) > 1:
            diagnostics.append(
                {
                    "code": "SEM006",
                    "severity": "error",
                    "message": "duplicate namespace declaration",
                    "line": namespaces[1].span.start.line,
                    "column": namespaces[1].span.start.column,
                }
            )
        elif namespaces:
            declaration = namespaces[0]
            namespace_name = declaration.name
            if program.statements[0] is not declaration:
                diagnostics.append(
                    {
                        "code": "SEM006",
                        "severity": "error",
                        "message": (
                            "namespace declaration must be the first statement"
                        ),
                        "line": declaration.span.start.line,
                        "column": declaration.span.start.column,
                    }
                )

        for statement in program.statements:
            if isinstance(statement, ImportStatement):
                package_name = (
                    statement.path
                    if statement.package
                    else None
                )
                if statement.package:
                    declaration = package_by_name.get(
                        statement.path
                    )
                    source_label = (
                        f"package:{statement.path}"
                    )
                    if package_manifest is None:
                        target = None
                        issue = "package-manifest-invalid"
                    elif declaration is None:
                        target = None
                        issue = "unknown-package"
                    else:
                        candidate = package_entry_path(
                            root,
                            declaration,
                        )
                        target = declaration.entry
                        issue = (
                            None
                            if candidate in available
                            else "missing"
                        )
                else:
                    (
                        source_label,
                        target,
                        issue,
                    ) = _resolve_import(
                        importer=module_path,
                        value=statement.path,
                        root=root,
                        available=available,
                    )

                imports.append(
                    {
                        "source": source_label,
                        "target": target,
                        "package": package_name,
                        "names": (
                            None
                            if statement.names is None
                            else list(statement.names)
                        ),
                        "alias": statement.alias,
                        "status": (
                            "resolved"
                            if issue is None
                            else issue
                        ),
                    }
                )
                if target is not None and issue is None:
                    resolved_edges.add((relative, target))
                    if statement.package:
                        package_imports_by_module.setdefault(
                            relative,
                            set(),
                        ).add(statement.path)
                    else:
                        path_edges.add((relative, target))
                if issue is not None:
                    diagnostics.append(
                        {
                            "code": "SEM006",
                            "severity": "error",
                            "message": (
                                "import resolution failed: "
                                + issue
                            ),
                            "line": statement.span.start.line,
                            "column": statement.span.start.column,
                        }
                    )
            elif isinstance(statement, NamespaceDeclaration):
                continue
            elif isinstance(statement, FunctionDeclaration):
                parameter_types = (
                    statement.parameter_types
                    if statement.parameter_types
                    else tuple(
                        None
                        for _parameter
                        in statement.parameters
                    )
                )
                functions.append(
                    {
                        "name": statement.name,
                        "identity": (
                            f"{relative}::{statement.name}"
                        ),
                        "visibility": statement.visibility,
                        "parameters": list(statement.parameters),
                        "parameter_types": list(parameter_types),
                        "return_type": statement.return_type,
                    }
                )
            else:
                executable_count += 1

        status = "ok" if not diagnostics else "invalid"
        kind = "library" if executable_count == 0 else "entry"
        modules.append(
            {
                "path": relative,
                "status": status,
                "kind": kind,
                "importable": (
                    status == "ok"
                    and executable_count == 0
                ),
                "imports": imports,
                "namespace": namespace_name,
                "functions": functions,
                "executable_statement_count": executable_count,
                "diagnostics": diagnostics,
                "overlay": module_path in overlay_sources,
            }
        )

    module_names = tuple(
        item["path"]
        for item in modules
        if isinstance(item.get("path"), str)
    )
    edges = tuple(sorted(resolved_edges))
    cycles = _dependency_cycles(module_names, edges)

    if package_manifest is not None:
        path_graph: dict[str, list[str]] = {}
        for source, target in sorted(path_edges):
            path_graph.setdefault(source, []).append(target)

        for declaration in package_manifest.packages:
            if declaration.entry not in module_names:
                continue
            seen: set[str] = set()
            pending = [declaration.entry]
            while pending:
                module_name = pending.pop()
                if module_name in seen:
                    continue
                seen.add(module_name)
                for imported_package in sorted(
                    package_imports_by_module.get(module_name, set())
                ):
                    if declaration.dependency(imported_package) is None:
                        package_diagnostics.append(
                            {
                                "code": "SEM006",
                                "severity": "error",
                                "message": (
                                    f"package {declaration.name!r} imports package "
                                    f"{imported_package!r} without a dependency contract"
                                ),
                                "line": 1,
                                "column": 1,
                            }
                        )
                pending.extend(path_graph.get(module_name, ()))

    modules_by_path = {
        item["path"]: item
        for item in modules
        if isinstance(item.get("path"), str)
    }
    packages: list[dict[str, object]] = []
    for name in sorted(package_by_name):
        declaration = package_by_name[name]
        module = modules_by_path.get(declaration.entry)
        exports = (
            sorted(
                function["name"]
                for function in module["functions"]
                if (
                    function.get("visibility") == "public"
                    and isinstance(function.get("name"), str)
                )
            )
            if module is not None
            else []
        )
        fingerprint: str | None = None
        if package_manifest is not None:
            try:
                fingerprint = package_fingerprint(
                    root,
                    declaration.name,
                    overlays=overlay_sources,
                    manifest=package_manifest,
                )
            except PackageFingerprintError as exc:
                package_diagnostics.append(
                    {
                        "code": "SEM006",
                        "severity": "error",
                        "message": str(exc),
                        "line": 1,
                        "column": 1,
                    }
                )

        record: dict[str, object] = {
            "name": declaration.name,
            "entry": declaration.entry,
            "exports": exports,
        }
        if declaration.version is not None:
            record["version"] = declaration.version
        if declaration.dependencies:
            record["dependencies"] = [
                {
                    "name": dependency_name,
                    "version": version,
                }
                for dependency_name, version in declaration.dependencies
            ]
        if fingerprint is not None:
            record["fingerprint"] = fingerprint
        packages.append(record)

    return {
        "schema": MODULE_BROWSER_SCHEMA,
        "root": ".",
        "ok": (
            not rejected
            and not cycles
            and not package_diagnostics
            and all(
                item["status"] == "ok"
                for item in modules
            )
        ),
        "module_count": len(modules),
        "edge_count": len(edges),
        "package_count": len(packages),
        "packages": packages,
        "package_diagnostics": package_diagnostics,
        "modules": modules,
        "edges": [
            {
                "from": source,
                "to": target,
            }
            for source, target in edges
        ],
        "cycles": [list(cycle) for cycle in cycles],
        "rejected": list(rejected),
    }


__all__ = [
    "MODULE_BROWSER_SCHEMA",
    "browse_project_modules",
]
