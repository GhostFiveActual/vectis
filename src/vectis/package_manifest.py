# GHOST FIVE // VECTIS
# Parses deterministic project-local package declarations from vectis.toml.
"""Project package metadata for VECTIS."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import re
import tomllib


_PACKAGE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class PackageManifestError(ValueError):
    """Raised when project package metadata is invalid."""


@dataclass(frozen=True, slots=True, order=True)
class PackageDeclaration:
    """One project-local package entry point."""

    name: str
    entry: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not _PACKAGE_NAME.fullmatch(self.name):
            raise ValueError("PackageDeclaration.name must be a VECTIS identifier")
        if self.name in {"true", "false"}:
            raise ValueError(
                "PackageDeclaration.name cannot be a boolean literal name"
            )
        if not isinstance(self.entry, str) or not self.entry:
            raise ValueError("PackageDeclaration.entry must not be empty")


@dataclass(frozen=True, slots=True)
class PackageManifest:
    """Validated package entries from one VECTIS project manifest."""

    packages: tuple[PackageDeclaration, ...] = ()

    def package(self, name: str) -> PackageDeclaration | None:
        """Return one package declaration by exact name."""
        for item in self.packages:
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
                f"package {name!r} must be a table with one entry field"
            )
        if set(specification) != {"entry"}:
            raise PackageManifestError(
                f"package {name!r} must define exactly the entry field"
            )

        entry = _validate_entry(
            name,
            specification["entry"],
        )
        declaration = PackageDeclaration(
            name=name,
            entry=entry,
        )
        package_entry_path(
            project_root,
            declaration,
        )
        declarations.append(declaration)

    return PackageManifest(
        packages=tuple(declarations),
    )


__all__ = [
    "PackageDeclaration",
    "PackageManifest",
    "PackageManifestError",
    "load_package_manifest",
    "package_entry_path",
]
