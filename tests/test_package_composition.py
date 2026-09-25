# GHOST FIVE // VECTIS
# Regression coverage for exact package versions and local dependency contracts.
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from vectis.compiler import compile_program
from vectis.lsp_workspace import load_workspace_program
from vectis.module_browser import browse_project_modules
from vectis.modules import ModuleError, load_program_file
from vectis.package_manifest import PackageManifestError, load_package_manifest
from vectis.product import initialize_project
from vectis.runtime import Runtime
from vectis.templates import template_preview


class PackageCompositionTests(unittest.TestCase):
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
            'name = "composition-test"\n'
            + packages,
            encoding="utf-8",
        )

    def compile_loaded(self, entry: Path):
        loaded = load_program_file(entry)
        compiled = compile_program(
            loaded.program,
            function_scope=loaded.function_scope,
        )
        return loaded, compiled

    def test_rfc0027_unversioned_package_remains_valid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.gate]\n"
                'entry = "packages/gate.vectis"\n',
            )
            manifest = load_package_manifest(root, require=True)
            declaration = manifest.package("gate")
            self.assertIsNotNone(declaration)
            self.assertIsNone(declaration.version)
            self.assertEqual(declaration.dependencies, ())

    def test_manifest_parses_exact_versions_and_sorted_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.alpha]\n"
                'entry = "packages/alpha.vectis"\n'
                'version = "1.2.3"\n'
                "\n[packages.beta]\n"
                'entry = "packages/beta.vectis"\n'
                'version = "2.0.0"\n'
                "\n[packages.release]\n"
                'entry = "packages/release.vectis"\n'
                'version = "3.0.0"\n'
                "\n[packages.release.dependencies]\n"
                'beta = "2.0.0"\n'
                'alpha = "1.2.3"\n',
            )
            manifest = load_package_manifest(root, require=True)
            release = manifest.package("release")
            self.assertEqual(release.version, "3.0.0")
            self.assertEqual(
                release.dependencies,
                (("alpha", "1.2.3"), ("beta", "2.0.0")),
            )
            self.assertEqual(release.dependency("alpha"), "1.2.3")
            self.assertIsNone(release.dependency("missing"))

    def test_manifest_rejects_invalid_package_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for version in ("1", "1.2", "01.2.3", "v1.2.3", "1.2.3-beta"):
                with self.subTest(version=version):
                    self.project(
                        root,
                        "\n[packages.gate]\n"
                        'entry = "packages/gate.vectis"\n'
                        f'version = "{version}"\n',
                    )
                    with self.assertRaisesRegex(
                        PackageManifestError,
                        "MAJOR.MINOR.PATCH",
                    ):
                        load_package_manifest(root, require=True)

    def test_manifest_rejects_invalid_dependency_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.core]\n"
                'entry = "core.vectis"\n'
                'version = "1.0.0"\n'
                "\n[packages.release]\n"
                'entry = "release.vectis"\n'
                "\n[packages.release.dependencies]\n"
                'core = "1.x"\n',
            )
            with self.assertRaisesRegex(
                PackageManifestError,
                "MAJOR.MINOR.PATCH",
            ):
                load_package_manifest(root, require=True)

    def test_manifest_rejects_unknown_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.release]\n"
                'entry = "release.vectis"\n'
                "\n[packages.release.dependencies]\n"
                'core = "1.0.0"\n',
            )
            with self.assertRaisesRegex(
                PackageManifestError,
                "is not declared",
            ):
                load_package_manifest(root, require=True)

    def test_manifest_rejects_unversioned_dependency_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.core]\n"
                'entry = "core.vectis"\n'
                "\n[packages.release]\n"
                'entry = "release.vectis"\n'
                "\n[packages.release.dependencies]\n"
                'core = "1.0.0"\n',
            )
            with self.assertRaisesRegex(
                PackageManifestError,
                "has no version",
            ):
                load_package_manifest(root, require=True)

    def test_manifest_rejects_exact_version_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.core]\n"
                'entry = "core.vectis"\n'
                'version = "1.1.0"\n'
                "\n[packages.release]\n"
                'entry = "release.vectis"\n'
                "\n[packages.release.dependencies]\n"
                'core = "1.0.0"\n',
            )
            with self.assertRaisesRegex(
                PackageManifestError,
                "found '1.1.0'",
            ):
                load_package_manifest(root, require=True)

    def test_manifest_rejects_self_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.core]\n"
                'entry = "core.vectis"\n'
                'version = "1.0.0"\n'
                "\n[packages.core.dependencies]\n"
                'core = "1.0.0"\n',
            )
            with self.assertRaisesRegex(
                PackageManifestError,
                "cannot depend on itself",
            ):
                load_package_manifest(root, require=True)

    def test_manifest_rejects_dependency_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.alpha]\n"
                'entry = "alpha.vectis"\n'
                'version = "1.0.0"\n'
                "\n[packages.alpha.dependencies]\n"
                'beta = "1.0.0"\n'
                "\n[packages.beta]\n"
                'entry = "beta.vectis"\n'
                'version = "1.0.0"\n'
                "\n[packages.beta.dependencies]\n"
                'alpha = "1.0.0"\n',
            )
            with self.assertRaisesRegex(
                PackageManifestError,
                "dependency cycle",
            ):
                load_package_manifest(root, require=True)

    def test_declared_package_dependency_executes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.core]\n"
                'entry = "packages/core.vectis"\n'
                'version = "1.0.0"\n'
                "\n[packages.release]\n"
                'entry = "packages/release.vectis"\n'
                'version = "2.0.0"\n'
                "\n[packages.release.dependencies]\n"
                'core = "1.0.0"\n',
            )
            self.write(
                root,
                "packages/core.vectis",
                "function ready(value: number): boolean { return value >= 90; }\n",
            )
            self.write(
                root,
                "packages/release.vectis",
                'import package "core";\n'
                "function ready(value: number): boolean { return core.ready(value); }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import package "release";\n'
                'mission "Composition" { publish release.ready(96); }\n',
            )
            loaded, compiled = self.compile_loaded(entry)
            self.assertTrue(compiled.ok, compiled.diagnostics)
            result = Runtime(compiled.graph).execute()
            self.assertIs(result.value_for("publish:0001"), True)
            targets = sorted(
                identity.label
                for _span, identity in loaded.function_scope.calls
            )
            self.assertEqual(
                targets,
                [
                    "packages/core.vectis::ready",
                    "packages/release.vectis::ready",
                ],
            )

    def test_undeclared_package_dependency_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.core]\n"
                'entry = "packages/core.vectis"\n'
                'version = "1.0.0"\n'
                "\n[packages.release]\n"
                'entry = "packages/release.vectis"\n'
                'version = "2.0.0"\n',
            )
            self.write(
                root,
                "packages/core.vectis",
                "function ready(value) { return value; }\n",
            )
            self.write(
                root,
                "packages/release.vectis",
                'import package "core";\n'
                "function ready(value) { return core.ready(value); }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import package "release";\n'
                'mission "Composition" { publish release.ready(true); }\n',
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn(
                "without a dependency contract",
                str(caught.exception),
            )

    def test_path_imported_implementation_module_uses_owner_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.core]\n"
                'entry = "packages/core.vectis"\n'
                'version = "1.0.0"\n'
                "\n[packages.release]\n"
                'entry = "packages/release/index.vectis"\n'
                'version = "2.0.0"\n'
                "\n[packages.release.dependencies]\n"
                'core = "1.0.0"\n',
            )
            self.write(
                root,
                "packages/core.vectis",
                "function ready(value) { return value; }\n",
            )
            self.write(
                root,
                "packages/release/internal.vectis",
                'import package "core";\n'
                "function checked(value) { return core.ready(value); }\n",
            )
            self.write(
                root,
                "packages/release/index.vectis",
                'import "internal.vectis";\n'
                "function ready(value) { return checked(value); }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import package "release";\n'
                'mission "Composition" { publish release.ready(true); }\n',
            )
            _loaded, compiled = self.compile_loaded(entry)
            self.assertTrue(compiled.ok, compiled.diagnostics)

    def test_path_imported_implementation_module_without_contract_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.core]\n"
                'entry = "packages/core.vectis"\n'
                'version = "1.0.0"\n'
                "\n[packages.release]\n"
                'entry = "packages/release/index.vectis"\n'
                'version = "2.0.0"\n',
            )
            self.write(root, "packages/core.vectis", "function ready(value) { return value; }\n")
            self.write(
                root,
                "packages/release/internal.vectis",
                'import package "core";\n'
                "function checked(value) { return core.ready(value); }\n",
            )
            self.write(
                root,
                "packages/release/index.vectis",
                'import "internal.vectis";\n'
                "function ready(value) { return checked(value); }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import package "release";\n'
                'mission "Composition" { publish release.ready(true); }\n',
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn("without a dependency contract", str(caught.exception))

    def test_transitive_dependency_does_not_authorize_direct_import(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.core]\n"
                'entry = "core.vectis"\n'
                'version = "1.0.0"\n'
                "\n[packages.policy]\n"
                'entry = "policy.vectis"\n'
                'version = "1.0.0"\n'
                "\n[packages.policy.dependencies]\n"
                'core = "1.0.0"\n'
                "\n[packages.release]\n"
                'entry = "release.vectis"\n'
                'version = "1.0.0"\n'
                "\n[packages.release.dependencies]\n"
                'policy = "1.0.0"\n',
            )
            self.write(root, "core.vectis", "function ready(value) { return value; }\n")
            self.write(root, "policy.vectis", 'import package "core";\nfunction policy(value) { return core.ready(value); }\n')
            self.write(root, "release.vectis", 'import package "core";\nfunction release(value) { return core.ready(value); }\n')
            entry = self.write(root, "main.vectis", 'import package "release";\nmission "Composition" { publish release.release(true); }\n')
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn("without a dependency contract", str(caught.exception))

    def test_shared_path_module_must_satisfy_every_package_owner(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.core]\n"
                'entry = "core.vectis"\n'
                'version = "1.0.0"\n'
                "\n[packages.alpha]\n"
                'entry = "packages/alpha.vectis"\n'
                "\n[packages.beta]\n"
                'entry = "packages/beta.vectis"\n'
                "\n[packages.beta.dependencies]\n"
                'core = "1.0.0"\n',
            )
            self.write(root, "core.vectis", "function ready(value) { return value; }\n")
            self.write(
                root,
                "packages/shared.vectis",
                'import package "core";\n'
                "function shared(value) { return core.ready(value); }\n",
            )
            self.write(
                root,
                "packages/alpha.vectis",
                'import "shared.vectis";\n'
                "function alpha(value) { return shared(value); }\n",
            )
            self.write(
                root,
                "packages/beta.vectis",
                'import "shared.vectis";\n'
                "function beta(value) { return shared(value); }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import package "alpha";\n'
                'import package "beta";\n'
                'mission "Composition" { publish alpha.alpha(true); }\n',
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn("package 'alpha'", str(caught.exception))
            self.assertIn("without a dependency contract", str(caught.exception))

    def test_project_entry_import_does_not_require_dependency_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.core]\n"
                'entry = "core.vectis"\n'
                'version = "1.0.0"\n',
            )
            self.write(root, "core.vectis", "function ready(value) { return value; }\n")
            entry = self.write(root, "main.vectis", 'import package "core";\nmission "Composition" { publish core.ready(true); }\n')
            _loaded, compiled = self.compile_loaded(entry)
            self.assertTrue(compiled.ok, compiled.diagnostics)

    def test_unused_dependency_contract_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.core]\n"
                'entry = "core.vectis"\n'
                'version = "1.0.0"\n'
                "\n[packages.release]\n"
                'entry = "release.vectis"\n'
                "\n[packages.release.dependencies]\n"
                'core = "1.0.0"\n',
            )
            self.write(root, "core.vectis", "function core(value) { return value; }\n")
            self.write(root, "release.vectis", "function ready(value) { return value; }\n")
            entry = self.write(root, "main.vectis", 'import package "release";\nmission "Composition" { publish release.ready(true); }\n')
            _loaded, compiled = self.compile_loaded(entry)
            self.assertTrue(compiled.ok, compiled.diagnostics)

    def test_version_metadata_does_not_change_function_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.core]\n"
                'entry = "packages/core.vectis"\n'
                'version = "9.8.7"\n',
            )
            self.write(root, "packages/core.vectis", "function ready(value) { return value; }\n")
            entry = self.write(root, "main.vectis", 'import package "core";\nmission "Composition" { publish core.ready(true); }\n')
            loaded = load_program_file(entry)
            self.assertEqual(
                [identity.label for _span, identity in loaded.function_scope.calls],
                ["packages/core.vectis::ready"],
            )

    def test_selectors_and_aliases_compose_with_dependency_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.core]\n"
                'entry = "core.vectis"\n'
                'version = "1.0.0"\n'
                "\n[packages.release]\n"
                'entry = "release.vectis"\n'
                "\n[packages.release.dependencies]\n"
                'core = "1.0.0"\n',
            )
            self.write(root, "core.vectis", "function ready(value) { return value; }\nfunction score(value) { return value; }\n")
            self.write(root, "release.vectis", 'import package "core" {ready} as c;\nfunction release(value) { return c.ready(value); }\n')
            entry = self.write(root, "main.vectis", 'import package "release";\nmission "Composition" { publish release.release(true); }\n')
            _loaded, compiled = self.compile_loaded(entry)
            self.assertTrue(compiled.ok, compiled.diagnostics)

    def test_workspace_accepts_declared_dependency_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.core]\n"
                'entry = "core.vectis"\n'
                'version = "1.0.0"\n'
                "\n[packages.release]\n"
                'entry = "release.vectis"\n'
                "\n[packages.release.dependencies]\n"
                'core = "1.0.0"\n',
            )
            self.write(root, "core.vectis", "function ready(value) { return value; }\n")
            self.write(root, "release.vectis", 'import package "core";\nfunction release(value) { return core.ready(value); }\n')
            entry = self.write(root, "main.vectis", 'import package "release";\nmission "Composition" { publish release.release(true); }\n')
            workspace = load_workspace_program(entry)
            self.assertEqual(
                sorted(identity.label for _span, identity in workspace.function_scope.calls),
                ["core.vectis::ready", "release.vectis::release"],
            )

    def test_workspace_rejects_undeclared_dependency_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.core]\n"
                'entry = "core.vectis"\n'
                'version = "1.0.0"\n'
                "\n[packages.release]\n"
                'entry = "release.vectis"\n',
            )
            self.write(root, "core.vectis", "function ready(value) { return value; }\n")
            self.write(root, "release.vectis", 'import package "core";\nfunction release(value) { return core.ready(value); }\n')
            entry = self.write(root, "main.vectis", 'import package "release";\nmission "Composition" { publish release.release(true); }\n')
            with self.assertRaises(ModuleError) as caught:
                load_workspace_program(entry)
            self.assertIn("without a dependency contract", str(caught.exception))

    def test_module_browser_exposes_versions_and_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.core]\n"
                'entry = "core.vectis"\n'
                'version = "1.0.0"\n'
                "\n[packages.release]\n"
                'entry = "release.vectis"\n'
                'version = "2.0.0"\n'
                "\n[packages.release.dependencies]\n"
                'core = "1.0.0"\n',
            )
            self.write(root, "core.vectis", "function ready(value) { return value; }\n")
            self.write(root, "release.vectis", 'import package "core";\nfunction release(value) { return core.ready(value); }\n')
            payload = browse_project_modules(root)
            self.assertTrue(payload["ok"], payload)
            self.assertEqual(
                payload["packages"],
                [
                    {
                        "name": "core",
                        "entry": "core.vectis",
                        "version": "1.0.0",
                        "exports": ["ready"],
                    },
                    {
                        "name": "release",
                        "entry": "release.vectis",
                        "version": "2.0.0",
                        "dependencies": [
                            {"name": "core", "version": "1.0.0"}
                        ],
                        "exports": ["release"],
                    },
                ],
            )

    def test_module_browser_reports_undeclared_composition(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.core]\n"
                'entry = "core.vectis"\n'
                'version = "1.0.0"\n'
                "\n[packages.release]\n"
                'entry = "release.vectis"\n',
            )
            self.write(root, "core.vectis", "function ready(value) { return value; }\n")
            self.write(root, "release.vectis", 'import package "core";\nfunction release(value) { return core.ready(value); }\n')
            payload = browse_project_modules(root)
            self.assertFalse(payload["ok"])
            self.assertTrue(
                any(
                    "without a dependency contract" in item["message"]
                    for item in payload["package_diagnostics"]
                ),
                payload,
            )

    def test_scaffold_and_starter_template_declare_exact_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            initialize_project(root)
            manifest = load_package_manifest(root, require=True)
            readiness = manifest.package("readiness")
            self.assertEqual(readiness.version, "1.0.0")

        preview = template_preview("starter")
        manifest_file = next(
            item
            for item in preview["files"]
            if item["path"] == "vectis.toml"
        )
        self.assertIn('version = "1.0.0"', manifest_file["content"])


if __name__ == "__main__":
    unittest.main()
