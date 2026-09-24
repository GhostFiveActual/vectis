# GHOST FIVE // VECTIS
# Regression coverage for RFC 0018 typed pure-function signatures.
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from vectis.ast import FunctionDeclaration
from vectis.compiler import compile_program
from vectis.formatter import format_program
from vectis.modules import load_program_file
from vectis.parser import parse
from vectis.runtime import Runtime


class TypedPureFunctionTests(unittest.TestCase):
    def compile(self, source: str):
        program = parse(source, file="<typed-function-test>")
        return program, compile_program(program)

    def test_parser_and_formatter_preserve_typed_contract(self) -> None:
        source = """
function release_ready(
    score: number,
    risk: number
): boolean {
    return score >= 90 && risk <= 25;
}
"""
        program = parse(source)
        function = program.statements[0]
        self.assertIsInstance(function, FunctionDeclaration)
        self.assertEqual(function.parameters, ("score", "risk"))
        self.assertEqual(function.parameter_types, ("number", "number"))
        self.assertEqual(function.return_type, "boolean")

        formatted = format_program(program)
        self.assertIn(
            "function release_ready(score: number, risk: number): boolean {",
            formatted,
        )
        self.assertEqual(format_program(parse(formatted)), formatted)

    def test_partial_annotations_preserve_untyped_compatibility(self) -> None:
        program = parse(
            """
function threshold(value, minimum: number): boolean {
    return value >= minimum;
}

function identity(value) {
    return value;
}
"""
        )
        threshold = program.statements[0]
        identity = program.statements[1]
        self.assertEqual(threshold.parameter_types, (None, "number"))
        self.assertEqual(threshold.return_type, "boolean")
        self.assertEqual(identity.parameter_types, ())
        self.assertIsNone(identity.return_type)

    def test_typed_argument_mismatch_is_rejected(self) -> None:
        _program, compiled = self.compile(
            """
function gate(score: number): boolean {
    return score >= 90;
}

mission "bad" {
    publish gate("ninety");
}
"""
        )
        self.assertFalse(compiled.ok)
        self.assertTrue(
            any(
                "Argument 1 to gate() must be number, not string"
                in diagnostic.message
                for diagnostic in compiled.diagnostics
            )
        )

    def test_declared_result_mismatch_is_rejected(self) -> None:
        _program, compiled = self.compile(
            """
function label(value: string): boolean {
    return upper(value);
}

mission "bad" {
    publish label("vectis");
}
"""
        )
        self.assertFalse(compiled.ok)
        self.assertTrue(
            any(
                "declares return type boolean but body evaluates to string"
                in diagnostic.message
                for diagnostic in compiled.diagnostics
            )
        )

    def test_declared_result_type_participates_in_call_semantics(self) -> None:
        _program, compiled = self.compile(
            """
function label(value: any): string {
    return upper(string(value));
}

mission "bad" {
    when label(7) {
        publish "invalid";
    }
}
"""
        )
        self.assertFalse(compiled.ok)
        self.assertTrue(
            any(
                "when condition must evaluate to boolean"
                in diagnostic.message
                for diagnostic in compiled.diagnostics
            )
        )

    def test_any_accepts_known_argument_types(self) -> None:
        _program, compiled = self.compile(
            """
function identity(value: any): any {
    return value;
}

mission "ok" {
    publish identity({ready: true});
}
"""
        )
        self.assertTrue(compiled.ok, compiled.diagnostics)
        result = Runtime(compiled.graph).execute()
        self.assertTrue(result.success)
        self.assertEqual(result.value_for("publish:0001"), {"ready": True})

    def test_unknown_annotation_name_fails_semantics(self) -> None:
        _program, compiled = self.compile(
            """
function gate(score: percentage): boolean {
    return score >= 90;
}

mission "bad" {
    publish gate(96);
}
"""
        )
        self.assertFalse(compiled.ok)
        self.assertTrue(
            any(
                "Unknown function type 'percentage'" in diagnostic.message
                for diagnostic in compiled.diagnostics
            )
        )

    def test_imported_typed_function_executes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "vectis.toml").write_text(
                "[project]\n",
                encoding="utf-8",
            )
            library = root / "lib" / "gate.vectis"
            library.parent.mkdir(parents=True)
            library.write_text(
                "function gate(score: number): boolean {\n"
                "    return score >= 90;\n"
                "}\n",
                encoding="utf-8",
            )
            entry = root / "main.vectis"
            entry.write_text(
                'import "lib/gate.vectis";\n'
                'mission "typed" { publish gate(96); }\n',
                encoding="utf-8",
            )

            loaded = load_program_file(entry)
            compiled = compile_program(loaded.program)
            self.assertTrue(compiled.ok, compiled.diagnostics)
            result = Runtime(compiled.graph).execute()
            self.assertTrue(result.success)
            self.assertIs(result.value_for("publish:0001"), True)


if __name__ == "__main__":
    unittest.main()
