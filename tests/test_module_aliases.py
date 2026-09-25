# GHOST FIVE // VECTIS
# Regression coverage for RFC 0025 module aliases and qualified calls.
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from vectis.ast import CallExpression, ImportStatement, Mission, PublishStatement
from vectis.compiler import compile_program
from vectis.formatter import format_program
from vectis.lsp_position import contains_lsp_position
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
from vectis.parser import parse
from vectis.runtime import Runtime


class ModuleAliasTests(unittest.TestCase):
    def project(self, root: Path) -> None:
        (root / "vectis.toml").write_text(
            "# GHOST FIVE // VECTIS\n[project]\n",
            encoding="utf-8",
        )

    def write(self, root: Path, relative: str, source: str) -> Path:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
        return path

    def compile_loaded(self, entry: Path):
        loaded = load_program_file(entry)
        compiled = compile_program(
            loaded.program,
            function_scope=loaded.function_scope,
        )
        return loaded, compiled

    def decoded_tokens(self, source: str) -> list[tuple[int, int, int, str, int]]:
        data = semantic_tokens(source)["data"]
        result = []
        line = 0
        start = 0
        for index in range(0, len(data), 5):
            delta_line = data[index]
            delta_start = data[index + 1]
            line += delta_line
            start = delta_start if delta_line else start + delta_start
            result.append(
                (
                    line,
                    start,
                    data[index + 2],
                    SEMANTIC_TOKEN_TYPES[data[index + 3]],
                    data[index + 4],
                )
            )
        return result

    def test_alias_syntax_parses_and_formats_contextually(self) -> None:
        source = (
            'import "lib/gate.vectis" {ready} as gate;\n'
            'mission "Alias" { publish gate.ready(96); }\n'
        )
        program = parse(source)
        imported = program.statements[0]
        self.assertIsInstance(imported, ImportStatement)
        self.assertEqual(imported.names, ("ready",))
        self.assertEqual(imported.alias, "gate")
        mission = program.statements[1]
        self.assertIsInstance(mission, Mission)
        publish = mission.body.statements[0]
        self.assertIsInstance(publish, PublishStatement)
        call = publish.value
        self.assertIsInstance(call, CallExpression)
        self.assertEqual(call.qualifier, "gate")
        self.assertEqual(call.name, "ready")
        self.assertEqual(
            format_program(program),
            'import "lib/gate.vectis" {ready} as gate;\n\n'
            'mission "Alias" {\n'
            '    publish gate.ready(96);\n'
            '}\n',
        )

    def test_as_remains_a_valid_contextual_function_name(self) -> None:
        program = parse(
            "function as(value) { return value; }\n"
            'mission "Context" { publish as(true); }\n'
        )
        compiled = compile_program(program)
        self.assertTrue(compiled.ok, compiled.diagnostics)

    def test_qualified_calls_disambiguate_colliding_functions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(
                root,
                "lib/release.vectis",
                "function ready(value: number): boolean { return value >= 90; }\n",
            )
            self.write(
                root,
                "lib/security.vectis",
                "function ready(value: number): boolean { return value >= 95; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/release.vectis" as release;\n'
                'import "lib/security.vectis" as security;\n'
                'mission "Alias" {\n'
                '    publish {release: release.ready(92), security: security.ready(92)};\n'
                '}\n',
            )
            loaded, compiled = self.compile_loaded(entry)
            self.assertTrue(compiled.ok, compiled.diagnostics)
            targets = sorted(
                identity.label
                for _span, identity in loaded.function_scope.calls
            )
            self.assertEqual(
                targets,
                ["lib/release.vectis::ready", "lib/security.vectis::ready"],
            )
            result = Runtime(compiled.graph).execute()
            self.assertEqual(
                result.value_for("publish:0001"),
                {"release": True, "security": False},
            )

    def test_alias_import_does_not_create_bare_binding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(
                root,
                "lib/gate.vectis",
                "function ready(value) { return value; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/gate.vectis" as gate;\n'
                'mission "Alias" { publish ready(true); }\n',
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn("not available as a bare call", str(caught.exception))

    def test_selective_alias_restricts_qualified_surface(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(
                root,
                "lib/gate.vectis",
                "function ready(value) { return value; }\n"
                "function score(value) { return value; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/gate.vectis" {ready} as gate;\n'
                'mission "Alias" { publish gate.score(96); }\n',
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn("not selected by module alias", str(caught.exception))

    def test_alias_cannot_access_private_function(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(
                root,
                "lib/gate.vectis",
                "private function hidden(value) { return value; }\n"
                "function ready(value) { return hidden(value); }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/gate.vectis" as gate;\n'
                'mission "Alias" { publish gate.hidden(true); }\n',
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn("private to module", str(caught.exception))

    def test_unknown_alias_fails_during_module_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            entry = self.write(
                root,
                "main.vectis",
                'mission "Alias" { publish missing.ready(true); }\n',
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn("unknown module alias", str(caught.exception))

    def test_duplicate_alias_in_one_module_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(root, "lib/a.vectis", "function a(value) { return value; }\n")
            self.write(root, "lib/b.vectis", "function b(value) { return value; }\n")
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/a.vectis" as shared;\n'
                'import "lib/b.vectis" as shared;\n'
                'mission "Alias" { publish true; }\n',
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn("duplicate module alias", str(caught.exception))

    def test_alias_surface_is_direct_not_transitive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(
                root,
                "lib/shared.vectis",
                "function helper(value) { return value; }\n",
            )
            self.write(
                root,
                "lib/gate.vectis",
                'import "shared.vectis";\n'
                "function ready(value) { return helper(value); }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/gate.vectis" as gate;\n'
                'mission "Alias" { publish gate.helper(true); }\n',
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn("not declared by aliased module", str(caught.exception))

    def test_aliased_dependency_does_not_leak_through_bare_parent_import(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(
                root,
                "lib/shared.vectis",
                "function helper(value) { return value; }\n",
            )
            self.write(
                root,
                "lib/gate.vectis",
                'import "shared.vectis" as shared;\n'
                "function ready(value) { return shared.helper(value); }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/gate.vectis";\n'
                'mission "Alias" { publish helper(true); }\n',
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn("not available as a bare call", str(caught.exception))

    def test_local_and_qualified_same_name_can_both_execute(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(
                root,
                "lib/gate.vectis",
                "function ready(value: number): boolean { return value >= 90; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/gate.vectis" as gate;\n'
                "function ready(value: number): boolean { return value >= 50; }\n"
                'mission "Alias" { publish {local: ready(60), remote: gate.ready(60)}; }\n',
            )
            _loaded, compiled = self.compile_loaded(entry)
            self.assertTrue(compiled.ok, compiled.diagnostics)
            result = Runtime(compiled.graph).execute()
            self.assertEqual(
                result.value_for("publish:0001"),
                {"local": True, "remote": False},
            )

    def test_qualified_identity_controls_type_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(
                root,
                "lib/gate.vectis",
                "function score(value: number): number { return value; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/gate.vectis" as gate;\n'
                'mission "Alias" { publish gate.score("bad"); }\n',
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

    def test_qualified_call_without_module_scope_fails_closed(self) -> None:
        program = parse(
            'mission "Alias" { publish gate.ready(true); }\n'
        )
        compiled = compile_program(program)
        self.assertFalse(compiled.ok)
        self.assertTrue(
            any("Unknown function: ready" in item.message for item in compiled.diagnostics),
            compiled.diagnostics,
        )

    def test_navigation_references_and_rename_use_qualified_member(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            library = self.write(
                root,
                "lib/gate.vectis",
                "function ready(value) { return value; }\n",
            )
            source = (
                'import "lib/gate.vectis" as ready;\n'
                'mission "Alias" { publish ready.ready(true); }\n'
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
            self.assertEqual(definition["uri"], library.resolve().as_uri())
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
            self.assertEqual(len(edit["changes"][entry.resolve().as_uri()]), 1)
            self.assertEqual(len(edit["changes"][library.resolve().as_uri()]), 1)

    def test_signature_help_uses_qualified_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(
                root,
                "lib/gate.vectis",
                "function ready(value: number, threshold: number): boolean {\n"
                "    return value >= threshold;\n"
                "}\n",
            )
            source = (
                'import "lib/gate.vectis" as gate;\n'
                'mission "Alias" { publish gate.ready(96, 90); }\n'
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

    def test_semantic_tokens_mark_alias_context_and_qualified_function(self) -> None:
        source = (
            'import "lib/gate.vectis" as gate;\n'
            'mission "Alias" { publish gate.ready(true); }\n'
        )
        items = self.decoded_tokens(source)
        slices = [
            (source.splitlines()[line][start:start + length], kind, modifiers)
            for line, start, length, kind, modifiers in items
        ]
        self.assertIn(("as", "keyword", 0), slices)
        self.assertIn(("gate", "variable", 1), slices)
        self.assertIn(("ready", "function", 0), slices)

    def test_module_browser_exposes_alias(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(
                root,
                "lib/gate.vectis",
                "function ready(value) { return value; }\n",
            )
            self.write(
                root,
                "main.vectis",
                'import "lib/gate.vectis" as gate;\n'
                'mission "Alias" { publish gate.ready(true); }\n',
            )
            payload = browse_project_modules(root)
            entry = next(
                item for item in payload["modules"]
                if item["path"] == "main.vectis"
            )
            self.assertEqual(entry["imports"][0]["alias"], "gate")


if __name__ == "__main__":
    unittest.main()
