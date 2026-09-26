# GHOST FIVE // VECTIS
# Parses deterministic project-local package declarations from vectis.toml.
"""Project package metadata for VECTIS."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import re
import tomllib


_PACKAGE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PACKAGE_VERSION = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$"
)
_PACKAGE_FINGERPRINT = re.compile(r"^[0-9a-f]{64}$")


class PackageManifestError(ValueError):
    """Raised when project package metadata is invalid."""


@dataclass(frozen=True, slots=True, order=True)
class PackageDeclaration:
    """One project-local package entry point and composition contract."""

    name: str
    entry: str
    version: str | None = None
    dependencies: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not _PACKAGE_NAME.fullmatch(self.name):
            raise ValueError("PackageDeclaration.name must be a VECTIS identifier")
        if self.name in {"true", "false"}:
            raise ValueError(
                "PackageDeclaration.name cannot be a boolean literal name"
            )
        if not isinstance(self.entry, str) or not self.entry:
            raise ValueError("PackageDeclaration.entry must not be empty")
        if self.version is not None and (
            not isinstance(self.version, str)
            or not _PACKAGE_VERSION.fullmatch(self.version)
        ):
            raise ValueError(
                "PackageDeclaration.version must use MAJOR.MINOR.PATCH"
            )
        if not isinstance(self.dependencies, tuple):
            raise TypeError("PackageDeclaration.dependencies must be tuple")
        for dependency in self.dependencies:
            if (
                not isinstance(dependency, tuple)
                or len(dependency) != 2
                or not all(isinstance(item, str) for item in dependency)
            ):
                raise TypeError(
                    "PackageDeclaration.dependencies must contain name/version pairs"
                )

    def dependency(self, name: str) -> str | None:
        """Return the exact required version for one direct dependency."""
        for dependency_name, version in self.dependencies:
            if dependency_name == name:
                return version
        return None


@dataclass(frozen=True, slots=True, order=True)
class LocalDependencyDeclaration:
    """One explicitly pinned package from another local VECTIS project."""

    name: str
    project: str
    package: str
    version: str
    fingerprint: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not _PACKAGE_NAME.fullmatch(self.name):
            raise ValueError(
                "LocalDependencyDeclaration.name must be a VECTIS identifier"
            )
        if self.name in {"true", "false"}:
            raise ValueError(
                "LocalDependencyDeclaration.name cannot be a boolean literal name"
            )
        if not isinstance(self.project, str) or not self.project:
            raise ValueError("LocalDependencyDeclaration.project must not be empty")
        if not isinstance(self.package, str) or not _PACKAGE_NAME.fullmatch(self.package):
            raise ValueError(
                "LocalDependencyDeclaration.package must be a VECTIS identifier"
            )
        if self.package in {"true", "false"}:
            raise ValueError(
                "LocalDependencyDeclaration.package cannot be a boolean literal name"
            )
        if not isinstance(self.version, str) or not _PACKAGE_VERSION.fullmatch(
            self.version
        ):
            raise ValueError(
                "LocalDependencyDeclaration.version must use MAJOR.MINOR.PATCH"
            )
        if not isinstance(self.fingerprint, str) or not _PACKAGE_FINGERPRINT.fullmatch(
            self.fingerprint
        ):
            raise ValueError(
                "LocalDependencyDeclaration.fingerprint must be lowercase SHA-256"
            )


@dataclass(frozen=True, slots=True)
class PackageManifest:
    """Validated package entries from one VECTIS project manifest."""

    packages: tuple[PackageDeclaration, ...] = ()
    local_dependencies: tuple[LocalDependencyDeclaration, ...] = ()

    def package(self, name: str) -> PackageDeclaration | None:
        """Return one package declaration by exact name."""
        for item in self.packages:
            if item.name == name:
                return item
        return None

    def local_dependency(self, name: str) -> LocalDependencyDeclaration | None:
        """Return one explicitly pinned local dependency by alias."""
        for item in self.local_dependencies:
            if item.name == name:
                return item
        return None


def _inside_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _validate_entry(name: str, entry: object) -> str:
    if not isinstance(entry, str) or not entry:
        raise PackageManifestError(
            f"package {name!r} entry must be a non-empty string"
        )
    if "\\" in entry:
        raise PackageManifestError(
            f"package {name!r} entry must use forward-slash path syntax"
        )
    if ":" in entry:
        raise PackageManifestError(
            f"package {name!r} entry must be a canonical project-relative path"
        )
    parts = entry.split("/")
    if (
        entry.startswith("/")
        or not parts
        or any(part in {"", ".", ".."} for part in parts)
    ):
        raise PackageManifestError(
            f"package {name!r} entry must be a canonical project-relative path"
        )
    relative = PurePosixPath(entry)
    if relative.suffix != ".vectis":
        raise PackageManifestError(
            f"package {name!r} entry must reference a .vectis source file"
        )
    return relative.as_posix()


def _validate_local_project_path(name: str, value: object) -> str:
    if not isinstance(value, str) or not value:
        raise PackageManifestError(
            f"local dependency {name!r} project must be a non-empty string"
        )
    if "\\" in value or ":" in value or value.startswith("/"):
        raise PackageManifestError(
            f"local dependency {name!r} project must be a canonical relative path"
        )
    parts = value.split("/")
    if not parts or any(part in {"", "."} for part in parts):
        raise PackageManifestError(
            f"local dependency {name!r} project must be a canonical relative path"
        )
    seen_normal = False
    for part in parts:
        if part == "..":
            if seen_normal:
                raise PackageManifestError(
                    f"local dependency {name!r} project must be a canonical relative path"
                )
            continue
        seen_normal = True
    relative = PurePosixPath(value)
    if relative.as_posix() == ".":
        raise PackageManifestError(
            f"local dependency {name!r} project must reference another project"
        )
    return relative.as_posix()


def _validate_fingerprint(label: str, value: object) -> str:
    if not isinstance(value, str) or not _PACKAGE_FINGERPRINT.fullmatch(value):
        raise PackageManifestError(
            f"{label} fingerprint must be 64 lowercase SHA-256 hex characters"
        )
    return value


def _validate_version(label: str, value: object) -> str:
    if not isinstance(value, str) or not _PACKAGE_VERSION.fullmatch(value):
        raise PackageManifestError(
            f"{label} version must use MAJOR.MINOR.PATCH"
        )
    return value


def _validate_dependencies(
    package_name: str,
    value: object,
) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, dict):
        raise PackageManifestError(
            f"package {package_name!r} dependencies must be a table"
        )

    dependencies: list[tuple[str, str]] = []
    for dependency_name in sorted(value):
        if (
            not isinstance(dependency_name, str)
            or not _PACKAGE_NAME.fullmatch(dependency_name)
            or dependency_name in {"true", "false"}
        ):
            raise PackageManifestError(
                f"package {package_name!r} dependency name "
                f"{dependency_name!r} must be a VECTIS identifier"
            )
        required_version = _validate_version(
            f"package {package_name!r} dependency {dependency_name!r}",
            value[dependency_name],
        )
        dependencies.append(
            (dependency_name, required_version)
        )
    return tuple(dependencies)


def _validate_dependency_graph(
    declarations: tuple[PackageDeclaration, ...],
    local_dependencies: tuple[LocalDependencyDeclaration, ...],
) -> None:
    by_name = {
        declaration.name: declaration
        for declaration in declarations
    }
    external_by_name = {
        declaration.name: declaration
        for declaration in local_dependencies
    }

    for declaration in declarations:
        for dependency_name, required_version in declaration.dependencies:
            if dependency_name == declaration.name:
                raise PackageManifestError(
                    f"package {declaration.name!r} cannot depend on itself"
                )
            target = by_name.get(dependency_name)
            if target is not None:
                if target.version is None:
                    raise PackageManifestError(
                        f"package {declaration.name!r} dependency "
                        f"{dependency_name!r} requires version {required_version!r}, "
                        f"but package {dependency_name!r} has no version"
                    )
                if target.version != required_version:
                    raise PackageManifestError(
                        f"package {declaration.name!r} dependency "
                        f"{dependency_name!r} requires version {required_version!r}, "
                        f"found {target.version!r}"
                    )
                continue

            external = external_by_name.get(dependency_name)
            if external is None:
                raise PackageManifestError(
                    f"package {declaration.name!r} dependency "
                    f"{dependency_name!r} is not declared"
                )
            if external.version != required_version:
                raise PackageManifestError(
                    f"package {declaration.name!r} dependency "
                    f"{dependency_name!r} requires version {required_version!r}, "
                    f"local dependency pins {external.version!r}"
                )

    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(name: str) -> None:
        state[name] = 1
        stack.append(name)
        declaration = by_name[name]
        for dependency_name, _version in declaration.dependencies:
            if dependency_name not in by_name:
                continue
            dependency_state = state.get(dependency_name, 0)
            if dependency_state == 0:
                visit(dependency_name)
                continue
            if dependency_state == 1:
                start = stack.index(dependency_name)
                cycle = [*stack[start:], dependency_name]
                raise PackageManifestError(
                    "package dependency cycle is not allowed: "
                    + " -> ".join(cycle)
                )
        stack.pop()
        state[name] = 2

    for name in sorted(by_name):
        if state.get(name, 0) == 0:
            visit(name)


def package_entry_path(
    root: Path,
    declaration: PackageDeclaration,
) -> Path:
    """Resolve one validated package entry below its project root."""
    project_root = root.expanduser().resolve()
    relative = PurePosixPath(declaration.entry)
    candidate = project_root.joinpath(*relative.parts).resolve(strict=False)
    if not _inside_root(candidate, project_root):
        raise PackageManifestError(
            f"package {declaration.name!r} entry escapes the project root"
        )
    return candidate


def local_dependency_project_path(
    root: Path,
    declaration: LocalDependencyDeclaration,
) -> Path:
    """Resolve an explicitly declared local dependency project path."""
    project_root = root.expanduser().resolve()
    relative = PurePosixPath(declaration.project)
    candidate = project_root.joinpath(*relative.parts).resolve(strict=False)
    if candidate == project_root:
        raise PackageManifestError(
            f"local dependency {declaration.name!r} must reference another project"
        )
    return candidate


def load_package_manifest(
    root: Path,
    *,
    require: bool = False,
) -> PackageManifest:
    """Load deterministic package declarations from project vectis.toml."""
    project_root = root.expanduser().resolve()
    manifest_path = project_root / "vectis.toml"
    if not manifest_path.is_file():
        if require:
            raise PackageManifestError(
                "package imports require vectis.toml at the project root"
            )
        return PackageManifest()

    try:
        data = tomllib.loads(
            manifest_path.read_text(encoding="utf-8")
        )
    except tomllib.TOMLDecodeError as exc:
        raise PackageManifestError(
            f"vectis.toml contains invalid TOML: {exc}"
        ) from exc
    except (OSError, UnicodeError) as exc:
        raise PackageManifestError(
            f"vectis.toml could not be read: {type(exc).__name__}"
        ) from exc

    raw_packages = data.get("packages", {})
    if not isinstance(raw_packages, dict):
        raise PackageManifestError(
            "vectis.toml [packages] must be a table"
        )
    raw_local_dependencies = data.get("local_dependencies", {})
    if not isinstance(raw_local_dependencies, dict):
        raise PackageManifestError(
            "vectis.toml [local_dependencies] must be a table"
        )

    local_dependencies: list[LocalDependencyDeclaration] = []
    for name in sorted(raw_local_dependencies):
        if (
            not isinstance(name, str)
            or not _PACKAGE_NAME.fullmatch(name)
            or name in {"true", "false"}
        ):
            raise PackageManifestError(
                f"local dependency name {name!r} must be a VECTIS identifier"
            )
        specification = raw_local_dependencies[name]
        if not isinstance(specification, dict):
            raise PackageManifestError(
                f"local dependency {name!r} must be a table"
            )
        expected = {"project", "package", "version", "fingerprint"}
        if set(specification) != expected:
            raise PackageManifestError(
                f"local dependency {name!r} must define exactly "
                "project, package, version, and fingerprint"
            )
        package_name = specification["package"]
        if (
            not isinstance(package_name, str)
            or not _PACKAGE_NAME.fullmatch(package_name)
            or package_name in {"true", "false"}
        ):
            raise PackageManifestError(
                f"local dependency {name!r} package must be a VECTIS identifier"
            )
        local_dependencies.append(
            LocalDependencyDeclaration(
                name=name,
                project=_validate_local_project_path(
                    name, specification["project"]
                ),
                package=package_name,
                version=_validate_version(
                    f"local dependency {name!r}", specification["version"]
                ),
                fingerprint=_validate_fingerprint(
                    f"local dependency {name!r}", specification["fingerprint"]
                ),
            )
        )

    declarations: list[PackageDeclaration] = []
    for name in sorted(raw_packages):
        if (
            not isinstance(name, str)
            or not _PACKAGE_NAME.fullmatch(name)
            or name in {"true", "false"}
        ):
            raise PackageManifestError(
                f"package name {name!r} must be a VECTIS identifier"
            )

        specification = raw_packages[name]
        if not isinstance(specification, dict):
            raise PackageManifestError(
                f"package {name!r} must be a table"
            )
        supported = {"entry", "version", "dependencies"}
        unsupported = sorted(set(specification) - supported)
        if unsupported:
            raise PackageManifestError(
                f"package {name!r} has unsupported fields: "
                + ", ".join(unsupported)
            )
        if "entry" not in specification:
            raise PackageManifestError(
                f"package {name!r} must define the entry field"
            )

        entry = _validate_entry(
            name,
            specification["entry"],
        )
        version = (
            None
            if "version" not in specification
            else _validate_version(
                f"package {name!r}",
                specification["version"],
            )
        )
        dependencies = _validate_dependencies(
            name,
            specification.get("dependencies", {}),
        )
        declaration = PackageDeclaration(
            name=name,
            entry=entry,
            version=version,
            dependencies=dependencies,
        )
        package_entry_path(
            project_root,
            declaration,
        )
        declarations.append(declaration)

    package_names = {item.name for item in declarations}
    local_names = {item.name for item in local_dependencies}
    collisions = sorted(package_names & local_names)
    if collisions:
        raise PackageManifestError(
            "package names and local dependency aliases must not collide: "
            + ", ".join(collisions)
        )

    manifest = PackageManifest(
        packages=tuple(declarations),
        local_dependencies=tuple(local_dependencies),
    )
    _validate_dependency_graph(
        manifest.packages,
        manifest.local_dependencies,
    )
    return manifest


__all__ = [
    "LocalDependencyDeclaration",
    "PackageDeclaration",
    "PackageManifest",
    "PackageManifestError",
    "load_package_manifest",
    "local_dependency_project_path",
    "package_entry_path",
]
