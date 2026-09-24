# GHOST FIVE // VECTIS
# Regression coverage for RFC 0019 typed list element contracts.
from __future__ import annotations

import unittest

from vectis.compiler import compile_program
from vectis.formatter import format_program
from vectis.parser import parse
from vectis.runtime import Runtime
from vectis.type_contracts import parse_type_contract


class TypedListContractTests(unittest.TestCase):
    def compile(self, source: str):
        program = parse(source, file="<typed-list-test>")
        return program, compile_program(program)

    def test_type_contract_parser_is_recursive_and_canonical(self) -> None:
        contract = parse_type_contract("list[list[number]]")
        self.assertIsNotNone(contract)
        self.assertEqual(contract.render(), "list[list[number]]")
        self.assertIsNone(parse_type_contract("number[string]"))
        self.assertIsNone(parse_type_contract("list[percentage]"))

    def test_parser_and_formatter_preserve_typed_list_contract(self) -> None:
        source = """
function first_score(scores: list[number]): number {
    return scores[0];
}
"""
        program = parse(source)
        function = program.statements[0]
        self.assertEqual(function.parameter_types, ("list[number]",))
        self.assertEqual(function.return_type, "number")
        formatted = format_program(program)
        self.assertIn(
            "function first_score(scores: list[number]): number {",
            formatted,
        )
        self.assertEqual(format_program(parse(formatted)), formatted)

    def test_list_literal_argument_mismatch_is_rejected(self) -> None:
        _program, compiled = self.compile(
            """
function total(values: list[number]): number {
    return values[0];
}
mission "bad" {
    publish total([96, "wrong"]);
}
"""
        )
        self.assertFalse(compiled.ok)
        self.assertTrue(
            any(
                "Argument 1 to total()[1] must be number, not string"
                in item.message
                for item in compiled.diagnostics
            )
        )

    def test_typed_list_parameter_index_produces_item_type(self) -> None:
        _program, compiled = self.compile(
            """
function first(values: list[number]): number {
    return values[0];
}
mission "ok" {
    publish first([96, 92]);
}
"""
        )
        self.assertTrue(compiled.ok, compiled.diagnostics)
        result = Runtime(compiled.graph).execute()
        self.assertTrue(result.success)
        self.assertEqual(result.value_for("publish:0001"), 96)

    def test_typed_list_result_rejects_wrong_literal_item(self) -> None:
        _program, compiled = self.compile(
            """
function scores(): list[number] {
    return [96, "wrong"];
}
mission "bad" {
    publish scores();
}
"""
        )
        self.assertFalse(compiled.ok)
        self.assertTrue(
            any(
                "Function scores() return value[1] must be number, not string"
                in item.message
                for item in compiled.diagnostics
            )
        )

    def test_declaration_contract_propagates_through_indexing(self) -> None:
        _program, compiled = self.compile(
            """
function label(value: string): string {
    return upper(value);
}
mission "bad" {
    source scores [96, 92];
    let first scores[0];
    publish label(first);
}
"""
        )
        self.assertFalse(compiled.ok)
        self.assertTrue(
            any(
                "Argument 1 to label() must be string, not number"
                in item.message
                for item in compiled.diagnostics
            )
        )

    def test_nested_list_contracts_validate_recursively(self) -> None:
        _program, compiled = self.compile(
            """
function matrix(values: list[list[number]]): list[number] {
    return values[0];
}
mission "bad" {
    publish matrix([[1, 2], [3, "wrong"]]);
}
"""
        )
        self.assertFalse(compiled.ok)
        self.assertTrue(
            any(
                "Argument 1 to matrix()[1][1] must be number, not string"
                in item.message
                for item in compiled.diagnostics
            )
        )

    def test_list_builtin_argument_mismatch_is_rejected(self) -> None:
        _program, compiled = self.compile(
            """
function total(values: list[number]): number {
    return values[0];
}
mission "bad" {
    publish total(list(96, "wrong"));
}
"""
        )
        self.assertFalse(compiled.ok)
        self.assertTrue(
            any(
                "Argument 1 to total()[1] must be number, not string"
                in item.message
                for item in compiled.diagnostics
            )
        )

    def test_plain_list_and_list_any_remain_broad_contracts(self) -> None:
        _program, compiled = self.compile(
            """
function broad(values: list): list {
    return values;
}
function explicit(values: list[any]): list[any] {
    return values;
}
mission "ok" {
    publish broad([1, "two", true]);
    publish explicit([1, "two", true]);
}
"""
        )
        self.assertTrue(compiled.ok, compiled.diagnostics)

    def test_non_list_generic_shape_is_rejected_semantically(self) -> None:
        _program, compiled = self.compile(
            """
function invalid(value: number[string]): number {
    return 1;
}
mission "bad" { publish invalid(1); }
"""
        )
        self.assertFalse(compiled.ok)
        self.assertTrue(
            any(
                "Unknown function type 'number[string]'" in item.message
                for item in compiled.diagnostics
            )
        )


if __name__ == "__main__":
    unittest.main()
