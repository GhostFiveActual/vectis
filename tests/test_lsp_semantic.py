\
# GHOST FIVE // VECTIS
# Verifies deterministic full-document semantic tokens for VECTIS.
from __future__ import annotations

import unittest

from vectis.lsp import LanguageServer
from vectis.lsp_semantic import (
    SEMANTIC_TOKEN_LEGEND,
    SEMANTIC_TOKEN_TYPES,
    semantic_tokens,
)


def _decoded(
    source: str,
    result: dict[str, object],
) -> list[tuple[int, int, int, str, int]]:
    data = result["data"]
    items = []
    line = 0
    start = 0

    for index in range(
        0,
        len(data),
        5,
    ):
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
                SEMANTIC_TOKEN_TYPES[
                    token_type
                ],
                modifiers,
            )
        )

    return items


class LspSemanticTokenTests(
    unittest.TestCase
):
    def test_legend_is_stable(self) -> None:
        self.assertEqual(
            SEMANTIC_TOKEN_LEGEND,
            {
                "tokenTypes": [
                    "keyword",
                    "string",
                    "number",
                    "operator",
                    "function",
                    "parameter",
                    "variable",
                    "property",
                ],
                "tokenModifiers": [
                    "declaration"
                ],
            },
        )

    def test_semantic_classes_cover_language_roles(
        self,
    ) -> None:
        source = (
            "function ready(value, threshold) {\n"
            "    return value >= threshold;\n"
            "}\n"
            'mission "Semantic" {\n'
            "    source quality 96;\n"
            "    let passed ready(quality, 90);\n"
            '    let label concat("Q", quality);\n'
            "    let item {name: label};\n"
            "    publish item.name;\n"
            "}\n"
        )
        result = semantic_tokens(
            source
        )
        items = _decoded(
            source,
            result,
        )

        self.assertIn(
            (0, 0, 8, "keyword", 0),
            items,
        )
        self.assertIn(
            (0, 9, 5, "function", 1),
            items,
        )
        self.assertIn(
            (0, 15, 5, "parameter", 1),
            items,
        )
        self.assertIn(
            (1, 11, 5, "parameter", 0),
            items,
        )
        self.assertIn(
            (1, 17, 2, "operator", 0),
            items,
        )
        self.assertIn(
            (4, 11, 7, "variable", 1),
            items,
        )
        self.assertIn(
            (5, 15, 5, "function", 0),
            items,
        )
        self.assertIn(
            (6, 14, 6, "function", 0),
            items,
        )
        self.assertIn(
            (7, 14, 4, "property", 1),
            items,
        )
        self.assertIn(
            (8, 17, 4, "property", 0),
            items,
        )

    def test_typed_function_preserves_parameter_semantics(
        self,
    ) -> None:
        source = (
            "function ready(value: number): boolean {\n"
            "    return value >= 90;\n"
            "}\n"
        )
        items = _decoded(source, semantic_tokens(source))

        self.assertIn((0, 15, 5, "parameter", 1), items)
        self.assertIn((0, 22, 6, "keyword", 0), items)
        self.assertIn((0, 31, 7, "keyword", 0), items)
        self.assertIn((1, 11, 5, "parameter", 0), items)

    def test_typed_list_contract_marks_nested_types_as_keywords(self) -> None:
        source = (
            "function first(values: list[number]): number {\n"
            "    return values[0];\n"
            "}\n"
        )
        items = _decoded(source, semantic_tokens(source))

        self.assertIn((0, 23, 4, "keyword", 0), items)
        self.assertIn((0, 28, 6, "keyword", 0), items)
        self.assertIn((0, 38, 6, "keyword", 0), items)

    def test_typed_object_shape_marks_type_names_as_keywords(self) -> None:
        source = (
            "function score(value: object{name:string,score:list[number]}): number {\n"
            "    return value.score[0];\n"
            "}\n"
        )
        items = _decoded(source, semantic_tokens(source))

        keyword_slices = {
            source.splitlines()[line][start:start + length]
            for line, start, length, kind, _modifiers in items
            if kind == "keyword"
        }
        self.assertTrue({"object", "string", "list", "number"}.issubset(keyword_slices))

    def test_multiline_string_is_split_by_line(
        self,
    ) -> None:
        source = (
            'mission "Semantic" {\n'
            '    source label "alpha\n'
            'beta";\n'
            "    publish label;\n"
            "}\n"
        )
        items = _decoded(
            source,
            semantic_tokens(source),
        )
        string_items = [
            item
            for item in items
            if item[3] == "string"
        ]

        self.assertGreaterEqual(
            len(string_items),
            3,
        )
        self.assertTrue(
            all(
                item[2] > 0
                for item in string_items
            )
        )

    def test_utf16_length_matches_lsp_units(
        self,
    ) -> None:
        source = (
            'mission "😀" {}\n'
        )
        items = _decoded(
            source,
            semantic_tokens(source),
        )
        string_item = next(
            item
            for item in items
            if item[3] == "string"
        )

        self.assertEqual(
            string_item[2],
            4,
        )

    def test_lexical_failure_returns_empty_data(
        self,
    ) -> None:
        self.assertEqual(
            semantic_tokens(
                'mission "unterminated'
            ),
            {"data": []},
        )

    def test_server_uses_unsaved_document(
        self,
    ) -> None:
        server = LanguageServer()
        uri = (
            "file:///tmp/"
            "semantic.vectis"
        )
        source = (
            'mission "Semantic" { '
            "source quality 96; "
            'let label concat("Q", quality); '
            "publish label; }"
        )
        server.documents[uri] = source

        reply = server.handle(
            {
                "jsonrpc": "2.0",
                "id": 40,
                "method": (
                    "textDocument/"
                    "semanticTokens/full"
                ),
                "params": {
                    "textDocument": {
                        "uri": uri
                    }
                },
            }
        )[0]

        self.assertTrue(
            reply["result"]["data"]
        )


    def test_private_function_modifier_is_contextual_keyword(self) -> None:
        source = (
            "private function helper(value: number): number {\n"
            "    return value;\n"
            "}\n"
        )
        items = _decoded(source, semantic_tokens(source))
        self.assertIn((0, 0, 7, "keyword", 0), items)
        self.assertIn((0, 17, 6, "function", 1), items)


if __name__ == "__main__":
    unittest.main()
