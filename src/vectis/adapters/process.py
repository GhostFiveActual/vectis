# GHOST FIVE // VECTIS
# Implements the allowlisted process capability adapter used by VECTIS.
"""Controlled process capability adapter for VECTIS."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
import math
import os
from pathlib import Path
import subprocess
from types import MappingProxyType


class ProcessAccessDenied(PermissionError):
    """Raised when an executable is outside the explicit allowlist."""


class ProcessTimeoutError(TimeoutError):
    """Raised when an allowlisted process exceeds its timeout."""

    def __init__(
        self,
        argv: tuple[str, ...],
        timeout: float,
        *,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        super().__init__(
            f"process exceeded timeout of {timeout:g} seconds: {argv[0]}"
        )
        self.argv = argv
        self.timeout = timeout
        self.stdout = stdout
        self.stderr = stderr


@dataclass(frozen=True, slots=True)
class ProcessResult:
    """Deterministic captured result from one process invocation."""

    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


class ProcessAdapter:
    """Execute only explicitly allowlisted programs with structured arguments."""

    capability = "process"

    def __init__(
        self,
        allowed_executables: Mapping[str, str | Path] | Iterable[str | Path],
        *,
        default_timeout: float = 30.0,
        max_timeout: float = 300.0,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        self._default_timeout = self._validate_timeout(
            default_timeout,
            name="default_timeout",
            maximum=None,
        )
        self._max_timeout = self._validate_timeout(
            max_timeout,
            name="max_timeout",
            maximum=None,
        )

        if self._default_timeout > self._max_timeout:
            raise ValueError(
                "default_timeout must not exceed max_timeout"
            )

        normalized = self._normalize_allowlist(allowed_executables)

        if not normalized:
            raise ValueError(
                "at least one executable must be explicitly allowlisted"
            )

        self._executables = MappingProxyType(normalized)
        self._environment = MappingProxyType(
            self._normalize_environment(environment)
        )

    @property
    def allowed_executables(self) -> tuple[tuple[str, Path], ...]:
        """Return the immutable executable allowlist in declaration order."""
        return tuple(self._executables.items())

    @property
    def default_timeout(self) -> float:
        return self._default_timeout

    @property
    def max_timeout(self) -> float:
        return self._max_timeout

    def resolve_executable(self, executable: str) -> Path:
        """Resolve a logical executable name strictly through the allowlist."""
        if not isinstance(executable, str):
            raise TypeError("executable name must be str")

        if not executable:
            raise ValueError("executable name must not be empty")

        try:
            return self._executables[executable]
        except KeyError as exc:
            raise ProcessAccessDenied(
                f"executable is not allowlisted: {executable!r}"
            ) from exc

    def run(
        self,
        executable: str,
        arguments: Sequence[str] = (),
        *,
        timeout: float | None = None,
    ) -> ProcessResult:
        """Run one allowlisted executable without shell interpolation."""
        path = self.resolve_executable(executable)
        argv = self._build_argv(path, arguments)
        effective_timeout = self._effective_timeout(timeout)

        try:
            completed = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                shell=False,
                timeout=effective_timeout,
                check=False,
                env=dict(self._environment),
            )
        except subprocess.TimeoutExpired as exc:
            raise ProcessTimeoutError(
                argv,
                effective_timeout,
                stdout=self._coerce_output(exc.stdout),
                stderr=self._coerce_output(exc.stderr),
            ) from exc

        return ProcessResult(
            argv=argv,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    def _normalize_allowlist(
        self,
        allowed: Mapping[str, str | Path] | Iterable[str | Path],
    ) -> dict[str, Path]:
        normalized: dict[str, Path] = {}

        if isinstance(allowed, Mapping):
            entries = tuple(allowed.items())
        else:
            if isinstance(allowed, (str, Path)):
                values = (allowed,)
            else:
                values = tuple(allowed)

            entries = tuple(
                (self._path_alias(value), value)
                for value in values
            )

        for alias, value in entries:
            if not isinstance(alias, str):
                raise TypeError("executable allowlist names must be str")

            if not alias:
                raise ValueError(
                    "executable allowlist names must not be empty"
                )

            path = self._canonical_executable(value)

            existing = normalized.get(alias)

            if existing is not None and existing != path:
                raise ValueError(
                    f"duplicate executable alias with different paths: {alias!r}"
                )

            normalized[alias] = path

        return normalized

    @staticmethod
    def _path_alias(value: str | Path) -> str:
        if not isinstance(value, (str, Path)):
            raise TypeError(
                "allowlisted executables must be str or pathlib.Path"
            )

        path = Path(value).expanduser()

        if not path.is_absolute():
            raise ValueError(
                "allowlisted executable paths must be absolute"
            )

        if not path.name:
            raise ValueError(
                "allowlisted executable path must name a file"
            )

        return path.name

    @staticmethod
    def _canonical_executable(value: str | Path) -> Path:
        if not isinstance(value, (str, Path)):
            raise TypeError(
                "allowlisted executables must be str or pathlib.Path"
            )

        raw = Path(value).expanduser()

        if not raw.is_absolute():
            raise ValueError(
                "allowlisted executable paths must be absolute"
            )

        try:
            path = raw.resolve(strict=True)
        except FileNotFoundError as exc:
            raise ValueError(
                f"allowlisted executable does not exist: {value!s}"
            ) from exc

        if not path.is_file():
            raise ValueError(
                f"allowlisted executable is not a file: {value!s}"
            )

        if not os.access(path, os.X_OK):
            raise ValueError(
                f"allowlisted executable is not executable: {value!s}"
            )

        return path

    @staticmethod
    def _normalize_environment(
        environment: Mapping[str, str] | None,
    ) -> dict[str, str]:
        if environment is None:
            return {}

        result: dict[str, str] = {}

        for key, value in environment.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise TypeError(
                    "process environment keys and values must be str"
                )

            if not key or "=" in key or "\x00" in key or "\x00" in value:
                raise ValueError(
                    "process environment contains an invalid entry"
                )

            result[key] = value

        return result

    @staticmethod
    def _build_argv(
        executable: Path,
        arguments: Sequence[str],
    ) -> tuple[str, ...]:
        if isinstance(arguments, (str, bytes)):
            raise TypeError(
                "process arguments must be a structured sequence of strings"
            )

        try:
            values = tuple(arguments)
        except TypeError as exc:
            raise TypeError(
                "process arguments must be a structured sequence of strings"
            ) from exc

        if not all(isinstance(value, str) for value in values):
            raise TypeError(
                "every process argument must be str"
            )

        if any("\x00" in value for value in values):
            raise ValueError(
                "process arguments must not contain NUL characters"
            )

        return (str(executable), *values)

    def _effective_timeout(
        self,
        timeout: float | None,
    ) -> float:
        if timeout is None:
            return self._default_timeout

        return self._validate_timeout(
            timeout,
            name="timeout",
            maximum=self._max_timeout,
        )

    @staticmethod
    def _validate_timeout(
        value: float,
        *,
        name: str,
        maximum: float | None,
    ) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{name} must be a positive number")

        result = float(value)

        if not math.isfinite(result) or result <= 0:
            raise ValueError(f"{name} must be a finite number greater than zero")

        if maximum is not None and result > maximum:
            raise ValueError(
                f"{name} must not exceed {maximum:g} seconds"
            )

        return result

    @staticmethod
    def _coerce_output(value: str | bytes | None) -> str:
        if value is None:
            return ""

        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")

        return value


__all__ = [
    "ProcessAccessDenied",
    "ProcessAdapter",
    "ProcessResult",
    "ProcessTimeoutError",
]
