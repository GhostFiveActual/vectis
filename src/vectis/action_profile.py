# GHOST FIVE // VECTIS
# Loads explicit local action authority from a user-selected TOML profile.
"""Project-local action authority profiles for the VECTIS CLI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib
from typing import Any

from vectis.actions import ActionRegistry
from vectis.adapters.filesystem import FileSystemAdapter
from vectis.adapters.http import HttpAdapter
from vectis.adapters.process import ProcessAdapter


@dataclass(frozen=True, slots=True)
class ActionProfile:
    """Resolved action handlers and capability grants from one profile."""

    source: Path
    actions: ActionRegistry
    capabilities: tuple[str, ...]
    adapters: tuple[dict[str, object], ...]


def load_action_profile(path: str | Path) -> ActionProfile:
    """Load one explicit TOML action profile without ambient discovery."""
    source = Path(path).expanduser().resolve(strict=True)

    if not source.is_file():
        raise ValueError(
            f"action profile must be a file: {source}"
        )

    try:
        data = tomllib.loads(
            source.read_text(encoding="utf-8")
        )
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(
            f"invalid action profile TOML: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(
            "action profile root must be a TOML table"
        )

    unknown_root = set(data) - {"actions"}
    if unknown_root:
        raise ValueError(
            "unsupported action profile root keys: "
            + ", ".join(sorted(unknown_root))
        )

    action_data = data.get("actions", {})
    if not isinstance(action_data, dict):
        raise ValueError(
            "[actions] must be a TOML table"
        )

    unknown_actions = set(action_data) - {
        "filesystem",
        "process",
        "http",
    }
    if unknown_actions:
        raise ValueError(
            "unsupported action profile adapters: "
            + ", ".join(sorted(unknown_actions))
        )

    registry = ActionRegistry()
    capabilities: list[str] = []
    manifest: list[dict[str, object]] = []
    base = source.parent

    filesystem = action_data.get("filesystem")
    if filesystem is not None:
        table = _table(filesystem, "actions.filesystem")
        _reject_unknown(
            table,
            {"roots"},
            "actions.filesystem",
        )
        roots = _string_list(
            table.get("roots"),
            "actions.filesystem.roots",
            required=True,
        )
        resolved_roots = tuple(
            _resolve_profile_path(base, item)
            for item in roots
        )
        registry.register_filesystem(
            FileSystemAdapter(resolved_roots)
        )
        capabilities.append("filesystem")
        manifest.append(
            {
                "capability": "filesystem",
                "roots": [
                    str(item)
                    for item in resolved_roots
                ],
            }
        )

    process = action_data.get("process")
    if process is not None:
        table = _table(process, "actions.process")
        _reject_unknown(
            table,
            {
                "executables",
                "environment",
                "default_timeout",
                "max_timeout",
            },
            "actions.process",
        )
        executables = _string_map(
            table.get("executables"),
            "actions.process.executables",
            required=True,
        )
        normalized_executables = {
            key: _absolute_executable(value)
            for key, value in executables.items()
        }
        environment = _string_map(
            table.get("environment", {}),
            "actions.process.environment",
            required=False,
        )
        default_timeout = _number(
            table.get("default_timeout", 30.0),
            "actions.process.default_timeout",
        )
        max_timeout = _number(
            table.get("max_timeout", 300.0),
            "actions.process.max_timeout",
        )
        registry.register_process(
            ProcessAdapter(
                normalized_executables,
                default_timeout=default_timeout,
                max_timeout=max_timeout,
                environment=environment,
            )
        )
        capabilities.append("process")
        manifest.append(
            {
                "capability": "process",
                "executables": sorted(
                    normalized_executables
                ),
                "environment_keys": sorted(environment),
                "default_timeout": default_timeout,
                "max_timeout": max_timeout,
            }
        )

    http = action_data.get("http")
    if http is not None:
        table = _table(http, "actions.http")
        _reject_unknown(
            table,
            {
                "allowed_hosts",
                "default_timeout",
                "max_timeout",
            },
            "actions.http",
        )
        allowed_hosts = _string_list(
            table.get("allowed_hosts"),
            "actions.http.allowed_hosts",
            required=True,
        )
        default_timeout = _number(
            table.get("default_timeout", 10.0),
            "actions.http.default_timeout",
        )
        max_timeout = _number(
            table.get("max_timeout", 60.0),
            "actions.http.max_timeout",
        )
        adapter = HttpAdapter(
            default_timeout=default_timeout,
            max_timeout=max_timeout,
            allowed_hosts=allowed_hosts,
        )
        registry.register_http(adapter)
        capabilities.append("http")
        manifest.append(
            {
                "capability": "http",
                "allowed_hosts": list(
                    adapter.allowed_hosts or ()
                ),
                "default_timeout": default_timeout,
                "max_timeout": max_timeout,
            }
        )

    if not capabilities:
        raise ValueError(
            "action profile must configure at least one adapter"
        )

    return ActionProfile(
        source=source,
        actions=registry,
        capabilities=tuple(capabilities),
        adapters=tuple(manifest),
    )


def profile_manifest(
    profile: ActionProfile,
) -> dict[str, object]:
    """Return a deterministic inspection view without secret values."""
    if not isinstance(profile, ActionProfile):
        raise TypeError(
            "profile must be ActionProfile"
        )
    return {
        "source": str(profile.source),
        "capabilities": list(profile.capabilities),
        "operations": list(profile.actions.manifest()),
        "adapters": list(profile.adapters),
    }


def _table(
    value: Any,
    name: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(
            f"[{name}] must be a TOML table"
        )
    return value


def _reject_unknown(
    table: dict[str, Any],
    allowed: set[str],
    name: str,
) -> None:
    unknown = set(table) - allowed
    if unknown:
        raise ValueError(
            f"unsupported {name} keys: "
            + ", ".join(sorted(unknown))
        )


def _string_list(
    value: Any,
    name: str,
    *,
    required: bool,
) -> tuple[str, ...]:
    if value is None:
        if required:
            raise ValueError(
                f"{name} is required"
            )
        return ()
    if not isinstance(value, list) or not value:
        raise ValueError(
            f"{name} must be a non-empty array of strings"
        )
    if not all(
        isinstance(item, str) and item
        for item in value
    ):
        raise ValueError(
            f"{name} must contain non-empty strings"
        )
    return tuple(value)


def _string_map(
    value: Any,
    name: str,
    *,
    required: bool,
) -> dict[str, str]:
    if value is None:
        if required:
            raise ValueError(
                f"{name} is required"
            )
        return {}
    if not isinstance(value, dict):
        raise ValueError(
            f"{name} must be a TOML table"
        )

    result: dict[str, str] = {}
    for key, item in value.items():
        if (
            not isinstance(key, str)
            or not key
            or not isinstance(item, str)
        ):
            raise ValueError(
                f"{name} keys and values must be strings"
            )
        result[key] = item

    if required and not result:
        raise ValueError(
            f"{name} must not be empty"
        )
    return result


def _number(
    value: Any,
    name: str,
) -> float:
    if isinstance(value, bool) or not isinstance(
        value,
        (int, float),
    ):
        raise ValueError(
            f"{name} must be numeric"
        )
    result = float(value)
    if result <= 0:
        raise ValueError(
            f"{name} must be greater than zero"
        )
    return result


def _resolve_profile_path(
    base: Path,
    value: str,
) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path.resolve(strict=False)
    return (base / path).resolve(strict=False)


def _absolute_executable(
    value: str,
) -> str:
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError(
            "process executable paths in action profiles must be absolute"
        )
    return str(path.resolve(strict=False))


__all__ = [
    "ActionProfile",
    "load_action_profile",
    "profile_manifest",
]
