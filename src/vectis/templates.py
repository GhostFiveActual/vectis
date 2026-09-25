# GHOST FIVE // VECTIS
# Provides deterministic built-in project templates without remote discovery.
"""Built-in VECTIS project templates."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path, PurePosixPath


TEMPLATE_SCHEMA = "vectis.project-templates/v1"

_BRAND_BLOCK = """<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->
"""


@dataclass(frozen=True, slots=True)
class ProjectTemplate:
    """One deterministic built-in project template."""

    id: str
    title: str
    description: str
    files: tuple[tuple[str, str], ...]


_TEMPLATES = (
    ProjectTemplate(
        id="starter",
        title="Starter Project",
        description="A small mission with one reusable pure function.",
        files=(
            (
                "README.md",
                _BRAND_BLOCK
                + "\n# VECTIS Starter Project\n\n"
                + "Validate the project with `vectis test .`.\n",
            ),
            (
                "vectis.toml",
                "# GHOST FIVE // VECTIS\n"
                "# Project metadata for the starter template.\n"
                "[project]\n"
                'name = "vectis-starter"\n'
                'mission_root = "missions"\n'
                "\n"
                "[packages.readiness]\n"
                'entry = "lib/readiness.vectis"\n'
                'version = "1.0.0"\n',
            ),
            (
                "actions.example.toml",
                "# GHOST FIVE // VECTIS\n"
                "# Explicit action authority example. Never loaded automatically.\n"
                "[actions.filesystem]\n"
                'roots = ["."]\n',
            ),
            (
                "lib/readiness.vectis",
                "// GHOST FIVE // VECTIS\n"
                "// Reusable readiness function.\n"
                "function readiness_status(ready) {\n"
                '    return if_else(ready, "READY", "REVIEW");\n'
                "}\n",
            ),
            (
                "missions/main.vectis",
                "// GHOST FIVE // VECTIS\n"
                "// Starter mission.\n"
                'import package "readiness";\n'
                "\n"
                'mission "Starter mission" {\n'
                "    source ready true;\n"
                "    let status readiness.readiness_status(ready);\n"
                "    publish status;\n"
                "}\n",
            ),
        ),
    ),
    ProjectTemplate(
        id="release-gate",
        title="Release Gate",
        description="A staged deterministic release decision workflow.",
        files=(
            (
                "README.md",
                _BRAND_BLOCK
                + "\n# Release Gate Template\n\n"
                + "A staged release decision project with no external authority.\n",
            ),
            (
                "vectis.toml",
                "# GHOST FIVE // VECTIS\n"
                "# Project metadata for the release gate template.\n"
                "[project]\n"
                'name = "vectis-release-gate"\n'
                'mission_root = "missions"\n',
            ),
            (
                "missions/release-gate.vectis",
                "// GHOST FIVE // VECTIS\n"
                "// Deterministic staged release gate.\n"
                'mission "Release gate" {\n'
                '    stage "Inputs" {\n'
                "        source ready true;\n"
                "        source quality 96;\n"
                "    }\n"
                '    stage "Decision" {\n'
                "        let approved ready && quality >= 90;\n"
                "        when approved {\n"
                '            publish "READY";\n'
                "        } otherwise {\n"
                '            publish "REVIEW";\n'
                "        }\n"
                "    }\n"
                "}\n",
            ),
        ),
    ),
    ProjectTemplate(
        id="filesystem-action",
        title="Filesystem Action",
        description="An explicit filesystem action with a reviewable profile example.",
        files=(
            (
                "README.md",
                _BRAND_BLOCK
                + "\n# Filesystem Action Template\n\n"
                + "Review the example action profile before selecting it for execution.\n",
            ),
            (
                "vectis.toml",
                "# GHOST FIVE // VECTIS\n"
                "# Project metadata for the filesystem action template.\n"
                "[project]\n"
                'name = "vectis-filesystem-action"\n'
                'mission_root = "missions"\n',
            ),
            (
                "actions.example.toml",
                "# GHOST FIVE // VECTIS\n"
                "# Explicit local filesystem authority example.\n"
                "[actions.filesystem]\n"
                'roots = ["workspace"]\n',
            ),
            (
                "missions/read-file.vectis",
                "// GHOST FIVE // VECTIS\n"
                "// Filesystem action template mission.\n"
                'mission "Read file" {\n'
                '    action content "filesystem.read_text" '
                'using "filesystem" {path: "input.txt"};\n'
                "    publish content;\n"
                "}\n",
            ),
        ),
    ),
)


def template_catalog() -> dict[str, object]:
    """Return deterministic metadata for every built-in template."""
    return {
        "schema": TEMPLATE_SCHEMA,
        "templates": [
            {
                "id": template.id,
                "title": template.title,
                "description": template.description,
                "file_count": len(template.files),
                "files": [
                    path
                    for path, _content in template.files
                ],
            }
            for template in sorted(
                _TEMPLATES,
                key=lambda item: item.id,
            )
        ],
    }


def template_preview(name: str) -> dict[str, object]:
    """Return one deterministic template including file content and hashes."""
    template = _template(name)
    return {
        "schema": TEMPLATE_SCHEMA,
        "id": template.id,
        "title": template.title,
        "description": template.description,
        "files": [
            {
                "path": path,
                "content": content,
                "sha256": hashlib.sha256(
                    content.encode("utf-8")
                ).hexdigest(),
            }
            for path, content in template.files
        ],
    }


def write_project_template(
    name: str,
    root: str | Path,
    *,
    force: bool = False,
) -> tuple[Path, ...]:
    """Materialize one built-in template without remote discovery."""
    template = _template(name)
    destination_root = Path(root).expanduser().resolve()
    destination_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    planned: list[tuple[Path, str]] = []
    for relative_name, content in template.files:
        relative = PurePosixPath(relative_name)
        if (
            relative.is_absolute()
            or not relative.parts
            or any(
                part in {"", ".", ".."}
                for part in relative.parts
            )
        ):
            raise ValueError(
                f"unsafe template path: {relative_name!r}"
            )

        raw_destination = destination_root.joinpath(
            *relative.parts
        )
        if raw_destination.is_symlink():
            raise ValueError(
                "template destination must not be a symlink: "
                f"{raw_destination}"
            )
        destination = raw_destination.resolve(
            strict=False
        )
        try:
            destination.relative_to(destination_root)
        except ValueError as exc:
            raise ValueError(
                f"template path escapes destination: {relative_name!r}"
            ) from exc

        if destination.exists() and not force:
            raise FileExistsError(
                f"{destination} already exists; use --force to replace template files"
            )
        planned.append((destination, content))

    created: list[Path] = []
    for destination, content in planned:
        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        destination.write_text(
            content,
            encoding="utf-8",
        )
        created.append(destination)

    return tuple(created)


def _template(name: str) -> ProjectTemplate:
    if not isinstance(name, str) or not name.strip():
        raise ValueError(
            "template name must be a non-empty string"
        )
    for template in _TEMPLATES:
        if template.id == name:
            return template
    raise ValueError(
        f"unknown VECTIS project template: {name!r}"
    )


__all__ = [
    "ProjectTemplate",
    "TEMPLATE_SCHEMA",
    "template_catalog",
    "template_preview",
    "write_project_template",
]
