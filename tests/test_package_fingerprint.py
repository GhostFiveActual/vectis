# GHOST FIVE // VECTIS
# Regression coverage for deterministic package content fingerprints.
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from vectis.module_browser import browse_project_modules
from vectis.package_fingerprint import (
    PACKAGE_FINGERPRINT_SCHEMA,
    PackageFingerprintError,
    package_descriptor,
    package_fingerprint,
)


class PackageFingerprintTests(unittest.TestCase):
    def write(
        self,
        root: Path,
        relative: str,
        content: str,
    ) -> Path:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def project(
        self,
        root: Path,
        packages: str,
    ) -> None:
        (root / "vectis.toml").write_text(
            "# GHOST FIVE // VECTIS\n"
            "[project]\n"
            'name = "fingerprint-test"\n'
            + packages,
            encoding="utf-8",
        )

    def simple_package(
        self,
        root: Path,
        *,
        version: str | None = "1.0.0",
        source: str = "function ready(value) { return value; }\n",
    ) -> Path:
        version_line = (
            ""
            if version is None
            else f'version = "{version}"\n'
        )
        self.project(
            root,
            "\n[packages.gate]\n"
            'entry = "packages/gate.vectis"\n'
            + version_line,
        )
        return self.write(
            root,
            "packages/gate.vectis",
            source,
        )

    def test_fingerprint_is_repeatable_and_sha256(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.simple_package(root)
            first = package_fingerprint(root, "gate")
            second = package_fingerprint(root, "gate")
            self.assertEqual(first, second)
            self.assertRegex(first, r"^[0-9a-f]{64}$")

    def test_descriptor_is_project_relative_and_canonical(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.core]\n"
                'entry = "packages/core.vectis"\n'
                'version = "1.0.0"\n'
                "\n[packages.gate]\n"
                'entry = "packages/gate/index.vectis"\n'
                'version = "2.0.0"\n'
                "\n[packages.gate.dependencies]\n"
                'core = "1.0.0"\n',
            )
            self.write(
                root,
                "packages/core.vectis",
                "function core(value) { return value; }\n",
            )
            self.write(
                root,
                "packages/gate/helper.vectis",
                "function helper(value) { return value; }\n",
            )
            self.write(
                root,
                "packages/gate/index.vectis",
                'import "helper.vectis";\n'
                'import package "core";\n'
                "function ready(value) { return core.core(helper(value)); }\n",
            )
            descriptor = package_descriptor(root, "gate")
            self.assertEqual(
                descriptor["schema"],
                PACKAGE_FINGERPRINT_SCHEMA,
            )
            self.assertEqual(descriptor["name"], "gate")
            self.assertEqual(
                descriptor["entry"],
                "packages/gate/index.vectis",
            )
            self.assertEqual(descriptor["version"], "2.0.0")
            self.assertEqual(
                [item["path"] for item in descriptor["files"]],
                [
                    "packages/gate/helper.vectis",
                    "packages/gate/index.vectis",
                ],
            )
            self.assertEqual(
                [item["name"] for item in descriptor["dependencies"]],
                ["core"],
            )
            self.assertNotIn(str(root.resolve()), repr(descriptor))

    def test_same_package_in_different_checkout_roots_has_same_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as left_directory:
            with tempfile.TemporaryDirectory() as right_directory:
                left = Path(left_directory)
                right = Path(right_directory)
                self.simple_package(left)
                self.simple_package(right)
                self.assertEqual(
                    package_fingerprint(left, "gate"),
                    package_fingerprint(right, "gate"),
                )

    def test_line_endings_normalize_to_lf(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = self.simple_package(root)
            lf = package_fingerprint(root, "gate")
            source_path.write_bytes(
                b"function ready(value) { return value; }\r\n"
            )
            crlf = package_fingerprint(root, "gate")
            self.assertEqual(lf, crlf)

    def test_own_source_change_changes_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = self.simple_package(root)
            before = package_fingerprint(root, "gate")
            source_path.write_text(
                "function ready(value) { return !value; }\n",
                encoding="utf-8",
            )
            after = package_fingerprint(root, "gate")
            self.assertNotEqual(before, after)

    def test_source_comment_change_changes_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = self.simple_package(root)
            before = package_fingerprint(root, "gate")
            source_path.write_text(
                "// fingerprint comment\n"
                "function ready(value) { return value; }\n",
                encoding="utf-8",
            )
            self.assertNotEqual(
                before,
                package_fingerprint(root, "gate"),
            )

    def test_unrelated_project_file_does_not_change_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.simple_package(root)
            before = package_fingerprint(root, "gate")
            self.write(
                root,
                "notes/other.vectis",
                "function unrelated() { return 7; }\n",
            )
            self.assertEqual(
                before,
                package_fingerprint(root, "gate"),
            )

    def test_path_imported_helper_participates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.gate]\n"
                'entry = "packages/gate/index.vectis"\n'
                'version = "1.0.0"\n',
            )
            helper = self.write(
                root,
                "packages/gate/helper.vectis",
                "function helper(value) { return value; }\n",
            )
            self.write(
                root,
                "packages/gate/index.vectis",
                'import "helper.vectis";\n'
                "function ready(value) { return helper(value); }\n",
            )
            before = package_fingerprint(root, "gate")
            helper.write_text(
                "function helper(value) { return !value; }\n",
                encoding="utf-8",
            )
            self.assertNotEqual(
                before,
                package_fingerprint(root, "gate"),
            )

    def test_sibling_package_change_does_not_change_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.alpha]\n"
                'entry = "alpha.vectis"\n'
                'version = "1.0.0"\n'
                "\n[packages.beta]\n"
                'entry = "beta.vectis"\n'
                'version = "1.0.0"\n',
            )
            self.write(
                root,
                "alpha.vectis",
                "function value() { return 1; }\n",
            )
            beta = self.write(
                root,
                "beta.vectis",
                "function value() { return 2; }\n",
            )
            before = package_fingerprint(root, "alpha")
            beta.write_text(
                "function value() { return 3; }\n",
                encoding="utf-8",
            )
            self.assertEqual(
                before,
                package_fingerprint(root, "alpha"),
            )

    def test_package_version_participates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.simple_package(root, version="1.0.0")
            before = package_fingerprint(root, "gate")
            manifest = (root / "vectis.toml").read_text(encoding="utf-8")
            (root / "vectis.toml").write_text(
                manifest.replace('version = "1.0.0"', 'version = "1.0.1"'),
                encoding="utf-8",
            )
            self.assertNotEqual(
                before,
                package_fingerprint(root, "gate"),
            )

    def test_unversioned_rfc0027_package_can_be_fingerprinted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.simple_package(root, version=None)
            descriptor = package_descriptor(root, "gate")
            self.assertIsNone(descriptor["version"])
            self.assertRegex(
                package_fingerprint(root, "gate"),
                r"^[0-9a-f]{64}$",
            )

    def test_manifest_declaration_order_does_not_change_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packages = (
                "\n[packages.alpha]\n"
                'entry = "alpha.vectis"\n'
                'version = "1.0.0"\n'
                "\n[packages.beta]\n"
                'entry = "beta.vectis"\n'
                'version = "1.0.0"\n'
            )
            self.project(root, packages)
            self.write(root, "alpha.vectis", "function a() { return 1; }\n")
            self.write(root, "beta.vectis", "function b() { return 2; }\n")
            before = package_fingerprint(root, "alpha")
            self.project(
                root,
                "\n[packages.beta]\n"
                'entry = "beta.vectis"\n'
                'version = "1.0.0"\n'
                "\n[packages.alpha]\n"
                'entry = "alpha.vectis"\n'
                'version = "1.0.0"\n',
            )
            self.assertEqual(
                before,
                package_fingerprint(root, "alpha"),
            )

    def test_declared_dependency_source_participates_even_when_unused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.core]\n"
                'entry = "core.vectis"\n'
                'version = "1.0.0"\n'
                "\n[packages.gate]\n"
                'entry = "gate.vectis"\n'
                'version = "2.0.0"\n'
                "\n[packages.gate.dependencies]\n"
                'core = "1.0.0"\n',
            )
            core = self.write(
                root,
                "core.vectis",
                "function core() { return 1; }\n",
            )
            self.write(
                root,
                "gate.vectis",
                "function gate() { return 2; }\n",
            )
            before = package_fingerprint(root, "gate")
            core.write_text(
                "function core() { return 3; }\n",
                encoding="utf-8",
            )
            self.assertNotEqual(
                before,
                package_fingerprint(root, "gate"),
            )

    def test_transitive_dependency_source_participates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.core]\n"
                'entry = "core.vectis"\n'
                'version = "1.0.0"\n'
                "\n[packages.policy]\n"
                'entry = "policy.vectis"\n'
                'version = "2.0.0"\n'
                "\n[packages.policy.dependencies]\n"
                'core = "1.0.0"\n'
                "\n[packages.release]\n"
                'entry = "release.vectis"\n'
                'version = "3.0.0"\n'
                "\n[packages.release.dependencies]\n"
                'policy = "2.0.0"\n',
            )
            core = self.write(
                root,
                "core.vectis",
                "function core() { return 1; }\n",
            )
            self.write(root, "policy.vectis", "function policy() { return 2; }\n")
            self.write(root, "release.vectis", "function release() { return 3; }\n")
            before = package_fingerprint(root, "release")
            core.write_text(
                "function core() { return 4; }\n",
                encoding="utf-8",
            )
            self.assertNotEqual(
                before,
                package_fingerprint(root, "release"),
            )

    def test_overlay_source_participates_without_writing_disk(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = self.simple_package(root)
            disk_source = source_path.read_text(encoding="utf-8")
            disk = package_fingerprint(root, "gate")
            overlay = package_fingerprint(
                root,
                "gate",
                overlays={
                    source_path.resolve(): (
                        "function ready(value) { return !value; }\n"
                    )
                },
            )
            self.assertNotEqual(disk, overlay)
            self.assertEqual(
                source_path.read_text(encoding="utf-8"),
                disk_source,
            )

    def test_unknown_package_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.simple_package(root)
            with self.assertRaisesRegex(
                PackageFingerprintError,
                "unknown package",
            ):
                package_fingerprint(root, "missing")

    def test_missing_entry_fails_with_project_relative_message(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.gate]\n"
                'entry = "packages/missing.vectis"\n',
            )
            with self.assertRaises(PackageFingerprintError) as caught:
                package_fingerprint(root, "gate")
            rendered = str(caught.exception)
            self.assertIn("packages/missing.vectis", rendered)
            self.assertNotIn(str(root.resolve()), rendered)

    def test_missing_path_import_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.gate]\n"
                'entry = "packages/gate.vectis"\n',
            )
            self.write(
                root,
                "packages/gate.vectis",
                'import "missing.vectis";\n'
                "function ready(value) { return value; }\n",
            )
            with self.assertRaisesRegex(
                PackageFingerprintError,
                "does not exist",
            ):
                package_fingerprint(root, "gate")

    def test_path_import_escape_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as parent_directory:
            parent = Path(parent_directory)
            root = parent / "project"
            root.mkdir()
            outside = parent / "outside.vectis"
            outside.write_text(
                "function outside() { return true; }\n",
                encoding="utf-8",
            )
            self.project(
                root,
                "\n[packages.gate]\n"
                'entry = "gate.vectis"\n',
            )
            self.write(
                root,
                "gate.vectis",
                'import "../outside.vectis";\n'
                "function ready(value) { return value; }\n",
            )
            with self.assertRaisesRegex(
                PackageFingerprintError,
                "escapes the project root",
            ):
                package_fingerprint(root, "gate")

    def test_undeclared_package_import_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.core]\n"
                'entry = "core.vectis"\n'
                'version = "1.0.0"\n'
                "\n[packages.gate]\n"
                'entry = "gate.vectis"\n'
                'version = "1.0.0"\n',
            )
            self.write(root, "core.vectis", "function core() { return 1; }\n")
            self.write(
                root,
                "gate.vectis",
                'import package "core";\n'
                "function gate() { return core.core(); }\n",
            )
            with self.assertRaisesRegex(
                PackageFingerprintError,
                "without a dependency contract",
            ):
                package_fingerprint(root, "gate")

    def test_module_browser_exposes_matching_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.simple_package(root)
            self.write(
                root,
                "main.vectis",
                'import package "gate";\n'
                'mission "Fingerprint" { publish gate.ready(true); }\n',
            )
            payload = browse_project_modules(root)
            self.assertTrue(payload["ok"], payload)
            package = next(
                item
                for item in payload["packages"]
                if item["name"] == "gate"
            )
            self.assertEqual(
                package["fingerprint"],
                package_fingerprint(root, "gate"),
            )
            self.assertRegex(
                package["fingerprint"],
                r"^[0-9a-f]{64}$",
            )
            self.assertNotIn(str(root.resolve()), repr(payload))


if __name__ == "__main__":
    unittest.main()
