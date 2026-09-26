# GHOST FIVE // VECTIS
# Regression coverage for deterministic multi-file module compilation.
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from vectis.compiler import compile_program
from vectis.formatter import format_program
from vectis.modules import (
    ModuleError,
    load_program_file,
    module_root_for,
)
from vectis.parser import ParserError, parse
from vectis.runtime import Runtime


class ModuleTests(unittest.TestCase):
    def project(self):
        return tempfile.TemporaryDirectory()

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

    def test_import_parses_and_formats(self):
        program = parse(
            'import "../lib/quality.vectis";\n'
            'mission "demo" { publish "ok"; }\n',
            file="missions/main.vectis",
        )
        formatted = format_program(program)
        self.assertIn(
            'import "../lib/quality.vectis";',
            formatted,
        )

    def test_project_root_uses_nearest_vectis_toml(self):
        with self.project() as temporary:
            root = Path(temporary)
            (root / "vectis.toml").write_text(
                "[project]\n",
                encoding="utf-8",
            )
            source = self.write(
                root,
                "missions/main.vectis",
                'mission "demo" {}\n',
            )
            self.assertEqual(
                module_root_for(source),
                root.resolve(),
            )

    def test_imported_pure_function_executes(self):
        with self.project() as temporary:
            root = Path(temporary)
            (root / "vectis.toml").write_text(
                "[project]\n",
                encoding="utf-8",
            )
            self.write(
                root,
                "lib/quality.vectis",
                '''
function release_ready(build) {
    return build.passed
        && build.coverage >= 90
        && all(build.checks);
}
''',
            )
            entry = self.write(
                root,
                "missions/main.vectis",
                '''
import "../lib/quality.vectis";

mission "Module gate" {
    source build {
        passed: true,
        coverage: 96,
        checks: [true, true, true]
    };
    let ready release_ready(build);
    assert ready, "Imported release gate failed";
    publish {status: if_else(ready, "GO", "HOLD")};
}
''',
            )

            loaded = load_program_file(entry)
            compiled = compile_program(loaded.program)

            self.assertTrue(compiled.ok)
            result = Runtime(compiled.graph).execute()
            self.assertTrue(result.success)
            self.assertEqual(
                result.value_for("publish:0001"),
                {"status": "GO"},
            )
            self.assertEqual(
                tuple(
                    path.relative_to(root.resolve()).as_posix()
                    for path in loaded.modules
                ),
                (
                    "lib/quality.vectis",
                    "missions/main.vectis",
                ),
            )

    def test_transitive_imports_are_deterministic(self):
        with self.project() as temporary:
            root = Path(temporary)
            (root / "vectis.toml").write_text(
                "[project]\n",
                encoding="utf-8",
            )
            self.write(
                root,
                "lib/math.vectis",
                '''
function at_least(value, minimum) {
    return value >= minimum;
}
''',
            )
            self.write(
                root,
                "lib/quality.vectis",
                '''
import "math.vectis";

function quality_ready(score) {
    return at_least(score, 90);
}
''',
            )
            entry = self.write(
                root,
                "missions/main.vectis",
                '''
import "../lib/quality.vectis";

mission "Transitive" {
    source score 96;
    publish quality_ready(score);
}
''',
            )

            first = load_program_file(entry)
            second = load_program_file(entry)

            self.assertEqual(first.program, second.program)
            self.assertEqual(first.modules, second.modules)

            compiled = compile_program(first.program)
            self.assertTrue(compiled.ok)
            result = Runtime(compiled.graph).execute()
            self.assertTrue(result.success)
            self.assertTrue(
                result.value_for("publish:0001")
            )

    def test_duplicate_import_is_loaded_once(self):
        with self.project() as temporary:
            root = Path(temporary)
            (root / "vectis.toml").write_text(
                "[project]\n",
                encoding="utf-8",
            )
            self.write(
                root,
                "lib/shared.vectis",
                '''
function shared(value) {
    return value;
}
''',
            )
            entry = self.write(
                root,
                "main.vectis",
                '''
import "lib/shared.vectis";
import "lib/shared.vectis";
mission "demo" { publish shared(true); }
''',
            )

            loaded = load_program_file(entry)
            names = [
                statement.name
                for statement in loaded.program.statements
                if hasattr(statement, "name")
            ]
            self.assertEqual(
                names.count("shared"),
                1,
            )

    def test_import_cycle_is_rejected(self):
        with self.project() as temporary:
            root = Path(temporary)
            (root / "vectis.toml").write_text(
                "[project]\n",
                encoding="utf-8",
            )
            a = self.write(
                root,
                "a.vectis",
                'import "b.vectis";\n'
                'function a(value) { return value; }\n',
            )
            self.write(
                root,
                "b.vectis",
                'import "a.vectis";\n'
                'function b(value) { return value; }\n',
            )

            with self.assertRaisesRegex(
                ModuleError,
                "import cycle",
            ):
                load_program_file(a)

    def test_import_cannot_escape_project_root(self):
        with self.project() as temporary:
            parent = Path(temporary)
            root = parent / "project"
            root.mkdir()
            (root / "vectis.toml").write_text(
                "[project]\n",
                encoding="utf-8",
            )
            self.write(
                parent,
                "outside.vectis",
                'function outside(value) { return value; }\n',
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "../outside.vectis";\n'
                'mission "demo" {}\n',
            )

            with self.assertRaisesRegex(
                ModuleError,
                "escapes the owning project root",
            ):
                load_program_file(entry)

    def test_imported_module_cannot_execute_missions(self):
        with self.project() as temporary:
            root = Path(temporary)
            (root / "vectis.toml").write_text(
                "[project]\n",
                encoding="utf-8",
            )
            self.write(
                root,
                "lib/bad.vectis",
                'mission "hidden" { publish "no"; }\n',
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/bad.vectis";\n'
                'mission "demo" {}\n',
            )

            with self.assertRaisesRegex(
                ModuleError,
                "pure function declarations",
            ):
                load_program_file(entry)

    def test_missing_module_fails_closed(self):
        with self.project() as temporary:
            root = Path(temporary)
            (root / "vectis.toml").write_text(
                "[project]\n",
                encoding="utf-8",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/missing.vectis";\n'
                'mission "demo" {}\n',
            )

            with self.assertRaisesRegex(
                ModuleError,
                "does not exist",
            ):
                load_program_file(entry)

    def test_import_requires_vectis_extension(self):
        with self.project() as temporary:
            root = Path(temporary)
            (root / "vectis.toml").write_text(
                "[project]\n",
                encoding="utf-8",
            )
            self.write(
                root,
                "lib/functions.txt",
                "not a module",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/functions.txt";\n'
                'mission "demo" {}\n',
            )

            with self.assertRaisesRegex(
                ModuleError,
                ".vectis",
            ):
                load_program_file(entry)


