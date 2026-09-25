# GHOST FIVE // VECTIS
# Regression coverage for RFC 0026 explicit namespace declarations.
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from vectis.ast import NamespaceDeclaration
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
from vectis.parser import ParserError, parse
from vectis.runtime import Runtime


class NamespaceDeclarationTests(unittest.TestCase):
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

    def test_namespace_syntax_parses_and_formats_contextually(self) -> None:
        source = (
            "namespace release;\n"
            "function ready(value) { return value; }\n"
        )
        program = parse(source)
        declaration = program.statements[0]
        self.assertIsInstance(declaration, NamespaceDeclaration)
        self.assertEqual(declaration.name, "release")
        self.assertEqual(
            format_program(program),
            "namespace release;\n\n"
            "function ready(value) {\n"
            "    return value;\n"
            "}\n",
        )

    def test_namespace_remains_a_valid_contextual_function_name(self) -> None:
        program = parse(
            "function namespace(value) { return value; }\n"
            'mission "Context" { publish namespace(true); }\n'
        )
        compiled = compile_program(program)
        self.assertTrue(compiled.ok, compiled.diagnostics)

    def test_boolean_literal_namespace_name_is_rejected(self) -> None:
        with self.assertRaises(ParserError):
            parse("namespace true;\n")

    def test_namespace_must_be_first_statement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(
                root,
                "lib/gate.vectis",
                "function ready(value) { return value; }\n"
                "namespace gate;\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/gate.vectis";\n'
                'mission "Namespace" { publish gate.ready(true); }\n',
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn(
                "namespace declaration must be the first statement",
                str(caught.exception),
            )

    def test_duplicate_namespace_declarations_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(
                root,
                "lib/gate.vectis",
                "namespace gate;\n"
                "namespace second;\n"
                "function ready(value) { return value; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/gate.vectis";\n'
                'mission "Namespace" { publish true; }\n',
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn(
                "duplicate namespace declaration",
                str(caught.exception),
            )

    def test_unaliased_import_exposes_namespace_and_preserves_bare_call(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(
                root,
                "lib/gate.vectis",
                "namespace gate;\n"
                "function ready(value: number): boolean { return value >= 90; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/gate.vectis";\n'
                'mission "Namespace" {\n'
                '    publish {bare: ready(96), qualified: gate.ready(96)};\n'
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
                ["lib/gate.vectis::ready", "lib/gate.vectis::ready"],
            )
            result = Runtime(compiled.graph).execute()
            self.assertEqual(
                result.value_for("publish:0001"),
                {"bare": True, "qualified": True},
            )

    def test_namespace_declaration_does_not_create_self_qualifier(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            entry = self.write(
                root,
                "main.vectis",
                "namespace local;\n"
                "function ready(value) { return value; }\n"
                'mission "Namespace" { publish local.ready(true); }\n',
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn("unknown module qualifier", str(caught.exception))

    def test_declared_namespaces_disambiguate_colliding_functions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(
                root,
                "lib/release.vectis",
                "namespace release;\n"
                "function ready(value: number): boolean { return value >= 90; }\n",
            )
            self.write(
                root,
                "lib/security.vectis",
                "namespace security;\n"
                "function ready(value: number): boolean { return value >= 95; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/release.vectis";\n'
                'import "lib/security.vectis";\n'
                'mission "Namespace" {\n'
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

    def test_selective_import_restricts_declared_namespace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(
                root,
                "lib/gate.vectis",
                "namespace gate;\n"
                "function ready(value) { return value; }\n"
                "function score(value) { return value; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/gate.vectis" {ready};\n'
                'mission "Namespace" { publish gate.score(96); }\n',
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn(
                "not selected by module namespace",
                str(caught.exception),
            )

    def test_declared_namespace_cannot_access_private_function(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(
                root,
                "lib/gate.vectis",
                "namespace gate;\n"
                "private function helper(value) { return value; }\n"
                "function ready(value) { return helper(value); }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/gate.vectis";\n'
                'mission "Namespace" { publish gate.helper(true); }\n',
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn("is private to module", str(caught.exception))

    def test_declared_namespace_surface_is_direct_not_transitive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(
                root,
                "lib/inner.vectis",
                "function hidden(value) { return value; }\n",
            )
            self.write(
                root,
                "lib/outer.vectis",
                "namespace outer;\n"
                'import "inner.vectis";\n'
                "function visible(value) { return hidden(value); }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/outer.vectis";\n'
                'mission "Namespace" { publish outer.hidden(true); }\n',
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn(
                "is not declared by namespaced module",
                str(caught.exception),
            )

    def test_declared_namespace_does_not_propagate_transitively(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(
                root,
                "lib/inner.vectis",
                "namespace inner;\n"
                "function ready(value) { return value; }\n",
            )
            self.write(
                root,
                "lib/outer.vectis",
                'import "inner.vectis";\n'
                "function visible(value) { return inner.ready(value); }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/outer.vectis";\n'
                'mission "Namespace" { publish inner.ready(true); }\n',
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn("unknown module qualifier", str(caught.exception))

    def test_explicit_alias_overrides_declared_namespace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(
                root,
                "lib/release.vectis",
                "namespace release;\n"
                "function ready(value) { return value; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/release.vectis" as rel;\n'
                'mission "Namespace" { publish release.ready(true); }\n',
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn("unknown module qualifier", str(caught.exception))

            entry.write_text(
                'import "lib/release.vectis" as rel;\n'
                'mission "Namespace" { publish rel.ready(true); }\n',
                encoding="utf-8",
            )
            _loaded, compiled = self.compile_loaded(entry)
            self.assertTrue(compiled.ok, compiled.diagnostics)

    def test_duplicate_declared_namespace_qualifier_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(
                root,
                "lib/a.vectis",
                "namespace shared;\nfunction one(value) { return value; }\n",
            )
            self.write(
                root,
                "lib/b.vectis",
                "namespace shared;\nfunction two(value) { return value; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/a.vectis";\n'
                'import "lib/b.vectis";\n'
                'mission "Namespace" { publish true; }\n',
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn("duplicate module qualifier", str(caught.exception))

    def test_duplicate_unaliased_import_of_same_namespace_remains_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(
                root,
                "lib/gate.vectis",
                "namespace gate;\n"
                "function ready(value) { return value; }\n"
                "function score(value) { return value; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/gate.vectis" {ready};\n'
                'import "lib/gate.vectis" {score};\n'
                'mission "Namespace" { publish {a: gate.ready(true), b: gate.score(7)}; }\n',
            )
            _loaded, compiled = self.compile_loaded(entry)
            self.assertTrue(compiled.ok, compiled.diagnostics)
            result = Runtime(compiled.graph).execute()
            self.assertEqual(
                result.value_for("publish:0001"),
                {"a": True, "b": 7},
            )

    def test_explicit_alias_cannot_collide_with_declared_namespace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(
                root,
                "lib/a.vectis",
                "namespace shared;\nfunction one(value) { return value; }\n",
            )
            self.write(
                root,
                "lib/b.vectis",
                "function two(value) { return value; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/a.vectis";\n'
                'import "lib/b.vectis" as shared;\n'
                'mission "Namespace" { publish true; }\n',
            )
            with self.assertRaises(ModuleError) as caught:
                load_program_file(entry)
            self.assertIn("duplicate module qualifier", str(caught.exception))

    def test_namespace_does_not_replace_project_relative_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(
                root,
                "lib/gate.vectis",
                "namespace gate;\n"
                "function ready(value) { return value; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/gate.vectis";\n'
                'mission "Namespace" { publish gate.ready(true); }\n',
            )
            loaded = load_program_file(entry)
            targets = [
                identity.label
                for _span, identity in loaded.function_scope.calls
            ]
            self.assertEqual(targets, ["lib/gate.vectis::ready"])

    def test_namespace_identity_controls_type_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(
                root,
                "lib/gate.vectis",
                "namespace gate;\n"
                "function score(value: number): number { return value; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/gate.vectis";\n'
                'mission "Namespace" { publish gate.score("bad"); }\n',
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

    def test_top_level_namespace_is_semantic_and_compiler_noop(self) -> None:
        program = parse(
            "namespace local;\n"
            "function ready(value) { return value; }\n"
            'mission "Namespace" { publish ready(true); }\n'
        )
        compiled = compile_program(program)
        self.assertTrue(compiled.ok, compiled.diagnostics)
        result = Runtime(compiled.graph).execute()
        self.assertIs(result.value_for("publish:0001"), True)

    def test_nested_namespace_is_rejected_semantically(self) -> None:
        program = parse(
            'mission "Namespace" { namespace local; publish true; }\n'
        )
        compiled = compile_program(program)
        self.assertFalse(compiled.ok)
        self.assertTrue(
            any(
                "namespace declarations are only allowed at program top level"
                in item.message
                for item in compiled.diagnostics
            ),
            compiled.diagnostics,
        )

    def test_navigation_references_and_rename_use_namespace_qualified_member(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            library = self.write(
                root,
                "lib/gate.vectis",
                "namespace gate;\n"
                "function ready(value) { return value; }\n",
            )
            source = (
                'import "lib/gate.vectis";\n'
                'mission "Namespace" { publish gate.ready(true); }\n'
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

    def test_signature_help_uses_namespace_qualified_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(
                root,
                "lib/gate.vectis",
                "namespace gate;\n"
                "function ready(value: number, threshold: number): boolean {\n"
                "    return value >= threshold;\n"
                "}\n",
            )
            source = (
                'import "lib/gate.vectis";\n'
                'mission "Namespace" { publish gate.ready(96, 90); }\n'
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

    def test_semantic_tokens_mark_namespace_context_and_qualified_function(self) -> None:
        source = (
            "namespace gate;\n"
            'mission "Namespace" { publish gate.ready(true); }\n'
        )
        items = self.decoded_tokens(source)
        slices = [
            (source.splitlines()[line][start:start + length], kind, modifiers)
            for line, start, length, kind, modifiers in items
        ]
        self.assertIn(("namespace", "keyword", 0), slices)
        self.assertIn(("gate", "variable", 1), slices)
        self.assertIn(("ready", "function", 0), slices)

    def test_module_browser_exposes_namespace_without_executable_count(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            self.write(
                root,
                "lib/gate.vectis",
                "namespace gate;\n"
                "function ready(value) { return value; }\n",
            )
            payload = browse_project_modules(root)
            module = payload["modules"][0]
            self.assertEqual(module["namespace"], "gate")
            self.assertEqual(module["kind"], "library")
            self.assertTrue(module["importable"])
            self.assertEqual(module["executable_statement_count"], 0)
            self.assertNotIn(str(root.resolve()), repr(payload))

    def test_workspace_overlay_can_change_declared_namespace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.project(root)
            library = self.write(
                root,
                "lib/gate.vectis",
                "namespace saved;\n"
                "function ready(value) { return value; }\n",
            )
            source = (
                'import "lib/gate.vectis";\n'
                'mission "Namespace" { publish live.ready(true); }\n'
            )
            entry = self.write(root, "main.vectis", source)
            workspace = load_workspace_program(
                entry,
                overlays={
                    library.resolve(): (
                        "namespace live;\n"
                        "function ready(value) { return value; }\n"
                    )
                },
            )
            call_targets = [
                identity.label
                for _span, identity in workspace.function_scope.calls
            ]
            self.assertEqual(call_targets, ["lib/gate.vectis::ready"])


if __name__ == "__main__":
    unittest.main()
