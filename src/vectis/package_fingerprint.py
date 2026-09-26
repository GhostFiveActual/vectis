# GHOST FIVE // VECTIS
# Produces deterministic content fingerprints for project-local VECTIS packages.
"""Portable package descriptors and SHA-256 fingerprints for VECTIS."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping

from vectis.ast import ImportStatement
from vectis.diagnostic import DiagnosticError
from vectis.package_manifest import (
    PackageDeclaration,
    PackageManifest,
    PackageManifestError,
    load_package_manifest,
    local_dependency_project_path,
    package_entry_path,
)
from vectis.parser import parse


PACKAGE_FINGERPRINT_SCHEMA = "vectis.package-fingerprint/v1"


class PackageFingerprintError(ValueError):
    """Raised when a package fingerprint cannot be derived safely."""


@dataclass(frozen=True, slots=True)
class _ImplementationFile:
    path: str
    source_sha256: str


def _inside_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _source_project_root(path: Path) -> Path:
    source = path.expanduser().resolve(strict=False)
    start = source.parent if source.suffix else source
    for candidate in (start, *start.parents):
        if (candidate / "vectis.toml").is_file():
            return candidate
    return source.parent if source.suffix else source


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _normalize_source(source: str) -> str:
    return source.replace("\r\n", "\n").replace("\r", "\n")


def _source_hash(source: str) -> str:
    payload = _normalize_source(source).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _canonical_fingerprint(value: Mapping[str, object]) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _overlay_sources(
    overlays: Mapping[Path, str] | None,
) -> dict[Path, str]:
    result: dict[Path, str] = {}
    for path, source in (overlays or {}).items():
        if not isinstance(path, Path):
            raise TypeError("package fingerprint overlay keys must be Path")
        if not isinstance(source, str):
            raise TypeError("package fingerprint overlay values must be str")
        result[path.expanduser().resolve()] = source
    return result


def _source_for(
    path: Path,
    *,
    root: Path,
    overlays: Mapping[Path, str],
) -> str:
    source = overlays.get(path)
    if source is not None:
        return source
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise PackageFingerprintError(
            f"package source does not exist: {_relative(path, root)}"
        ) from exc
    except (OSError, UnicodeError) as exc:
        raise PackageFingerprintError(
            "package source could not be read: "
            f"{_relative(path, root)} ({type(exc).__name__})"
        ) from exc


def _exists(path: Path, overlays: Mapping[Path, str]) -> bool:
    return path in overlays or path.is_file()


def _resolve_path_import(
    importer: Path,
    value: str,
    *,
    root: Path,
    overlays: Mapping[Path, str],
) -> Path:
    raw = Path(value)
    if raw.is_absolute():
        raise PackageFingerprintError(
            "package implementation import path must be relative"
        )

    candidate = (importer.parent / raw).resolve(strict=False)
    if not _inside_root(candidate, root):
        raise PackageFingerprintError(
            "package implementation import path escapes the project root"
        )
    candidate_root = _source_project_root(candidate)
    if (candidate_root / "vectis.toml").is_file() and candidate_root != root:
        raise PackageFingerprintError(
            "package implementation import path crosses a project boundary"
        )
    if candidate.suffix != ".vectis":
        raise PackageFingerprintError(
            "package implementation import path must reference a .vectis source file"
        )
    if not _exists(candidate, overlays):
        raise PackageFingerprintError(
            "package implementation import does not exist: "
            + _relative(candidate, root)
        )
    return candidate


def _implementation_files(
    root: Path,
    declaration: PackageDeclaration,
    *,
    overlays: Mapping[Path, str],
) -> tuple[_ImplementationFile, ...]:
    entry = package_entry_path(root, declaration)
    if not _exists(entry, overlays):
        raise PackageFingerprintError(
            f"package {declaration.name!r} entry does not exist: {declaration.entry}"
        )

    visited: set[Path] = set()
    visiting: list[Path] = []
    files: list[_ImplementationFile] = []

    def visit(path: Path) -> None:
        if path in visited:
            return
        if path in visiting:
            start = visiting.index(path)
            cycle = [*visiting[start:], path]
            raise PackageFingerprintError(
                "package implementation import cycle is not allowed: "
                + " -> ".join(_relative(item, root) for item in cycle)
            )

        source = _source_for(
            path,
            root=root,
            overlays=overlays,
        )
        try:
            program = parse(
                source,
                file=_relative(path, root),
            )
        except DiagnosticError as exc:
            raise PackageFingerprintError(
                "package source cannot be parsed for fingerprinting: "
                + _relative(path, root)
            ) from exc

        visiting.append(path)
        for statement in program.statements:
            if not isinstance(statement, ImportStatement):
                continue
            if statement.package:
                if declaration.dependency(statement.path) is None:
                    raise PackageFingerprintError(
                        f"package {declaration.name!r} imports package "
                        f"{statement.path!r} without a dependency contract"
                    )
                continue
            target = _resolve_path_import(
                path,
                statement.path,
                root=root,
                overlays=overlays,
            )
            visit(target)

        visiting.pop()
        visited.add(path)
        files.append(
            _ImplementationFile(
                path=_relative(path, root),
                source_sha256=_source_hash(source),
            )
        )

    visit(entry)
    return tuple(sorted(files, key=lambda item: item.path))


def package_descriptor(
    root: Path,
    package_name: str,
    *,
    overlays: Mapping[Path, str] | None = None,
    manifest: PackageManifest | None = None,
) -> dict[str, object]:
    """Return the canonical content descriptor for one local package."""
    if not isinstance(root, Path):
        raise TypeError("package fingerprint root must be Path")
    if manifest is not None and not isinstance(manifest, PackageManifest):
        raise TypeError("package fingerprint manifest must be PackageManifest")

    project_root = root.expanduser().resolve()
    overlay_map = _overlay_sources(overlays)
    manifest_cache: dict[Path, PackageManifest] = {}

    try:
        root_manifest = (
            load_package_manifest(project_root, require=True)
            if manifest is None
            else manifest
        )
    except PackageManifestError as exc:
        raise PackageFingerprintError(str(exc)) from exc
    manifest_cache[project_root] = root_manifest

    declaration = root_manifest.package(package_name)
    if declaration is None:
        raise PackageFingerprintError(
            f"unknown package {package_name!r}"
        )

    fingerprint_cache: dict[tuple[Path, str], str] = {}
    descriptor_cache: dict[tuple[Path, str], dict[str, object]] = {}
    stack: list[tuple[Path, str]] = []

    def manifest_for(current_root: Path) -> PackageManifest:
        cached = manifest_cache.get(current_root)
        if cached is not None:
            return cached
        try:
            loaded = load_package_manifest(
                current_root,
                require=True,
            )
        except PackageManifestError as exc:
            raise PackageFingerprintError(str(exc)) from exc
        manifest_cache[current_root] = loaded
        return loaded

    def external_target(
        current_root: Path,
        current_manifest: PackageManifest,
        dependency_name: str,
    ) -> tuple[Path, PackageManifest, PackageDeclaration, str]:
        binding = current_manifest.local_dependency(dependency_name)
        if binding is None:
            raise PackageFingerprintError(
                f"package dependency {dependency_name!r} is not declared"
            )
        try:
            target_root = local_dependency_project_path(
                current_root,
                binding,
            )
        except PackageManifestError as exc:
            raise PackageFingerprintError(str(exc)) from exc
        if not target_root.is_dir():
            raise PackageFingerprintError(
                f"local dependency {binding.name!r} project does not exist: "
                f"{binding.project}"
            )
        target_manifest = manifest_for(target_root)
        target = target_manifest.package(binding.package)
        if target is None:
            raise PackageFingerprintError(
                f"local dependency {binding.name!r} target package "
                f"{binding.package!r} is not declared"
            )
        if target.version != binding.version:
            raise PackageFingerprintError(
                f"local dependency {binding.name!r} requires version "
                f"{binding.version!r}, found {target.version!r}"
            )
        return target_root, target_manifest, target, binding.fingerprint

    def build(current_root: Path, name: str) -> dict[str, object]:
        key = (current_root, name)
        cached = descriptor_cache.get(key)
        if cached is not None:
            return cached
        if key in stack:
            start_index = stack.index(key)
            cycle = [*stack[start_index:], key]
            raise PackageFingerprintError(
                "package fingerprint dependency cycle is not allowed: "
                + " -> ".join(item_name for _item_root, item_name in cycle)
            )

        current_manifest = manifest_for(current_root)
        item = current_manifest.package(name)
        if item is None:
            raise PackageFingerprintError(
                f"unknown package {name!r}"
            )

        stack.append(key)
        try:
            try:
                implementation = _implementation_files(
                    current_root,
                    item,
                    overlays=overlay_map,
                )
            except PackageManifestError as exc:
                raise PackageFingerprintError(str(exc)) from exc

            dependencies: list[dict[str, object]] = []
            for dependency_name, required_version in item.dependencies:
                local_target = current_manifest.package(dependency_name)
                expected_external_fingerprint: str | None = None
                if local_target is not None:
                    dependency_root = current_root
                    dependency_package = local_target.name
                else:
                    (
                        dependency_root,
                        _dependency_manifest,
                        external_package,
                        expected_external_fingerprint,
                    ) = external_target(
                        current_root,
                        current_manifest,
                        dependency_name,
                    )
                    dependency_package = external_package.name

                dependency_descriptor = build(
                    dependency_root,
                    dependency_package,
                )
                dependency_key = (
                    dependency_root,
                    dependency_package,
                )
                dependency_fingerprint = fingerprint_cache.get(
                    dependency_key
                )
                if dependency_fingerprint is None:
                    dependency_fingerprint = _canonical_fingerprint(
                        dependency_descriptor
                    )
                    fingerprint_cache[dependency_key] = dependency_fingerprint

                if (
                    expected_external_fingerprint is not None
                    and dependency_fingerprint != expected_external_fingerprint
                ):
                    binding = current_manifest.local_dependency(dependency_name)
                    if binding is None:
                        raise RuntimeError(
                            "local dependency binding disappeared during fingerprinting"
                        )
                    raise PackageFingerprintError(
                        f"local dependency {binding.name!r} fingerprint mismatch: "
                        f"expected {binding.fingerprint}, found {dependency_fingerprint}"
                    )

                dependencies.append(
                    {
                        "name": dependency_name,
                        "version": required_version,
                        "fingerprint": dependency_fingerprint,
                    }
                )

            descriptor: dict[str, object] = {
                "schema": PACKAGE_FINGERPRINT_SCHEMA,
                "name": item.name,
                "entry": item.entry,
                "version": item.version,
                "files": [
                    {
                        "path": source.path,
                        "sha256": source.source_sha256,
                    }
                    for source in implementation
                ],
                "dependencies": dependencies,
            }
            descriptor_cache[key] = descriptor
            fingerprint_cache[key] = _canonical_fingerprint(descriptor)
            return descriptor
        finally:
            if stack and stack[-1] == key:
                stack.pop()

    return build(project_root, declaration.name)


def package_fingerprint(
    root: Path,
    package_name: str,
    *,
    overlays: Mapping[Path, str] | None = None,
    manifest: PackageManifest | None = None,
) -> str:
    """Return the portable SHA-256 fingerprint for one local package."""
    descriptor = package_descriptor(
        root,
        package_name,
        overlays=overlays,
        manifest=manifest,
    )
    return _canonical_fingerprint(descriptor)


__all__ = [
    "PACKAGE_FINGERPRINT_SCHEMA",
    "PackageFingerprintError",
    "package_descriptor",
    "package_fingerprint",
]
