# GHOST FIVE // VECTIS
# Verifies module-scoped function identity across compilation and editor tooling.
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from vectis.compiler import compile_program
from vectis.lsp_signature import signature_help
from vectis.lsp_workspace import (
    function_definition,
    function_references,
    function_rename,
    load_workspace_program,
)
from vectis.module_browser import browse_project_modules
from vectis.modules import ModuleError, load_program_file
from vectis.runtime import Runtime


class ModuleFunctionIdentityTests(unittest.TestCase):
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

    def project(self, root: Path) -> None:
        (root / "vectis.toml").write_text(
            "[project]\n",
            encoding="utf-8",
        )

    def compile_loaded(self, entry: Path):
        loaded = load_program_file(entry)
        return loaded, compile_program(
            loaded.program,
            function_scope=loaded.function_scope,
        )

    def test_same_public_name_can_coexist_when_unused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(
                root,
                "lib/release.vectis",
                "function ready(value) { return value >= 90; }\n",
            )
            self.write(
                root,
                "lib/security.vectis",
                "function ready(value) { return value >= 95; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/release.vectis";\n'
                'import "lib/security.vectis";\n'
                'mission "Identity" { publish true; }\n',
            )

            loaded, compiled = self.compile_loaded(entry)
            self.assertTrue(compiled.ok, compiled.diagnostics)
            identities = {
                identity.label
                for _span, identity in loaded.function_scope.declarations
                if identity.name == "ready"
            }
            self.assertEqual(
                identities,
                {
                    "lib/release.vectis::ready",
                    "lib/security.vectis::ready",
                },
            )

    def test_ambiguous_bare_call_fails_during_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(
                root,
                "lib/release.vectis",
                "function ready(value) { return value >= 90; }\n",
            )
            self.write(
                root,
                "lib/security.vectis",
                "function ready(value) { return value >= 95; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/release.vectis";\n'
                'import "lib/security.vectis";\n'
                'mission "Identity" { publish ready(96); }\n',
            )

            with self.assertRaisesRegex(
                ModuleError,
                "function 'ready' is ambiguous",
            ):
                load_program_file(entry)

    def test_selective_import_disambiguates_same_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(
                root,
                "lib/release.vectis",
                "function ready(value: number): boolean {\n"
                "    return value >= 90;\n"
                "}\n",
            )
            self.write(
                root,
                "lib/security.vectis",
                "function ready(value: string): boolean {\n"
                '    return length(value) > 0;\n'
                "}\n"
                "function audit(value) { return value; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/release.vectis" {ready};\n'
                'import "lib/security.vectis" {audit};\n'
                'mission "Identity" { publish ready(96); }\n',
            )

            _loaded, compiled = self.compile_loaded(entry)
            self.assertTrue(compiled.ok, compiled.diagnostics)
            result = Runtime(compiled.graph).execute()
            self.assertTrue(result.success)
            self.assertIs(
                result.value_for("publish:0001"),
                True,
            )

    def test_local_function_wins_over_imported_same_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(
                root,
                "lib/gate.vectis",
                "function ready(value) { return value >= 90; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/gate.vectis";\n'
                "function ready(value) { return value >= 10; }\n"
                'mission "Identity" { publish ready(50); }\n',
            )

            _loaded, compiled = self.compile_loaded(entry)
            self.assertTrue(compiled.ok, compiled.diagnostics)
            result = Runtime(compiled.graph).execute()
            self.assertIs(
                result.value_for("publish:0001"),
                True,
            )

    def test_colliding_private_helpers_keep_module_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(
                root,
                "lib/release.vectis",
                "private function threshold(value: number): boolean {\n"
                "    return value >= 90;\n"
                "}\n"
                "function release_ready(value: number): boolean {\n"
                "    return threshold(value);\n"
                "}\n",
            )
            self.write(
                root,
                "lib/security.vectis",
                "private function threshold(value: number): boolean {\n"
                "    return value >= 95;\n"
                "}\n"
                "function security_ready(value: number): boolean {\n"
                "    return threshold(value);\n"
                "}\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/release.vectis";\n'
                'import "lib/security.vectis";\n'
                'mission "Identity" {\n'
                '    publish {\n'
                "        release: release_ready(92),\n"
                "        security: security_ready(92)\n"
                "    };\n"
                "}\n",
            )

            _loaded, compiled = self.compile_loaded(entry)
            self.assertTrue(compiled.ok, compiled.diagnostics)
            result = Runtime(compiled.graph).execute()
            self.assertEqual(
                result.value_for("publish:0001"),
                {
                    "release": True,
                    "security": False,
                },
            )

    def test_bound_identity_controls_type_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(
                root,
                "lib/release.vectis",
                "function score(value: number): number { return value; }\n",
            )
            self.write(
                root,
                "lib/security.vectis",
                "function score(value: string): string { return value; }\n"
                "function audit(value) { return value; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/release.vectis" {score};\n'
                'import "lib/security.vectis" {audit};\n'
                'mission "Identity" { publish score("bad"); }\n',
            )

            loaded = load_program_file(entry)
            compiled = compile_program(
                loaded.program,
                function_scope=loaded.function_scope,
            )
            self.assertFalse(compiled.ok)
            messages = [
                item.message
                for item in compiled.diagnostics
            ]
            self.assertTrue(
                any(
                    "Argument 1 to score() must be number"
                    in message
                    for message in messages
                ),
                messages,
            )

    def test_navigation_and_rename_are_identity_scoped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            release = self.write(
                root,
                "lib/release.vectis",
                "function ready(value) {\n"
                "    return value >= 90;\n"
                "}\n",
            )
            security = self.write(
                root,
                "lib/security.vectis",
                "function ready(value) { return value >= 95; }\n"
                "function audit(value) { return value; }\n",
            )
            entry_source = (
                'import "lib/release.vectis" {ready};\n'
                'import "lib/security.vectis" {audit};\n'
                'mission "Identity" { publish ready(96); }\n'
            )
            entry = self.write(
                root,
                "main.vectis",
                entry_source,
            )
            workspace = load_workspace_program(entry)
            line = 2
            character = (
                entry_source.splitlines()[line].index("ready")
                + 2
            )

            definition = function_definition(
                workspace,
                path=entry,
                line=line,
                character=character,
            )
            self.assertIsNotNone(definition)
            self.assertEqual(
                definition["uri"],
                release.resolve().as_uri(),
            )

            references = function_references(
                workspace,
                path=entry,
                line=line,
                character=character,
                include_declaration=True,
            )
            self.assertEqual(len(references), 3)
            self.assertNotIn(
                security.resolve().as_uri(),
                {
                    item["uri"]
                    for item in references
                },
            )

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
                2,
            )
            self.assertEqual(
                len(edit["changes"][release.resolve().as_uri()]),
                1,
            )
            self.assertNotIn(
                security.resolve().as_uri(),
                edit["changes"],
            )

    def test_signature_help_uses_bound_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(
                root,
                "lib/release.vectis",
                "function ready(\n"
                "    value: number,\n"
                "    threshold: number\n"
                "): boolean {\n"
                "    return value >= threshold;\n"
                "}\n",
            )
            self.write(
                root,
                "lib/security.vectis",
                "function ready(value: string): boolean {\n"
                "    return length(value) > 0;\n"
                "}\n"
                "function audit(value) { return value; }\n",
            )
            source = (
                'import "lib/release.vectis" {ready};\n'
                'import "lib/security.vectis" {audit};\n'
                'mission "Identity" { publish ready(96, 90); }\n'
            )
            entry = self.write(
                root,
                "main.vectis",
                source,
            )
            workspace = load_workspace_program(entry)
            line = 2
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

    def test_module_browser_exposes_project_relative_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(
                root,
                "lib/release.vectis",
                "function ready(value) { return value; }\n",
            )
            catalog = browse_project_modules(root)
            release = next(
                module
                for module in catalog["modules"]
                if module["path"] == "lib/release.vectis"
            )
            self.assertEqual(
                release["functions"][0]["identity"],
                "lib/release.vectis::ready",
            )


if __name__ == "__main__":
    unittest.main()
