# GHOST FIVE // VECTIS
# Regression coverage for the VECTIS filesystem adapter contract.
"""Tests for the controlled VECTIS filesystem capability adapter."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from vectis.adapters.filesystem import (
    FileSystemAccessDenied,
    FileSystemAdapter,
)


class FileSystemAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = TemporaryDirectory()
        self.base = Path(self._temp.name)

        self.root = self.base / "allowed"
        self.root.mkdir()

        self.second_root = self.base / "second"
        self.second_root.mkdir()

        self.outside = self.base / "outside"
        self.outside.mkdir()

        # Deliberately shares a string prefix with "allowed".
        self.prefix_collision = self.base / "allowed-evil"
        self.prefix_collision.mkdir()

        self.adapter = FileSystemAdapter(self.root)

    def tearDown(self) -> None:
        self._temp.cleanup()

    def assertDenied(self, path: str | Path) -> None:
        with self.assertRaises(FileSystemAccessDenied):
            self.adapter.resolve_path(path)

    def test_public_capability_name(self) -> None:
        self.assertEqual(
            FileSystemAdapter.capability,
            "filesystem",
        )

    def test_single_allowed_root_is_canonical(self) -> None:
        self.assertEqual(
            self.adapter.allowed_roots,
            (self.root.resolve(),),
        )

    def test_multiple_explicit_roots_are_supported(self) -> None:
        adapter = FileSystemAdapter(
            [
                self.root,
                self.second_root,
            ]
        )

        self.assertEqual(
            adapter.allowed_roots,
            (
                self.root.resolve(),
                self.second_root.resolve(),
            ),
        )

    def test_duplicate_roots_are_collapsed(self) -> None:
        adapter = FileSystemAdapter(
            [
                self.root,
                self.root,
            ]
        )

        self.assertEqual(
            adapter.allowed_roots,
            (self.root.resolve(),),
        )

    def test_empty_root_allowlist_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            FileSystemAdapter([])

    def test_relative_read_write_round_trip(self) -> None:
        self.adapter.write(
            "relative.txt",
            "relative-data",
        )

        self.assertEqual(
            self.adapter.read("relative.txt"),
            "relative-data",
        )

        self.assertEqual(
            (self.root / "relative.txt").read_text(
                encoding="utf-8"
            ),
            "relative-data",
        )

    def test_absolute_path_inside_root_is_allowed(self) -> None:
        target = self.root / "absolute.txt"

        self.adapter.write(
            target,
            "absolute-data",
        )

        self.assertEqual(
            self.adapter.read(target),
            "absolute-data",
        )

    def test_parent_traversal_escape_is_denied(self) -> None:
        self.assertDenied(
            "../outside.txt"
        )

    def test_string_prefix_collision_is_denied(self) -> None:
        self.assertDenied(
            self.prefix_collision / "payload.txt"
        )

    def test_absolute_outside_path_is_denied(self) -> None:
        self.assertDenied(
            self.outside / "payload.txt"
        )

    def test_symlink_escape_is_denied(self) -> None:
        link = self.root / "escape-link"

        try:
            link.symlink_to(
                self.outside,
                target_is_directory=True,
            )
        except (OSError, NotImplementedError) as exc:
            self.skipTest(
                f"symlinks unavailable on this platform: {exc}"
            )

        self.assertDenied(
            link / "payload.txt"
        )

    def test_second_explicit_root_can_be_used(self) -> None:
        adapter = FileSystemAdapter(
            [
                self.root,
                self.second_root,
            ]
        )

        target = self.second_root / "second.txt"

        adapter.write(
            target,
            "second-data",
        )

        self.assertEqual(
            adapter.read(target),
            "second-data",
        )

    def test_read_text_write_text_aliases_round_trip(self) -> None:
        self.adapter.write_text(
            "alias.txt",
            "alias-data",
        )

        self.assertEqual(
            self.adapter.read_text("alias.txt"),
            "alias-data",
        )

    def test_non_text_write_content_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            self.adapter.write(
                "binary.txt",
                b"not-text",  # type: ignore[arg-type]
            )

    def test_invalid_path_type_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            self.adapter.resolve_path(
                123  # type: ignore[arg-type]
            )

    def test_denial_error_is_permission_error(self) -> None:
        self.assertTrue(
            issubclass(
                FileSystemAccessDenied,
                PermissionError,
            )
        )


if __name__ == "__main__":
    unittest.main()
