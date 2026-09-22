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
from vectis.parser import parse
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
                "escapes the module root",
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


if __name__ == "__main__":
    unittest.main()
