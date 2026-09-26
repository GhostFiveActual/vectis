# GHOST FIVE // VECTIS
# Resolves explicit local multi-project package bindings.
"""Exact local package references across VECTIS project boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from vectis.package_fingerprint import (
    PackageFingerprintError,
    package_fingerprint,
)
from vectis.package_manifest import (
    PackageDeclaration,
    PackageManifest,
    PackageManifestError,
    load_package_manifest,
    local_dependency_project_path,
)


class PackageReferenceError(ValueError):
    """Raised when an explicit local package binding cannot be verified."""


@dataclass(frozen=True, slots=True)
class PackageReference:
    """Resolved package target and the project that owns its source."""

    alias: str
    project_root: Path
    manifest: PackageManifest
    declaration: PackageDeclaration
    external: bool = False


def resolve_package_reference(
    root: Path,
    package_name: str,
    *,
    overlays: Mapping[Path, str] | None = None,
    manifest: PackageManifest | None = None,
) -> PackageReference:
    """Resolve one local package name or exact local multi-project binding."""
    if not isinstance(root, Path):
        raise TypeError("package reference root must be Path")
    if not isinstance(package_name, str) or not package_name:
        raise TypeError("package reference name must be a non-empty str")
    if manifest is not None and not isinstance(manifest, PackageManifest):
        raise TypeError("package reference manifest must be PackageManifest")

    project_root = root.expanduser().resolve()
    try:
        source_manifest = (
            load_package_manifest(project_root, require=True)
            if manifest is None
            else manifest
        )
    except PackageManifestError as exc:
        raise PackageReferenceError(str(exc)) from exc

    local = source_manifest.package(package_name)
    if local is not None:
        return PackageReference(
            alias=package_name,
            project_root=project_root,
            manifest=source_manifest,
            declaration=local,
            external=False,
        )

    binding = source_manifest.local_dependency(package_name)
    if binding is None:
        raise PackageReferenceError(
            f"unknown package {package_name!r}"
        )

    try:
        target_root = local_dependency_project_path(
            project_root,
            binding,
        )
    except PackageManifestError as exc:
        raise PackageReferenceError(str(exc)) from exc

    if not target_root.is_dir():
        raise PackageReferenceError(
            f"local dependency {binding.name!r} project does not exist: "
            f"{binding.project}"
        )

    try:
        target_manifest = load_package_manifest(
            target_root,
            require=True,
        )
    except PackageManifestError as exc:
        raise PackageReferenceError(
            f"local dependency {binding.name!r} target manifest is invalid: {exc}"
        ) from exc

    target = target_manifest.package(binding.package)
    if target is None:
        raise PackageReferenceError(
            f"local dependency {binding.name!r} target package "
            f"{binding.package!r} is not declared"
        )
    if target.version != binding.version:
        raise PackageReferenceError(
            f"local dependency {binding.name!r} requires version "
            f"{binding.version!r}, found {target.version!r}"
        )

    try:
        actual_fingerprint = package_fingerprint(
            target_root,
            target.name,
            overlays=overlays,
            manifest=target_manifest,
        )
    except PackageFingerprintError as exc:
        raise PackageReferenceError(
            f"local dependency {binding.name!r} fingerprint could not be verified: {exc}"
        ) from exc

    if actual_fingerprint != binding.fingerprint:
        raise PackageReferenceError(
            f"local dependency {binding.name!r} fingerprint mismatch: "
            f"expected {binding.fingerprint}, found {actual_fingerprint}"
        )

    return PackageReference(
        alias=package_name,
        project_root=target_root,
        manifest=target_manifest,
        declaration=target,
        external=True,
    )


__all__ = [
    "PackageReference",
    "PackageReferenceError",
    "resolve_package_reference",
]