class ModuleFunctionVisibilityTests(unittest.TestCase):
    def write(self, root: Path, relative: str, content: str) -> Path:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_private_function_parses_and_formats_contextually(self) -> None:
        program = parse(
            "private function helper(value: number): number {\n"
            "    return value;\n"
            "}\n"
        )
        function = program.statements[0]
        self.assertEqual(function.visibility, "private")
        formatted = format_program(program)
        self.assertIn("private function helper", formatted)
        self.assertEqual(format_program(parse(formatted)), formatted)

    def test_bare_function_remains_public(self) -> None:
        program = parse("function helper(value) { return value; }\n")
        self.assertEqual(program.statements[0].visibility, "public")

    def test_private_identifier_remains_valid_function_name(self) -> None:
        program = parse("function private(value) { return value; }\n")
        self.assertEqual(program.statements[0].name, "private")
        self.assertEqual(program.statements[0].visibility, "public")

    def test_imported_public_function_can_use_private_helper(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "vectis.toml").write_text("[project]\n", encoding="utf-8")
            self.write(
                root,
                "lib/gate.vectis",
                "private function threshold(value: number): boolean {\n"
                "    return value >= 90;\n"
                "}\n"
                "function ready(value: number): boolean {\n"
                "    return threshold(value);\n"
                "}\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/gate.vectis";\n'
                'mission "ok" { publish ready(96); }\n',
            )
            loaded = load_program_file(entry)
            compiled = compile_program(loaded.program)
            self.assertTrue(compiled.ok, compiled.diagnostics)
            result = Runtime(compiled.graph).execute()
            self.assertTrue(result.success)
            self.assertIs(result.value_for("publish:0001"), True)

    def test_entry_cannot_call_imported_private_function(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "vectis.toml").write_text("[project]\n", encoding="utf-8")
            self.write(
                root,
                "lib/gate.vectis",
                "private function threshold(value) { return value; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/gate.vectis";\n'
                'mission "bad" { publish threshold(true); }\n',
            )
            with self.assertRaisesRegex(
                ModuleError,
                "private to module lib/gate.vectis",
            ):
                load_program_file(entry)

    def test_imported_module_cannot_call_another_modules_private_function(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "vectis.toml").write_text("[project]\n", encoding="utf-8")
            self.write(
                root,
                "lib/base.vectis",
                "private function secret(value) { return value; }\n",
            )
            self.write(
                root,
                "lib/api.vectis",
                'import "base.vectis";\n'
                "function exposed(value) { return secret(value); }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/api.vectis";\n'
                'mission "bad" { publish exposed(true); }\n',
            )
            with self.assertRaisesRegex(ModuleError, "private to module"):
                load_program_file(entry)


