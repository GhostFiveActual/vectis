# GHOST FIVE // VECTIS
# Regression coverage for deterministic project packages and package imports.
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from vectis.compiler import compile_program
from vectis.formatter import format_program
from vectis.lsp_semantic import SEMANTIC_TOKEN_TYPES, semantic_tokens
from vectis.lsp_signature import signature_help
from vectis.lsp_workspace import (
    function_definition,
    function_references,
    function_rename,
    load_workspace_program,
)
from vectis.module_browser import browse_project_modules
from vectis.modules import ModuleError, load_program_file
from vectis.package_manifest import (
    PackageManifestError,
    load_package_manifest,
    package_entry_path,
)
from vectis.parser import parse
from vectis.runtime import Runtime


def decoded_tokens(
    source: str,
) -> list[tuple[int, int, int, str, int]]:
    data = semantic_tokens(source)["data"]
    items: list[tuple[int, int, int, str, int]] = []
    line = 0
    start = 0
    for index in range(0, len(data), 5):
        delta_line = data[index]
        delta_start = data[index + 1]
        length = data[index + 2]
        token_type = data[index + 3]
        modifiers = data[index + 4]
        line += delta_line
        start = (
            delta_start
            if delta_line
            else start + delta_start
        )
        items.append(
            (
                line,
                start,
                length,
                SEMANTIC_TOKEN_TYPES[token_type],
                modifiers,
            )
        )
    return items


