# GHOST FIVE // VECTIS
# Regression coverage for exact local multi-project package dependencies.
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from vectis.compiler import compile_program
from vectis.lsp_workspace import (
    function_definition,
    function_rename,
    load_workspace_program,
)
from vectis.module_browser import browse_project_modules
from vectis.modules import ModuleError, load_program_file
from vectis.package_fingerprint import (
    PackageFingerprintError,
    package_fingerprint,
)
from vectis.package_manifest import (
    PackageManifestError,
    load_package_manifest,
)
from vectis.package_reference import (
    PackageReferenceError,
    resolve_package_reference,
)
from vectis.runtime import Runtime


ZERO_FP = "0" * 64
ONE_FP = "1" * 64


class MultiProjectDependencyTests(unittest.TestCase):
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
        body: str,
        *,
        name: str = "multi-project-test",
    ) -> None:
        root.mkdir(parents=True, exist_ok=True)
        (root / "vectis.toml").write_text(
            "# GHOST FIVE // VECTIS\n"
            "[project]\n"
            f'name = "{name}"\n'
            + body,
            encoding="utf-8",
        )

    def simple_provider(
        self,
        root: Path,
        *,
        package: str = "core",
        version: str = "1.0.0",
        source: str = "function ready(value) { return value; }\n",
    ) -> str:
        self.project(
            root,
            f"\n[packages.{package}]\n"
            f'entry = "{package}.vectis"\n'
            f'version = "{version}"\n',
            name=f"provider-{package}",
        )
        self.write(root, f"{package}.vectis", source)
        return package_fingerprint(root, package)

    def consumer_binding(
        self,
        root: Path,
        *,
        alias: str,
        project: str,
        package: str,
        version: str,
        fingerprint: str,
        packages: str = "",
    ) -> None:
        self.project(
            root,
            f"\n[local_dependencies.{alias}]\n"
            f'project = "{project}"\n'
            f'package = "{package}"\n'
            f'version = "{version}"\n'
            f'fingerprint = "{fingerprint}"\n'
            + packages,
            name="consumer",
        )

    def compile_loaded(self, entry: Path):
        loaded = load_program_file(entry)
        compiled = compile_program(
            loaded.program,
            function_scope=loaded.function_scope,
        )
        return loaded, compiled

    def test_manifest_parses_sorted_local_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[local_dependencies.zeta]\n"
                'project = "../zeta"\n'
                'package = "core"\n'
                'version = "2.0.0"\n'
                f'fingerprint = "{ONE_FP}"\n'
                "\n[local_dependencies.alpha]\n"
                'project = "../alpha"\n'
                'package = "core"\n'
                'version = "1.0.0"\n'
                f'fingerprint = "{ZERO_FP}"\n'
                "\n[packages.release]\n"
                'entry = "release.vectis"\n'
                'version = "3.0.0"\n'
                "\n[packages.release.dependencies]\n"
                'alpha = "1.0.0"\n',
            )
            manifest = load_package_manifest(root, require=True)
            self.assertEqual(
                [item.name for item in manifest.local_dependencies],
                ["alpha", "zeta"],
            )
            alpha = manifest.local_dependency("alpha")
            self.assertIsNotNone(alpha)
            self.assertEqual(alpha.project, "../alpha")
            self.assertEqual(alpha.package, "core")
            self.assertEqual(alpha.version, "1.0.0")
            self.assertEqual(alpha.fingerprint, ZERO_FP)
            self.assertEqual(
                manifest.package("release").dependency("alpha"),
                "1.0.0",
            )

    def test_manifest_rejects_noncanonical_local_project_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for value in (
                "/shared",
                "C:/shared",
                "shared\\core",
                "./shared",
                "shared//core",
                "shared/./core",
                "shared/../core",
            ):
                with self.subTest(value=value):
                    self.project(
                        root,
                        "\n[local_dependencies.core]\n"
                        f"project = '{value}'\n"
                        'package = "core"\n'
                        'version = "1.0.0"\n'
                        f'fingerprint = "{ZERO_FP}"\n',
                    )
                    with self.assertRaisesRegex(
                        PackageManifestError,
                        "canonical relative path",
                    ):
                        load_package_manifest(root, require=True)

    def test_manifest_rejects_invalid_local_dependency_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for value in ("abc", "A" * 64, "g" * 64):
                with self.subTest(value=value):
                    self.project(
                        root,
                        "\n[local_dependencies.core]\n"
                        'project = "../core"\n'
                        'package = "core"\n'
                        'version = "1.0.0"\n'
                        f'fingerprint = "{value}"\n',
                    )
                    with self.assertRaisesRegex(
                        PackageManifestError,
                        "64 lowercase SHA-256",
                    ):
                        load_package_manifest(root, require=True)

    def test_manifest_requires_exact_local_dependency_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[local_dependencies.core]\n"
                'project = "../core"\n'
                'package = "core"\n'
                'version = "1.0.0"\n',
            )
            with self.assertRaisesRegex(
                PackageManifestError,
                "define exactly project, package, version, and fingerprint",
            ):
                load_package_manifest(root, require=True)

    def test_manifest_rejects_package_and_local_alias_collision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.core]\n"
                'entry = "core.vectis"\n'
                'version = "1.0.0"\n'
                "\n[local_dependencies.core]\n"
                'project = "../provider"\n'
                'package = "core"\n'
                'version = "1.0.0"\n'
                f'fingerprint = "{ZERO_FP}"\n',
            )
            with self.assertRaisesRegex(
                PackageManifestError,
                "must not collide",
            ):
                load_package_manifest(root, require=True)

    def test_manifest_rejects_package_dependency_version_mismatch_with_binding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[local_dependencies.core_ref]\n"
                'project = "../provider"\n'
                'package = "core"\n'
                'version = "2.0.0"\n'
                f'fingerprint = "{ZERO_FP}"\n'
                "\n[packages.release]\n"
                'entry = "release.vectis"\n'
                'version = "1.0.0"\n'
                "\n[packages.release.dependencies]\n"
                'core_ref = "1.0.0"\n',
            )
            with self.assertRaisesRegex(
                PackageManifestError,
                "local dependency pins '2.0.0'",
            ):
                load_package_manifest(root, require=True)

    def test_reference_rejects_missing_local_project(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "consumer"
            self.consumer_binding(
                root,
                alias="core_ref",
                project="../missing",
                package="core",
                version="1.0.0",
                fingerprint=ZERO_FP,
            )
            with self.assertRaisesRegex(
                PackageReferenceError,
                "project does not exist",
            ):
                resolve_package_reference(root, "core_ref")

    def test_reference_rejects_missing_target_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            provider = base / "provider"
            provider.mkdir()
            consumer = base / "consumer"
            self.consumer_binding(
                consumer,
                alias="core_ref",
                project="../provider",
                package="core",
                version="1.0.0",
                fingerprint=ZERO_FP,
            )
            with self.assertRaisesRegex(
                PackageReferenceError,
                "target manifest is invalid",
            ):
                resolve_package_reference(consumer, "core_ref")

    def test_reference_rejects_unknown_target_package(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            provider = base / "provider"
            self.project(provider, "", name="provider")
            consumer = base / "consumer"
            self.consumer_binding(
                consumer,
                alias="core_ref",
                project="../provider",
                package="core",
                version="1.0.0",
                fingerprint=ZERO_FP,
            )
            with self.assertRaisesRegex(
                PackageReferenceError,
                "target package 'core' is not declared",
            ):
                resolve_package_reference(consumer, "core_ref")

    def test_reference_rejects_target_version_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            provider = base / "provider"
            fingerprint = self.simple_provider(
                provider,
                version="2.0.0",
            )
            consumer = base / "consumer"
            self.consumer_binding(
                consumer,
                alias="core_ref",
                project="../provider",
                package="core",
                version="1.0.0",
                fingerprint=fingerprint,
            )
            with self.assertRaisesRegex(
                PackageReferenceError,
                "requires version '1.0.0', found '2.0.0'",
            ):
                resolve_package_reference(consumer, "core_ref")

    def test_reference_rejects_fingerprint_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            provider = base / "provider"
            self.simple_provider(provider)
            consumer = base / "consumer"
            self.consumer_binding(
                consumer,
                alias="core_ref",
                project="../provider",
                package="core",
                version="1.0.0",
                fingerprint=ZERO_FP,
            )
            with self.assertRaisesRegex(
                PackageReferenceError,
                "fingerprint mismatch",
            ):
                resolve_package_reference(consumer, "core_ref")

    def test_project_entry_can_import_exact_external_package(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            provider = base / "provider"
            fingerprint = self.simple_provider(
                provider,
                source=(
                    "function ready(value: number): boolean { "
                    "return value >= 90; }\n"
                ),
            )
            consumer = base / "consumer"
            self.consumer_binding(
                consumer,
                alias="shared_core",
                project="../provider",
                package="core",
                version="1.0.0",
                fingerprint=fingerprint,
            )
            entry = self.write(
                consumer,
                "main.vectis",
                'import package "shared_core";\n'
                'mission "Cross project" { publish shared_core.ready(96); }\n',
            )
            loaded, compiled = self.compile_loaded(entry)
            self.assertTrue(compiled.ok, compiled.diagnostics)
            result = Runtime(compiled.graph).execute()
            self.assertIs(result.value_for("publish:0001"), True)
            self.assertEqual(
                [
                    identity.label
                    for _span, identity in loaded.function_scope.calls
                ],
                ["../provider/core.vectis::ready"],
            )

    def test_local_package_can_depend_on_external_binding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            provider = base / "provider"
            fingerprint = self.simple_provider(provider)
            consumer = base / "consumer"
            self.consumer_binding(
                consumer,
                alias="core_ref",
                project="../provider",
                package="core",
                version="1.0.0",
                fingerprint=fingerprint,
                packages=(
                    "\n[packages.release]\n"
                    'entry = "release.vectis"\n'
                    'version = "2.0.0"\n'
                    "\n[packages.release.dependencies]\n"
                    'core_ref = "1.0.0"\n'
                ),
            )
            self.write(
                consumer,
                "release.vectis",
                'import package "core_ref";\n'
                "function release(value) { return core_ref.ready(value); }\n",
            )
            entry = self.write(
                consumer,
                "main.vectis",
                'import package "release";\n'
                'mission "Composition" { publish release.release(true); }\n',
            )
            _loaded, compiled = self.compile_loaded(entry)
            self.assertTrue(compiled.ok, compiled.diagnostics)

    def test_local_package_requires_external_dependency_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            provider = base / "provider"
            fingerprint = self.simple_provider(provider)
            consumer = base / "consumer"
            self.consumer_binding(
                consumer,
                alias="core_ref",
                project="../provider",
                package="core",
                version="1.0.0",
                fingerprint=fingerprint,
                packages=(
                    "\n[packages.release]\n"
                    'entry = "release.vectis"\n'
                    'version = "2.0.0"\n'
                ),
            )
            self.write(
                consumer,
                "release.vectis",
                'import package "core_ref";\n'
                "function release(value) { return core_ref.ready(value); }\n",
            )
            entry = self.write(
                consumer,
                "main.vectis",
                'import package "release";\n'
                'mission "Composition" { publish release.release(true); }\n',
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn(
                "without a dependency contract",
                str(caught.exception),
            )

    def test_external_path_imported_helper_stays_in_provider_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            provider = base / "provider"
            self.project(
                provider,
                "\n[packages.core]\n"
                'entry = "pkg/index.vectis"\n'
                'version = "1.0.0"\n',
                name="provider",
            )
            self.write(
                provider,
                "pkg/helper.vectis",
                "function helper(value) { return value; }\n",
            )
            self.write(
                provider,
                "pkg/index.vectis",
                'import "helper.vectis";\n'
                "function ready(value) { return helper(value); }\n",
            )
            fingerprint = package_fingerprint(provider, "core")
            consumer = base / "consumer"
            self.consumer_binding(
                consumer,
                alias="core_ref",
                project="../provider",
                package="core",
                version="1.0.0",
                fingerprint=fingerprint,
            )
            entry = self.write(
                consumer,
                "main.vectis",
                'import package "core_ref";\n'
                'mission "Boundary" { publish core_ref.ready(true); }\n',
            )
            loaded, compiled = self.compile_loaded(entry)
            self.assertTrue(compiled.ok, compiled.diagnostics)
            identities = sorted(
                identity.label
                for _span, identity in loaded.function_scope.declarations
            )
            self.assertIn(
                "../provider/pkg/helper.vectis::helper",
                identities,
            )
            self.assertIn(
                "../provider/pkg/index.vectis::ready",
                identities,
            )

    def test_path_import_cannot_bypass_nested_project_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            consumer = workspace / "consumer"
            provider = consumer / "deps" / "provider"
            fingerprint = self.simple_provider(provider)
            self.consumer_binding(
                consumer,
                alias="core_ref",
                project="deps/provider",
                package="core",
                version="1.0.0",
                fingerprint=fingerprint,
            )
            entry = self.write(
                consumer,
                "main.vectis",
                'import "deps/provider/core.vectis";\n'
                'mission "Boundary" { publish ready(true); }\n',
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn(
                "crosses a project boundary",
                str(caught.exception),
            )

    def test_external_path_import_cannot_escape_provider_project(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            provider = base / "provider"
            self.project(
                provider,
                "\n[packages.core]\n"
                'entry = "pkg/index.vectis"\n'
                'version = "1.0.0"\n',
                name="provider",
            )
            self.write(
                base,
                "outside.vectis",
                "function outside(value) { return value; }\n",
            )
            self.write(
                provider,
                "pkg/index.vectis",
                'import "../../outside.vectis";\n'
                "function ready(value) { return outside(value); }\n",
            )
            consumer = base / "consumer"
            self.consumer_binding(
                consumer,
                alias="core_ref",
                project="../provider",
                package="core",
                version="1.0.0",
                fingerprint=ZERO_FP,
            )
            entry = self.write(
                consumer,
                "main.vectis",
                'import package "core_ref";\n'
                'mission "Boundary" { publish true; }\n',
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn(
                "escapes the project root",
                str(caught.exception),
            )

    def test_transitive_multi_project_dependencies_resolve_in_owner_projects(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            core = base / "core-project"
            core_fingerprint = self.simple_provider(
                core,
                package="core",
                source="function ready(value) { return value; }\n",
            )

            policy = base / "policy-project"
            self.consumer_binding(
                policy,
                alias="core_ref",
                project="../core-project",
                package="core",
                version="1.0.0",
                fingerprint=core_fingerprint,
                packages=(
                    "\n[packages.policy]\n"
                    'entry = "policy.vectis"\n'
                    'version = "2.0.0"\n'
                    "\n[packages.policy.dependencies]\n"
                    'core_ref = "1.0.0"\n'
                ),
            )
            self.write(
                policy,
                "policy.vectis",
                'import package "core_ref";\n'
                "function allowed(value) { return core_ref.ready(value); }\n",
            )
            policy_fingerprint = package_fingerprint(policy, "policy")

            app = base / "app"
            self.consumer_binding(
                app,
                alias="policy_ref",
                project="../policy-project",
                package="policy",
                version="2.0.0",
                fingerprint=policy_fingerprint,
            )
            entry = self.write(
                app,
                "main.vectis",
                'import package "policy_ref";\n'
                'mission "Transitive" { publish policy_ref.allowed(true); }\n',
            )
            loaded, compiled = self.compile_loaded(entry)
            self.assertTrue(compiled.ok, compiled.diagnostics)
            result = Runtime(compiled.graph).execute()
            self.assertIs(result.value_for("publish:0001"), True)
            call_ids = sorted(
                identity.label
                for _span, identity in loaded.function_scope.calls
            )
            self.assertEqual(
                call_ids,
                [
                    "../core-project/core.vectis::ready",
                    "../policy-project/policy.vectis::allowed",
                ],
            )

    def test_cross_project_dependency_cycle_fails_fingerprinting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            alpha = base / "alpha"
            beta = base / "beta"
            self.project(
                alpha,
                "\n[local_dependencies.beta_ref]\n"
                'project = "../beta"\n'
                'package = "beta"\n'
                'version = "1.0.0"\n'
                f'fingerprint = "{ZERO_FP}"\n'
                "\n[packages.alpha]\n"
                'entry = "alpha.vectis"\n'
                'version = "1.0.0"\n'
                "\n[packages.alpha.dependencies]\n"
                'beta_ref = "1.0.0"\n',
                name="alpha",
            )
            self.project(
                beta,
                "\n[local_dependencies.alpha_ref]\n"
                'project = "../alpha"\n'
                'package = "alpha"\n'
                'version = "1.0.0"\n'
                f'fingerprint = "{ONE_FP}"\n'
                "\n[packages.beta]\n"
                'entry = "beta.vectis"\n'
                'version = "1.0.0"\n'
                "\n[packages.beta.dependencies]\n"
                'alpha_ref = "1.0.0"\n',
                name="beta",
            )
            self.write(alpha, "alpha.vectis", "function alpha() { return 1; }\n")
            self.write(beta, "beta.vectis", "function beta() { return 2; }\n")
            with self.assertRaisesRegex(
                PackageFingerprintError,
                "dependency cycle",
            ):
                package_fingerprint(alpha, "alpha")

    def test_external_selectors_and_aliases_preserve_package_surface(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            provider = base / "provider"
            fingerprint = self.simple_provider(
                provider,
                source=(
                    "function ready(value) { return value; }\n"
                    "function score(value) { return value; }\n"
                ),
            )
            consumer = base / "consumer"
            self.consumer_binding(
                consumer,
                alias="core_ref",
                project="../provider",
                package="core",
                version="1.0.0",
                fingerprint=fingerprint,
            )
            entry = self.write(
                consumer,
                "main.vectis",
                'import package "core_ref" {ready} as c;\n'
                'mission "Selectors" { publish c.ready(true); }\n',
            )
            _loaded, compiled = self.compile_loaded(entry)
            self.assertTrue(compiled.ok, compiled.diagnostics)

            entry.write_text(
                'import package "core_ref" {ready} as c;\n'
                'mission "Selectors" { publish c.score(7); }\n',
                encoding="utf-8",
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn(
                "not selected by module alias 'c'",
                str(caught.exception),
            )

    def test_workspace_navigation_and_rename_follow_external_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            provider = base / "provider"
            fingerprint = self.simple_provider(provider)
            library = provider / "core.vectis"
            consumer = base / "consumer"
            self.consumer_binding(
                consumer,
                alias="core_ref",
                project="../provider",
                package="core",
                version="1.0.0",
                fingerprint=fingerprint,
            )
            source = (
                'import package "core_ref";\n'
                'mission "Editor" { publish core_ref.ready(true); }\n'
            )
            entry = self.write(consumer, "main.vectis", source)
            workspace = load_workspace_program(entry)
            line = 1
            character = source.splitlines()[line].index("ready") + 2
            definition = function_definition(
                workspace,
                path=entry,
                line=line,
                character=character,
            )
            self.assertIsNotNone(definition)
            self.assertEqual(
                definition["uri"],
                library.resolve().as_uri(),
            )
            edit = function_rename(
                workspace,
                path=entry,
                line=line,
                character=character,
                new_name="approved",
            )
            self.assertIsNotNone(edit)
            self.assertIn(
                library.resolve().as_uri(),
                edit["changes"],
            )
            self.assertIn(
                entry.resolve().as_uri(),
                edit["changes"],
            )

    def test_browser_exposes_local_dependency_without_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            provider = base / "provider"
            fingerprint = self.simple_provider(provider)
            consumer = base / "consumer"
            self.consumer_binding(
                consumer,
                alias="core_ref",
                project="../provider",
                package="core",
                version="1.0.0",
                fingerprint=fingerprint,
            )
            self.write(
                consumer,
                "main.vectis",
                'import package "core_ref";\n'
                'mission "Browse" { publish core_ref.ready(true); }\n',
            )
            payload = browse_project_modules(consumer)
            self.assertTrue(payload["ok"], payload)
            self.assertEqual(payload["local_dependency_count"], 1)
            self.assertEqual(
                payload["local_dependencies"],
                [
                    {
                        "name": "core_ref",
                        "project": "../provider",
                        "package": "core",
                        "version": "1.0.0",
                        "fingerprint": fingerprint,
                        "target": "../provider/core.vectis",
                        "status": "resolved",
                    }
                ],
            )
            main = next(
                item for item in payload["modules"]
                if item["path"] == "main.vectis"
            )
            self.assertEqual(
                main["imports"][0]["target"],
                "../provider/core.vectis",
            )
            self.assertEqual(main["imports"][0]["status"], "resolved")
            self.assertNotIn(str(base.resolve()), repr(payload))

    def test_browser_reports_local_dependency_fingerprint_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            provider = base / "provider"
            self.simple_provider(provider)
            consumer = base / "consumer"
            self.consumer_binding(
                consumer,
                alias="core_ref",
                project="../provider",
                package="core",
                version="1.0.0",
                fingerprint=ZERO_FP,
            )
            self.write(
                consumer,
                "main.vectis",
                'import package "core_ref";\n'
                'mission "Browse" { publish true; }\n',
            )
            payload = browse_project_modules(consumer)
            self.assertFalse(payload["ok"])
            self.assertEqual(
                payload["local_dependencies"][0]["status"],
                "invalid",
            )
            self.assertTrue(
                any(
                    "fingerprint mismatch" in item["message"]
                    for item in payload["package_diagnostics"]
                ),
                payload,
            )
            self.assertNotIn(str(base.resolve()), repr(payload))

    def test_consumer_fingerprint_requires_exact_external_pin_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            provider = base / "provider"
            provider_fingerprint = self.simple_provider(provider)
            consumer = base / "consumer"
            self.consumer_binding(
                consumer,
                alias="core_ref",
                project="../provider",
                package="core",
                version="1.0.0",
                fingerprint=provider_fingerprint,
                packages=(
                    "\n[packages.release]\n"
                    'entry = "release.vectis"\n'
                    'version = "2.0.0"\n'
                    "\n[packages.release.dependencies]\n"
                    'core_ref = "1.0.0"\n'
                ),
            )
            self.write(
                consumer,
                "release.vectis",
                "function release(value) { return value; }\n",
            )
            before = package_fingerprint(consumer, "release")

            (provider / "core.vectis").write_text(
                "function ready(value) { return !value; }\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                PackageFingerprintError,
                "fingerprint mismatch",
            ):
                package_fingerprint(consumer, "release")

            refreshed = package_fingerprint(provider, "core")
            manifest = (consumer / "vectis.toml").read_text(encoding="utf-8")
            (consumer / "vectis.toml").write_text(
                manifest.replace(provider_fingerprint, refreshed),
                encoding="utf-8",
            )
            after = package_fingerprint(consumer, "release")
            self.assertNotEqual(before, after)

    def test_equivalent_multi_project_layout_has_portable_identity(self) -> None:
        def build(base: Path) -> str:
            provider = base / "provider"
            fingerprint = self.simple_provider(provider)
            consumer = base / "consumer"
            self.consumer_binding(
                consumer,
                alias="core_ref",
                project="../provider",
                package="core",
                version="1.0.0",
                fingerprint=fingerprint,
                packages=(
                    "\n[packages.release]\n"
                    'entry = "release.vectis"\n'
                    'version = "2.0.0"\n'
                    "\n[packages.release.dependencies]\n"
                    'core_ref = "1.0.0"\n'
                ),
            )
            self.write(
                consumer,
                "release.vectis",
                "function release(value) { return value; }\n",
            )
            return package_fingerprint(consumer, "release")

        with tempfile.TemporaryDirectory() as left_directory:
            with tempfile.TemporaryDirectory() as right_directory:
                self.assertEqual(
                    build(Path(left_directory)),
                    build(Path(right_directory)),
                )


if __name__ == "__main__":
    unittest.main()
