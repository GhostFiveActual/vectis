# GHOST FIVE // VECTIS
# Regression coverage for RFC 0021 deterministic built-in result contracts.
from __future__ import annotations

import unittest

from vectis.compiler import compile_program
from vectis.parser import parse
from vectis.runtime import Runtime
from vectis.type_contracts import (
    TypeContract,
    common_type_contract,
    parse_type_contract,
)


class ResultContractInferenceTests(unittest.TestCase):
    def compile(self, source: str):
        return compile_program(parse(source, file="<result-contract-test>"))

    def test_common_contract_preserves_shared_object_fields(self) -> None:
        first = parse_type_contract(
            "object{name:string,score:number}"
        )
        second = parse_type_contract(
            "object{name:string,risk:number}"
        )
        common = common_type_contract((first, second))
        self.assertIsNotNone(common)
        self.assertEqual(common.render(), "object{name:string}")

    def test_common_contract_preserves_nested_list_item_shape(self) -> None:
        first = parse_type_contract(
            "list[object{name:string,score:number}]"
        )
        second = parse_type_contract(
            "list[object{name:string,risk:number}]"
        )
        common = common_type_contract((first, second))
        self.assertIsNotNone(common)
        self.assertEqual(common.render(), "list[object{name:string}]")

    def test_common_contract_rejects_incompatible_top_level_types(self) -> None:
        self.assertIsNone(
            common_type_contract(
                (TypeContract("number"), TypeContract("string"))
            )
        )

    def test_if_else_common_result_catches_declared_mismatch(self) -> None:
        compiled = self.compile(
            """
function choose(flag: boolean): string {
    return if_else(flag, 96, 92);
}
mission "bad" { publish choose(true); }
"""
        )
        self.assertFalse(compiled.ok)
        self.assertTrue(
            any(
                "declares return type string but body evaluates to number"
                in item.message
                for item in compiled.diagnostics
            )
        )

    def test_if_else_literal_condition_uses_selected_contract(self) -> None:
        compiled = self.compile(
            """
function choose(): number {
    return if_else(true, 96, "fallback");
}
mission "ok" { publish choose(); }
"""
        )
        self.assertTrue(compiled.ok, compiled.diagnostics)
        result = Runtime(compiled.graph).execute()
        self.assertEqual(result.value_for("publish:0001"), 96)

    def test_if_else_object_join_preserves_guaranteed_field(self) -> None:
        compiled = self.compile(
            """
function name(flag: boolean): string {
    return if_else(
        flag,
        {name: "release", score: 96},
        {name: "fallback", risk: 12}
    ).name;
}
mission "ok" { publish name(true); }
"""
        )
        self.assertTrue(compiled.ok, compiled.diagnostics)

    def test_if_else_mixed_types_remain_permissive_unknown(self) -> None:
        compiled = self.compile(
            """
function uncertain(flag: boolean): number {
    return if_else(flag, 96, "fallback");
}
mission "ok" { publish uncertain(true); }
"""
        )
        self.assertTrue(compiled.ok, compiled.diagnostics)

    def test_coalesce_common_result_catches_declared_mismatch(self) -> None:
        compiled = self.compile(
            """
function choose(): boolean {
    return coalesce(96, 92);
}
mission "bad" { publish choose(); }
"""
        )
        self.assertFalse(compiled.ok)
        self.assertTrue(
            any(
                "declares return type boolean but body evaluates to number"
                in item.message
                for item in compiled.diagnostics
            )
        )

    def test_object_constructor_projects_static_shape(self) -> None:
        compiled = self.compile(
            """
function requires_text(value: string): string {
    return value;
}
mission "bad" {
    let legacy object("name", "release", "score", 96);
    publish requires_text(legacy.score);
}
"""
        )
        self.assertFalse(compiled.ok)
        self.assertTrue(
            any(
                "Argument 1 to requires_text() must be string, not number"
                in item.message
                for item in compiled.diagnostics
            )
        )

    def test_get_typed_list_projects_item_contract(self) -> None:
        compiled = self.compile(
            """
function requires_text(value: string): string {
    return value;
}
mission "bad" {
    let scores [96, 92];
    publish requires_text(get(scores, 0));
}
"""
        )
        self.assertFalse(compiled.ok)
        self.assertTrue(
            any(
                "Argument 1 to requires_text() must be string, not number"
                in item.message
                for item in compiled.diagnostics
            )
        )

    def test_get_typed_list_default_joins_result_contract(self) -> None:
        compiled = self.compile(
            """
function requires_number(value: number): number {
    return value;
}
mission "ok" {
    let scores [96, 92];
    publish requires_number(get(scores, 7, 0));
}
"""
        )
        self.assertTrue(compiled.ok, compiled.diagnostics)

    def test_list_literal_joins_object_item_shapes(self) -> None:
        compiled = self.compile(
            """
function requires_text(value: string): string {
    return value;
}
mission "ok" {
    let rows [
        {name: "release", score: 96},
        {name: "fallback", risk: 12}
    ];
    publish requires_text(rows[0].name);
}
"""
        )
        self.assertTrue(compiled.ok, compiled.diagnostics)


if __name__ == "__main__":
    unittest.main()
