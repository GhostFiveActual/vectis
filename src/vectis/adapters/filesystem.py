# GHOST FIVE // VECTIS
# Implements the bounded filesystem capability adapter used by VECTIS.
"""Controlled filesystem capability adapter for VECTIS."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path


class FileSystemAccessDenied(PermissionError):
    """Raised when a filesystem path escapes every explicitly allowed root."""


class FileSystemAdapter:
    """Perform controlled text-file operations within explicit allowed roots.

    Paths are resolved canonically before access. Absolute paths must remain
    beneath one of the configured roots. Relative paths are interpreted beneath
    the first configured root.

    Constructing the adapter is the explicit grant of the ``filesystem``
    capability; paths outside the grant are denied.
    """

    capability = "filesystem"

    def __init__(
        self,
        allowed_roots: str | Path | Iterable[str | Path],
    ) -> None:
        if isinstance(allowed_roots, (str, Path)):
            roots = (allowed_roots,)
        else:
            roots = tuple(allowed_roots)

        if not roots:
            raise ValueError(
                "at least one allowed filesystem root is required"
            )

        normalized: list[Path] = []

        for root in roots:
            if not isinstance(root, (str, Path)):
                raise TypeError(
                    "allowed filesystem roots must be str or pathlib.Path"
                )

            resolved = Path(root).expanduser().resolve(strict=False)

            if resolved not in normalized:
                normalized.append(resolved)

        self._allowed_roots = tuple(normalized)

    @property
    def allowed_roots(self) -> tuple[Path, ...]:
        """Return the immutable canonical root allowlist."""
        return self._allowed_roots

    def resolve_path(self, path: str | Path) -> Path:
        """Return a canonical allowed path or deny the request."""
        if not isinstance(path, (str, Path)):
            raise TypeError(
                "filesystem path must be str or pathlib.Path"
            )

        requested = Path(path).expanduser()

        if requested.is_absolute():
            candidate = requested.resolve(strict=False)
        else:
            candidate = (
                self._allowed_roots[0] / requested
            ).resolve(strict=False)

        for root in self._allowed_roots:
            try:
                candidate.relative_to(root)
            except ValueError:
                continue
            else:
                return candidate

        raise FileSystemAccessDenied(
            f"path is outside allowed filesystem roots: {path!s}"
        )

    def read(
        self,
        path: str | Path,
        *,
        encoding: str = "utf-8",
    ) -> str:
        """Read a text file after enforcing the root allowlist."""
        resolved = self.resolve_path(path)
        return resolved.read_text(encoding=encoding)

    def write(
        self,
        path: str | Path,
        content: str,
        *,
        encoding: str = "utf-8",
    ) -> None:
        """Write a text file after enforcing the root allowlist."""
        if not isinstance(content, str):
            raise TypeError("filesystem text content must be str")

        resolved = self.resolve_path(path)
        resolved.write_text(content, encoding=encoding)

    def read_text(
        self,
        path: str | Path,
        *,
        encoding: str = "utf-8",
    ) -> str:
        """Compatibility spelling for :meth:`read`."""
        return self.read(path, encoding=encoding)

    def write_text(
        self,
        path: str | Path,
        content: str,
        *,
        encoding: str = "utf-8",
    ) -> None:
        """Compatibility spelling for :meth:`write`."""
        self.write(
            path,
            content,
            encoding=encoding,
        )


# Compatibility for the capitalization used by the discarded generated draft.
FilesystemAdapter = FileSystemAdapter


__all__ = [
    "FileSystemAccessDenied",
    "FileSystemAdapter",
]