class PackageImportTests(unittest.TestCase):
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
        packages: str = "",
    ) -> None:
        (root / "vectis.toml").write_text(
            "# GHOST FIVE // VECTIS\n"
            "[project]\n"
            'name = "package-test"\n'
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

    def test_manifest_is_sorted_and_project_relative(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.zeta]\n"
                'entry = "packages/zeta/index.vectis"\n'
                "\n[packages.alpha]\n"
                'entry = "packages/alpha.vectis"\n',
            )
            self.write(
                root,
                "packages/zeta/index.vectis",
                "function value() { return 2; }\n",
            )
            self.write(
                root,
                "packages/alpha.vectis",
                "function value() { return 1; }\n",
            )
            manifest = load_package_manifest(root, require=True)
            self.assertEqual(
                [(item.name, item.entry) for item in manifest.packages],
                [
                    ("alpha", "packages/alpha.vectis"),
                    ("zeta", "packages/zeta/index.vectis"),
                ],
            )
            resolved = package_entry_path(
                root,
                manifest.package("alpha"),
            )
            self.assertEqual(
                resolved,
                (root / "packages/alpha.vectis").resolve(),
            )

    def test_manifest_missing_is_optional_until_package_import(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(
                load_package_manifest(root).packages,
                (),
            )
            with self.assertRaisesRegex(
                PackageManifestError,
                "require vectis.toml",
            ):
                load_package_manifest(root, require=True)

    def test_manifest_rejects_invalid_package_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.\"release-tools\"]\n"
                'entry = "release.vectis"\n',
            )
            with self.assertRaisesRegex(
                PackageManifestError,
                "VECTIS identifier",
            ):
                load_package_manifest(root)

    def test_manifest_rejects_non_vectis_entry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.release]\n"
                'entry = "release.txt"\n',
            )
            with self.assertRaisesRegex(
                PackageManifestError,
                r"\.vectis",
            ):
                load_package_manifest(root)

    def test_manifest_rejects_parent_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.release]\n"
                'entry = "../release.vectis"\n',
            )
            with self.assertRaisesRegex(
                PackageManifestError,
                "project-relative",
            ):
                load_package_manifest(root)

    def test_manifest_rejects_backslash_path_syntax(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.release]\n"
                'entry = "packages\\\\release.vectis"\n',
            )
            with self.assertRaisesRegex(
                PackageManifestError,
                "forward-slash",
            ):
                load_package_manifest(root)

    def test_manifest_rejects_unknown_package_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.release]\n"
                'entry = "release.vectis"\n'
                'registry = "local"\n',
            )
            with self.assertRaisesRegex(
                PackageManifestError,
                "unsupported fields",
            ):
                load_package_manifest(root)

    def test_manifest_rejects_invalid_toml(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "vectis.toml").write_text(
                "[packages.release\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                PackageManifestError,
                "invalid TOML",
            ):
                load_package_manifest(root)

    def test_manifest_rejects_drive_like_entry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.release]\n"
                'entry = "C:/release.vectis"\n',
            )
            with self.assertRaisesRegex(
                PackageManifestError,
                "project-relative",
            ):
                load_package_manifest(root)

    def test_package_syntax_parses_and_formats_contextually(self) -> None:
        source = (
            'import package "release" {ready, score} as rel;\n'
            'mission "Package" { publish rel.ready(96); }\n'
        )
        program = parse(source)
        statement = program.statements[0]
        self.assertTrue(statement.package)
        self.assertEqual(statement.path, "release")
        self.assertEqual(statement.names, ("ready", "score"))
        self.assertEqual(statement.alias, "rel")
        canonical = format_program(program)
        self.assertEqual(
            canonical,
            'import package "release" {ready, score} as rel;\n\n'
            'mission "Package" {\n'
            '    publish rel.ready(96);\n'
            '}\n',
        )
        self.assertEqual(
            format_program(parse(canonical)),
            canonical,
        )

        compatibility = parse(
            "function package(value) { return value; }\n"
        )
        self.assertEqual(
            compatibility.statements[0].name,
            "package",
        )

    def test_package_import_is_namespace_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.release]\n"
                'entry = "packages/release.vectis"\n',
            )
            self.write(
                root,
                "packages/release.vectis",
                "function ready(value) { return value; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import package "release";\n'
                'mission "Package" { publish release.ready(true); }\n',
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
                ["packages/release.vectis::ready"],
            )

            entry.write_text(
                'import package "release";\n'
                'mission "Package" { publish ready(true); }\n',
                encoding="utf-8",
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn(
                "not available as a bare call",
                str(caught.exception),
            )

    def test_package_selectors_restrict_export_surface(self) -> None:
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
                "function ready(value) { return value; }\n"
                "function score(value) { return value; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import package "gate" {ready};\n'
                'mission "Package" { publish gate.score(96); }\n',
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn(
                "not selected by package import",
                str(caught.exception),
            )

    def test_package_private_function_is_not_exported(self) -> None:
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
                "private function helper(value) { return value; }\n"
                "function ready(value) { return helper(value); }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import package "gate";\n'
                'mission "Package" { publish gate.helper(true); }\n',
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn(
                "is private to module",
                str(caught.exception),
            )

    def test_package_exports_are_direct_not_transitive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.outer]\n"
                'entry = "packages/outer.vectis"\n',
            )
            self.write(
                root,
                "packages/inner.vectis",
                "function hidden(value) { return value; }\n",
            )
            self.write(
                root,
                "packages/outer.vectis",
                'import "inner.vectis";\n'
                "function visible(value) { return hidden(value); }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import package "outer";\n'
                'mission "Package" { publish outer.hidden(true); }\n',
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn(
                "is not exported by package",
                str(caught.exception),
            )

    def test_package_names_disambiguate_colliding_exports(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.release]\n"
                'entry = "packages/release.vectis"\n'
                "\n[packages.security]\n"
                'entry = "packages/security.vectis"\n',
            )
            self.write(
                root,
                "packages/release.vectis",
                "function ready(value: number): boolean { return value >= 90; }\n",
            )
            self.write(
                root,
                "packages/security.vectis",
                "function ready(value: number): boolean { return value >= 99; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import package "release";\n'
                'import package "security";\n'
                'mission "Package" {\n'
                '    publish {release: release.ready(96), security: security.ready(96)};\n'
                '}\n',
            )
            _loaded, compiled = self.compile_loaded(entry)
            self.assertTrue(compiled.ok, compiled.diagnostics)
            result = Runtime(compiled.graph).execute()
            self.assertEqual(
                result.value_for("publish:0001"),
                {"release": True, "security": False},
            )

    def test_explicit_alias_overrides_package_qualifier(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.release]\n"
                'entry = "packages/release.vectis"\n',
            )
            self.write(
                root,
                "packages/release.vectis",
                "function ready(value) { return value; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import package "release" as rel;\n'
                'mission "Package" { publish rel.ready(true); }\n',
            )
            _loaded, compiled = self.compile_loaded(entry)
            self.assertTrue(compiled.ok, compiled.diagnostics)

            entry.write_text(
                'import package "release" as rel;\n'
                'mission "Package" { publish release.ready(true); }\n',
                encoding="utf-8",
            )
            with self.assertRaises(ModuleError):
                load_program_file(entry)

    def test_duplicate_package_imports_merge_selectors(self) -> None:
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
                "function ready(value) { return value; }\n"
                "function score(value) { return value; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import package "gate" {ready};\n'
                'import package "gate" {score};\n'
                'mission "Package" { publish {a: gate.ready(true), b: gate.score(7)}; }\n',
            )
            _loaded, compiled = self.compile_loaded(entry)
            self.assertTrue(compiled.ok, compiled.diagnostics)
            result = Runtime(compiled.graph).execute()
            self.assertEqual(
                result.value_for("publish:0001"),
                {"a": True, "b": 7},
            )

    def test_package_qualifier_collision_with_module_namespace_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.shared]\n"
                'entry = "packages/pkg.vectis"\n',
            )
            self.write(
                root,
                "packages/pkg.vectis",
                "function one(value) { return value; }\n",
            )
            self.write(
                root,
                "lib/shared.vectis",
                "namespace shared;\n"
                "function two(value) { return value; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import package "shared";\n'
                'import "lib/shared.vectis";\n'
                'mission "Package" { publish true; }\n',
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn(
                "duplicate module qualifier",
                str(caught.exception),
            )

    def test_package_qualifier_collision_with_alias_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.shared]\n"
                'entry = "packages/pkg.vectis"\n',
            )
            self.write(
                root,
                "packages/pkg.vectis",
                "function one(value) { return value; }\n",
            )
            self.write(
                root,
                "lib/other.vectis",
                "function two(value) { return value; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import package "shared";\n'
                'import "lib/other.vectis" as shared;\n'
                'mission "Package" { publish true; }\n',
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn(
                "duplicate module qualifier",
                str(caught.exception),
            )

    def test_package_key_wins_over_entry_namespace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.release]\n"
                'entry = "packages/entry.vectis"\n',
            )
            self.write(
                root,
                "packages/entry.vectis",
                "namespace internal;\n"
                "function ready(value) { return value; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import package "release";\n'
                'mission "Package" { publish release.ready(true); }\n',
            )
            _loaded, compiled = self.compile_loaded(entry)
            self.assertTrue(compiled.ok, compiled.diagnostics)

            entry.write_text(
                'import package "release";\n'
                'mission "Package" { publish internal.ready(true); }\n',
                encoding="utf-8",
            )
            with self.assertRaises(ModuleError):
                load_program_file(entry)

    def test_package_dependency_does_not_leak_through_parent_path_import(self) -> None:
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
                "function ready(value) { return value; }\n",
            )
            self.write(
                root,
                "lib/outer.vectis",
                'import package "gate";\n'
                "function visible(value) { return gate.ready(value); }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/outer.vectis";\n'
                'mission "Package" { publish ready(true); }\n',
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn(
                "not available as a bare call",
                str(caught.exception),
            )

    def test_package_identity_remains_project_relative_module_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.gate]\n"
                'entry = "packages/gate/index.vectis"\n',
            )
            self.write(
                root,
                "packages/gate/index.vectis",
                "function ready(value) { return value; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import package "gate";\n'
                'mission "Package" { publish gate.ready(true); }\n',
            )
            loaded = load_program_file(entry)
            self.assertEqual(
                [
                    identity.label
                    for _span, identity in loaded.function_scope.calls
                ],
                ["packages/gate/index.vectis::ready"],
            )

    def test_package_identity_controls_type_validation(self) -> None:
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
                "function score(value: number): number { return value; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import package "gate";\n'
                'mission "Package" { publish gate.score("bad"); }\n',
            )
            _loaded, compiled = self.compile_loaded(entry)
            self.assertFalse(compiled.ok)
            self.assertTrue(
                any(
                    "Argument 1 to score() must be number" in item.message
                    for item in compiled.diagnostics
                ),
                compiled.diagnostics,
            )

    def test_package_import_requires_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entry = self.write(
                root,
                "main.vectis",
                'import package "gate";\n'
                'mission "Package" { publish true; }\n',
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn(
                "require vectis.toml",
                str(caught.exception),
            )

    def test_unknown_package_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            entry = self.write(
                root,
                "main.vectis",
                'import package "missing";\n'
                'mission "Package" { publish true; }\n',
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn(
                "unknown package 'missing'",
                str(caught.exception),
            )

    def test_missing_package_entry_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.gate]\n"
                'entry = "packages/missing.vectis"\n',
            )
            entry = self.write(
                root,
                "main.vectis",
                'import package "gate";\n'
                'mission "Package" { publish true; }\n',
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn(
                "package entry does not exist",
                str(caught.exception),
            )

    def test_package_entry_must_remain_pure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.bad]\n"
                'entry = "packages/bad.vectis"\n',
            )
            self.write(
                root,
                "packages/bad.vectis",
                'mission "Hidden" { publish true; }\n',
            )
            entry = self.write(
                root,
                "main.vectis",
                'import package "bad";\n'
                'mission "Package" { publish true; }\n',
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn(
                "imported modules may contain only",
                str(caught.exception),
            )

    def test_package_cycle_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.a]\n"
                'entry = "packages/a.vectis"\n',
            )
            self.write(
                root,
                "packages/a.vectis",
                'import "../lib/b.vectis";\n'
                "function a(value) { return b(value); }\n",
            )
            self.write(
                root,
                "lib/b.vectis",
                'import package "a";\n'
                "function b(value) { return a(value); }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import package "a";\n'
                'mission "Package" { publish a.a(true); }\n',
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn(
                "import cycle is not allowed",
                str(caught.exception),
            )

    def test_workspace_overlay_can_supply_package_entry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.gate]\n"
                'entry = "packages/gate.vectis"\n',
            )
            package_entry = root / "packages/gate.vectis"
            source = (
                'import package "gate";\n'
                'mission "Package" { publish gate.ready(true); }\n'
            )
            entry = self.write(root, "main.vectis", source)
            workspace = load_workspace_program(
                entry,
                overlays={
                    package_entry.resolve(): (
                        "function ready(value) { return value; }\n"
                    )
                },
            )
            self.assertEqual(
                [
                    identity.label
                    for _span, identity in workspace.function_scope.calls
                ],
                ["packages/gate.vectis::ready"],
            )

    def test_navigation_references_and_rename_follow_package_export(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(
                root,
                "\n[packages.gate]\n"
                'entry = "packages/gate.vectis"\n',
            )
            library = self.write(
                root,
                "packages/gate.vectis",
                "function ready(value) { return value; }\n",
            )
            source = (
                'import package "gate";\n'
                'mission "Package" { publish gate.ready(true); }\n'
            )
            entry = self.write(root, "main.vectis", source)
            workspace = load_workspace_program(entry)
            line = 1
            character = source.splitlines()[line].rindex("ready") + 2
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
            references = function_references(
                workspace,
                path=entry,
                line=line,
                character=character,
                include_declaration=True,
            )
            self.assertEqual(len(references), 2)
            edit = function_rename(
                workspace,
                path=entry,
                line=line,
                character=character,
                new_name="approved",
            )
            self.assertIsNotNone(edit)
            self.assertEqual(
                len(edit["changes"][entry.resolve().as_uri()]),
                1,
            )
            self.assertEqual(
                len(edit["changes"][library.resolve().as_uri()]),
                1,
            )

    def test_signature_help_uses_package_identity(self) -> None:
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
                "function ready(value: number, threshold: number): boolean {\n"
                "    return value >= threshold;\n"
                "}\n",
            )
            source = (
                'import package "gate";\n'
                'mission "Package" { publish gate.ready(96, 90); }\n'
            )
            entry = self.write(root, "main.vectis", source)
            workspace = load_workspace_program(entry)
            line = 1
            character = source.splitlines()[line].index("90") + 1
            result = signature_help(
                source,
                line=line,
                character=character,
                workspace=workspace,
                path=entry,
            )
            self.assertIsNotNone(result)
            self.assertEqual(
                result["signatures"][0]["label"],
                "ready(value: number, threshold: number): boolean",
            )

    def test_semantic_tokens_mark_package_context_only(self) -> None:
        source = (
            'import package "gate";\n'
            'mission "Package" { publish gate.ready(true); }\n'
            "function package(value) { return value; }\n"
        )
        items = decoded_tokens(source)
        slices = [
            (
                source.splitlines()[line][start:start + length],
                kind,
                modifiers,
            )
            for line, start, length, kind, modifiers in items
        ]
        self.assertIn(("package", "keyword", 0), slices)
        self.assertIn(("ready", "function", 0), slices)
        self.assertIn(("package", "function", 1), slices)

    def test_module_browser_exposes_package_catalog_and_exports(self) -> None:
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
                "private function helper(value) { return value; }\n"
                "function ready(value) { return helper(value); }\n",
            )
            self.write(
                root,
                "main.vectis",
                'import package "gate";\n'
                'mission "Package" { publish gate.ready(true); }\n',
            )
            payload = browse_project_modules(root)
            self.assertTrue(payload["ok"], payload)
            self.assertEqual(
                payload["packages"],
                [
                    {
                        "name": "gate",
                        "entry": "packages/gate.vectis",
                        "exports": ["ready"],
                    }
                ],
            )
            entry = next(
                item
                for item in payload["modules"]
                if item["path"] == "main.vectis"
            )
            self.assertEqual(
                entry["imports"][0]["package"],
                "gate",
            )
            self.assertEqual(
                entry["imports"][0]["target"],
                "packages/gate.vectis",
            )
            self.assertNotIn(str(root.resolve()), repr(payload))


if __name__ == "__main__":
    unittest.main()