class SelectiveImportTests(unittest.TestCase):
    def write(self, root: Path, relative: str, content: str) -> Path:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_selective_import_parses_and_formats(self) -> None:
        program = parse(
            'import "lib/gate.vectis" {ready, score};\n'
        )
        statement = program.statements[0]
        self.assertEqual(statement.names, ("ready", "score"))
        formatted = format_program(program)
        self.assertEqual(
            formatted,
            'import "lib/gate.vectis" {ready, score};\n',
        )
        self.assertEqual(format_program(parse(formatted)), formatted)

    def test_bare_import_keeps_all_names(self) -> None:
        statement = parse('import "lib/gate.vectis";\n').statements[0]
        self.assertIsNone(statement.names)

    def test_duplicate_selector_is_rejected(self) -> None:
        with self.assertRaisesRegex(ParserError, "duplicate imported"):
            parse('import "lib/gate.vectis" {ready, ready};\n')

    def test_selected_public_function_executes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "vectis.toml").write_text("[project]\n", encoding="utf-8")
            self.write(
                root,
                "lib/gate.vectis",
                "function ready(value) { return value >= 90; }\n"
                "function score(value) { return value; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/gate.vectis" {ready};\n'
                'mission "ok" { publish ready(96); }\n',
            )
            loaded = load_program_file(entry)
            compiled = compile_program(loaded.program)
            self.assertTrue(compiled.ok, compiled.diagnostics)
            result = Runtime(compiled.graph).execute()
            self.assertTrue(result.success)
            self.assertIs(result.value_for("publish:0001"), True)

    def test_unselected_public_function_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "vectis.toml").write_text("[project]\n", encoding="utf-8")
            self.write(
                root,
                "lib/gate.vectis",
                "function ready(value) { return value; }\n"
                "function score(value) { return value; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/gate.vectis" {ready};\n'
                'mission "bad" { publish score(96); }\n',
            )
            with self.assertRaisesRegex(
                ModuleError,
                "not selected by imports in module main.vectis",
            ):
                load_program_file(entry)

    def test_unknown_selector_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "vectis.toml").write_text("[project]\n", encoding="utf-8")
            self.write(
                root,
                "lib/gate.vectis",
                "function ready(value) { return value; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/gate.vectis" {missing};\n'
                'mission "bad" { publish true; }\n',
            )
            with self.assertRaisesRegex(
                ModuleError,
                "not declared by module lib/gate.vectis",
            ):
                load_program_file(entry)

    def test_private_selector_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "vectis.toml").write_text("[project]\n", encoding="utf-8")
            self.write(
                root,
                "lib/gate.vectis",
                "private function helper(value) { return value; }\n"
                "function ready(value) { return helper(value); }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/gate.vectis" {helper};\n'
                'mission "bad" { publish true; }\n',
            )
            with self.assertRaisesRegex(
                ModuleError,
                "private to module lib/gate.vectis",
            ):
                load_program_file(entry)

    def test_selected_function_keeps_internal_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "vectis.toml").write_text("[project]\n", encoding="utf-8")
            self.write(
                root,
                "lib/base.vectis",
                "function floor_score(value) { return value; }\n",
            )
            self.write(
                root,
                "lib/gate.vectis",
                'import "base.vectis";\n'
                "private function threshold(value) {\n"
                "    return floor_score(value) >= 90;\n"
                "}\n"
                "function ready(value) { return threshold(value); }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/gate.vectis" {ready};\n'
                'mission "ok" { publish ready(96); }\n',
            )
            loaded = load_program_file(entry)
            compiled = compile_program(loaded.program)
            self.assertTrue(compiled.ok, compiled.diagnostics)
            result = Runtime(compiled.graph).execute()
            self.assertTrue(result.success)
            self.assertIs(result.value_for("publish:0001"), True)

    def test_bare_import_preserves_transitive_public_access(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "vectis.toml").write_text("[project]\n", encoding="utf-8")
            self.write(
                root,
                "lib/base.vectis",
                "function shared(value) { return value; }\n",
            )
            self.write(
                root,
                "lib/gate.vectis",
                'import "base.vectis";\n'
                "function ready(value) { return value; }\n",
            )
            entry = self.write(
                root,
                "main.vectis",
                'import "lib/gate.vectis";\n'
                'mission "compat" { publish shared(96); }\n',
            )
            loaded = load_program_file(entry)
            compiled = compile_program(loaded.program)
            self.assertTrue(compiled.ok, compiled.diagnostics)

if __name__ == "__main__":
    unittest.main()
