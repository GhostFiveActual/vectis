# GHOST FIVE // VECTIS
# Regression coverage for explicit action registration and adapter bindings.
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from vectis.actions import (
    ActionCapabilityMismatch,
    ActionRegistry,
    ActionUnavailable,
)
from vectis.adapters.filesystem import FileSystemAdapter


class ActionRegistryTests(unittest.TestCase):
    def test_registry_fails_closed_for_unknown_operation(self):
        registry = ActionRegistry()

        with self.assertRaises(ActionUnavailable):
            registry.execute(
                "missing.operation",
                "filesystem",
                {},
            )

    def test_registry_rejects_capability_mismatch(self):
        registry = ActionRegistry()
        registry.register(
            "example.read",
            "filesystem",
            lambda _arguments: "ok",
        )

        with self.assertRaises(ActionCapabilityMismatch):
            registry.execute(
                "example.read",
                "http",
                {},
            )

    def test_filesystem_actions_use_bounded_adapter(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "input.txt").write_text(
                "vectis",
                encoding="utf-8",
            )
            registry = ActionRegistry()
            registry.register_filesystem(
                FileSystemAdapter(root)
            )

            value = registry.execute(
                "filesystem.read_text",
                "filesystem",
                {"path": "input.txt"},
            )
            self.assertEqual(value, "vectis")

            result = registry.execute(
                "filesystem.write_text",
                "filesystem",
                {
                    "path": "output.txt",
                    "content": "proof",
                },
            )
            self.assertEqual(
                result,
                {
                    "path": "output.txt",
                    "written": True,
                    "characters": 5,
                },
            )
            self.assertEqual(
                (root / "output.txt").read_text(
                    encoding="utf-8"
                ),
                "proof",
            )

    def test_manifest_is_sorted_and_authority_visible(self):
        registry = ActionRegistry()
        registry.register(
            "z.operation",
            "process",
            lambda _arguments: None,
        )
        registry.register(
            "a.operation",
            "filesystem",
            lambda _arguments: None,
        )

        self.assertEqual(
            registry.manifest(),
            (
                {
                    "operation": "a.operation",
                    "capability": "filesystem",
                },
                {
                    "operation": "z.operation",
                    "capability": "process",
                },
            ),
        )


if __name__ == "__main__":
    unittest.main()
