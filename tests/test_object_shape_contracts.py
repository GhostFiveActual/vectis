# GHOST FIVE // VECTIS
# Regression coverage for RFC 0020 typed object shape contracts.
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from vectis.compiler import compile_program
from vectis.formatter import format_program
from vectis.lsp_workspace import load_workspace_program
from vectis.parser import parse
from vectis.runtime import Runtime
from vectis.type_contracts import parse_type_contract


class TypedObjectShapeContractTests(unittest.TestCase):
    def compile(self, source: str):
        program = parse(source, file="<typed-object-test>")
        return program, compile_program(program)

    def test_type_contract_parser_supports_nested_object_shapes(self) -> None:
        contract = parse_type_contract(
            "object{name:string,metrics:object{scores:list[number]}}"
        )
        self.assertIsNotNone(contract)
        self.assertEqual(
            contract.render(),
            "object{name:string,metrics:object{scores:list[number]}}",
        )
        self.assertEqual(contract.field("name").render(), "string")
        self.assertIsNone(parse_type_contract("list{score:number}"))
        self.assertIsNone(parse_type_contract("object{}"))
        self.assertIsNone(
            parse_type_contract("object{name:string,name:number}")
        )

    def test_parser_and_formatter_preserve_object_shape_contract(self) -> None:
        source = """
function label(value: object{name:string,score:number}): string {
    return value.name;
}
"""
        program = parse(source)
        function = program.statements[0]
        self.assertEqual(
            function.parameter_types,
            ("object{name:string,score:number}",),
        )
        self.assertEqual(function.return_type, "string")
        formatted = format_program(program)
        self.assertIn(
            "function label(value: object{name:string,score:number}): string {",
            formatted,
        )
        self.assertEqual(format_program(parse(formatted)), formatted)

    def test_object_literal_argument_field_mismatch_is_rejected(self) -> None:
        _program, compiled = self.compile(
            """
function ready(value: object{name:string,score:number}): boolean {
    return value.score >= 90;
}
mission "bad" {
    publish ready({name: "release", score: "wrong"});
}
"""
        )
        self.assertFalse(compiled.ok)
        self.assertTrue(
            any(
                "Argument 1 to ready().score must be number, not string"
                in item.message
                for item in compiled.diagnostics
            )
        )

    def test_object_literal_missing_required_field_is_rejected(self) -> None:
        _program, compiled = self.compile(
            """
function ready(value: object{name:string,score:number}): boolean {
    return value.score >= 90;
}
mission "bad" {
    publish ready({name: "release"});
}
"""
        )
        self.assertFalse(compiled.ok)
        self.assertTrue(
            any(
                "Argument 1 to ready() requires field 'score'"
                in item.message
                for item in compiled.diagnostics
            )
        )

    def test_extra_object_fields_are_structurally_compatible(self) -> None:
        _program, compiled = self.compile(
            """
function label(value: object{name:string}): string {
    return value.name;
}
mission "ok" {
    publish label({name: "release", score: 96});
}
"""
        )
        self.assertTrue(compiled.ok, compiled.diagnostics)
        result = Runtime(compiled.graph).execute()
        self.assertTrue(result.success)
        self.assertEqual(result.value_for("publish:0001"), "release")

    def test_member_access_propagates_field_contract(self) -> None:
        _program, compiled = self.compile(
            """
function score(value: object{name:string,score:number}): number {
    return value.score;
}
mission "ok" {
    publish score({name: "release", score: 96});
}
"""
        )
        self.assertTrue(compiled.ok, compiled.diagnostics)
        result = Runtime(compiled.graph).execute()
        self.assertEqual(result.value_for("publish:0001"), 96)

    def test_string_index_access_propagates_field_contract(self) -> None:
        _program, compiled = self.compile(
            """
function score(value: object{name:string,score:number}): number {
    return value["score"];
}
mission "ok" {
    publish score({name: "release", score: 96});
}
"""
        )
        self.assertTrue(compiled.ok, compiled.diagnostics)

    def test_missing_member_is_rejected_when_shape_is_known(self) -> None:
        _program, compiled = self.compile(
            """
function invalid(value: object{name:string}): string {
    return value.missing;
}
mission "bad" { publish invalid({name: "release"}); }
"""
        )
        self.assertFalse(compiled.ok)
        self.assertTrue(
            any(
                "Object contract has no field 'missing'" in item.message
                for item in compiled.diagnostics
            )
        )

    def test_object_result_validates_nested_structures(self) -> None:
        _program, compiled = self.compile(
            """
function release(): object{name:string,scores:list[number]} {
    return {name: "release", scores: [96, "wrong"]};
}
mission "bad" { publish release(); }
"""
        )
        self.assertFalse(compiled.ok)
        self.assertTrue(
            any(
                "Function release() return value.scores[1] must be number, not string"
                in item.message
                for item in compiled.diagnostics
            )
        )

    def test_nested_object_shapes_validate_recursively(self) -> None:
        _program, compiled = self.compile(
            """
function first(value: object{metrics:object{scores:list[number]}}): number {
    return value.metrics.scores[0];
}
mission "bad" {
    publish first({metrics: {scores: [96, "wrong"]}});
}
"""
        )
        self.assertFalse(compiled.ok)
        self.assertTrue(
            any(
                "Argument 1 to first().metrics.scores[1] must be number, not string"
                in item.message
                for item in compiled.diagnostics
            )
        )

    def test_plain_object_return_type_does_not_consume_function_body(self) -> None:
        source = """
function identity(value: object): object {
    return value;
}
mission "ok" {
    publish identity({name: "release"});
}
"""
        program = parse(source)
        function = program.statements[0]
        self.assertEqual(function.parameter_types, ("object",))
        self.assertEqual(function.return_type, "object")
        compiled = compile_program(program)
        self.assertTrue(compiled.ok, compiled.diagnostics)

    def test_get_missing_field_is_rejected_when_shape_is_known(self) -> None:
        _program, compiled = self.compile(
            """
function invalid(value: object{name:string}): string {
    return get(value, "missing");
}
mission "bad" { publish invalid({name: "release"}); }
"""
        )
        self.assertFalse(compiled.ok)
        self.assertTrue(
            any(
                "Object contract has no field 'missing'" in item.message
                for item in compiled.diagnostics
            )
        )

    def test_imported_object_shape_function_compiles(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            library = root / "lib.vectis"
            entry = root / "main.vectis"
            library.write_text(
                "function score(value: object{name:string,score:number}): number {\n"
                "    return value.score;\n"
                "}\n",
                encoding="utf-8",
            )
            entry.write_text(
                'import "lib.vectis";\n'
                'mission "ok" { publish score({name: "release", score: 96}); }\n',
                encoding="utf-8",
            )
            workspace = load_workspace_program(entry)
            compiled = compile_program(workspace.program)
            self.assertTrue(compiled.ok, compiled.diagnostics)


if __name__ == "__main__":
    unittest.main()
