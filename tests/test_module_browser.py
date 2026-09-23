# GHOST FIVE // VECTIS
# Regression coverage for deterministic project module browsing.
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from vectis.module_browser import (
    MODULE_BROWSER_SCHEMA,
    browse_project_modules,
)


class ModuleBrowserTests(unittest.TestCase):
    def write(self, root: Path, relative: str, content: str) -> Path:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_catalog_is_project_relative_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "vectis.toml").write_text(
                "# GHOST FIVE // VECTIS\n[project]\n",
                encoding="utf-8",
            )
            self.write(
                root,
                "lib/checks.vectis",
                "function ready(value) { return value; }\n",
            )
            self.write(
                root,
                "missions/main.vectis",
                'import "../lib/checks.vectis";\n'
                'mission "Browse" { publish ready(true); }\n',
            )
            first = browse_project_modules(root)
            second = browse_project_modules(root)
            self.assertEqual(first, second)
            self.assertEqual(first["schema"], MODULE_BROWSER_SCHEMA)
            self.assertTrue(first["ok"])
            self.assertEqual(first["root"], ".")
            self.assertEqual(first["module_count"], 2)
            self.assertEqual(
                first["edges"],
                [{"from": "missions/main.vectis", "to": "lib/checks.vectis"}],
            )
            self.assertNotIn(str(root.resolve()), repr(first))

    def test_functions_and_executable_shape_are_visible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "vectis.toml").write_text(
                "# GHOST FIVE // VECTIS\n[project]\n",
                encoding="utf-8",
            )
            self.write(
                root,
                "lib/math.vectis",
                "function clamp_score(value, minimum, maximum) {\n"
                "    return clamp(value, minimum, maximum);\n"
                "}\n",
            )
            self.write(root, "main.vectis", 'mission "Entry" { publish true; }\n')
            payload = browse_project_modules(root)
            by_path = {item["path"]: item for item in payload["modules"]}
            library = by_path["lib/math.vectis"]
            self.assertEqual(library["kind"], "library")
            self.assertTrue(library["importable"])
            self.assertEqual(
                library["functions"],
                [{
                    "name": "clamp_score",
                    "parameters": ["value", "minimum", "maximum"],
                }],
            )
            self.assertEqual(by_path["main.vectis"]["kind"], "entry")
            self.assertFalse(by_path["main.vectis"]["importable"])

    def test_import_failures_are_safe_and_project_relative(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "vectis.toml").write_text(
                "# GHOST FIVE // VECTIS\n[project]\n",
                encoding="utf-8",
            )
            self.write(
                root,
                "main.vectis",
                'import "lib/missing.vectis";\nmission "Entry" {}\n',
            )
            payload = browse_project_modules(root)
            self.assertFalse(payload["ok"])
            module = payload["modules"][0]
            self.assertEqual(module["status"], "invalid")
            self.assertEqual(module["imports"][0]["status"], "missing")
            self.assertEqual(module["imports"][0]["target"], "lib/missing.vectis")
            self.assertNotIn(str(root.resolve()), repr(payload))

    def test_parse_diagnostic_does_not_expose_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "vectis.toml").write_text(
                "# GHOST FIVE // VECTIS\n[project]\n",
                encoding="utf-8",
            )
            self.write(root, "broken.vectis", "@")
            payload = browse_project_modules(root)
            self.assertFalse(payload["ok"])
            diagnostic = payload["modules"][0]["diagnostics"][0]
            self.assertTrue(diagnostic["code"].startswith("LEX"))
            self.assertNotIn(str(root.resolve()), repr(payload))

    def test_overlays_replace_disk_and_add_unsaved_modules(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "vectis.toml").write_text(
                "# GHOST FIVE // VECTIS\n[project]\n",
                encoding="utf-8",
            )
            saved = self.write(
                root,
                "lib/shared.vectis",
                "function saved(value) { return value; }\n",
            )
            unsaved = root / "lib" / "draft.vectis"
            overlays = {
                saved.resolve(): (
                    "function overlay(value, fallback) { "
                    "return coalesce(value, fallback); }\n"
                ),
                unsaved.resolve(): "function draft(value) { return value; }\n",
            }
            payload = browse_project_modules(root, overlays=overlays)
            by_path = {item["path"]: item for item in payload["modules"]}
            self.assertEqual(sorted(by_path), ["lib/draft.vectis", "lib/shared.vectis"])
            self.assertEqual(
                by_path["lib/shared.vectis"]["functions"][0]["name"],
                "overlay",
            )
            self.assertTrue(by_path["lib/shared.vectis"]["overlay"])
            self.assertTrue(by_path["lib/draft.vectis"]["overlay"])

    def test_cycles_are_reported_deterministically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "vectis.toml").write_text(
                "# GHOST FIVE // VECTIS\n[project]\n",
                encoding="utf-8",
            )
            self.write(
                root,
                "a.vectis",
                'import "b.vectis";\nfunction a(value) { return value; }\n',
            )
            self.write(
                root,
                "b.vectis",
                'import "a.vectis";\nfunction b(value) { return value; }\n',
            )
            payload = browse_project_modules(root)
            self.assertFalse(payload["ok"])
            self.assertEqual(
                payload["cycles"],
                [["a.vectis", "b.vectis", "a.vectis"]],
            )


if __name__ == "__main__":
    unittest.main()
