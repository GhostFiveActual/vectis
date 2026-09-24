# GHOST FIVE // VECTIS
# Verifies deterministic signature help for built-ins and pure functions.
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from vectis.lsp import LanguageServer
from vectis.lsp_signature import signature_help
from vectis.lsp_workspace import load_workspace_program


class LspSignatureHelpTests(unittest.TestCase):
    def test_builtin_fixed_arity_and_active_parameter(self) -> None:
        source = (
            'mission "Signature" { '
            'let result replace("a", "b", "c"); '
            'publish result; }'
        )
        character = source.index('"b"') + 1
        result = signature_help(
            source,
            line=0,
            character=character,
        )

        self.assertIsNotNone(result)
        self.assertEqual(
            result["signatures"][0]["label"],
            "replace(arg1, arg2, arg3)",
        )
        self.assertEqual(
            result["activeParameter"],
            1,
        )

    def test_nested_call_selects_innermost_signature(self) -> None:
        source = (
            'mission "Signature" { '
            'let result concat("a", upper("b"), "c"); '
            'publish result; }'
        )
        character = source.index('"b"') + 1
        result = signature_help(
            source,
            line=0,
            character=character,
        )

        self.assertIsNotNone(result)
        self.assertEqual(
            result["signatures"][0]["label"],
            "upper(arg1)",
        )
        self.assertEqual(
            result["activeParameter"],
            0,
        )

    def test_variadic_signature_uses_stable_variadic_slot(self) -> None:
        source = (
            'mission "Signature" { '
            'let result concat("a", "b", "c"); '
            'publish result; }'
        )
        character = source.index('"c"') + 1
        result = signature_help(
            source,
            line=0,
            character=character,
        )

        self.assertIsNotNone(result)
        self.assertEqual(
            result["signatures"][0]["label"],
            "concat(arg1, ...)",
        )
        self.assertEqual(
            result["activeParameter"],
            1,
        )

    def test_commas_inside_nested_values_do_not_advance_outer_call(self) -> None:
        source = (
            'mission "Signature" { '
            'let result concat("a,b", [1, 2], "c"); '
            'publish result; }'
        )
        character = source.index('"c"') + 1
        result = signature_help(
            source,
            line=0,
            character=character,
        )

        self.assertIsNotNone(result)
        self.assertEqual(
            result["activeParameter"],
            1,
        )

    def test_workspace_user_function_uses_overlay_parameters(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            library = root / "library.vectis"
            entry = root / "main.vectis"

            library.write_text(
                (
                    "function stale(value) {\n"
                    "    return value;\n"
                    "}\n"
                ),
                encoding="utf-8",
            )
            entry_source = (
                'import "library.vectis";\n'
                'mission "Signature" {\n'
                "    let result ready(96, 90);\n"
                "    publish result;\n"
                "}\n"
            )
            entry.write_text(
                entry_source,
                encoding="utf-8",
            )
            library_overlay = (
                "function ready(value, threshold) {\n"
                "    return value >= threshold;\n"
                "}\n"
            )

            workspace = load_workspace_program(
                entry,
                overlays={
                    library.resolve(): library_overlay
                },
            )
            line = 2
            character = (
                entry_source.splitlines()[line].index("90")
                + 1
            )
            result = signature_help(
                entry_source,
                line=line,
                character=character,
                workspace=workspace,
            )

            self.assertIsNotNone(result)
            self.assertEqual(
                result["signatures"][0]["label"],
                "ready(value, threshold)",
            )
            self.assertEqual(
                result["activeParameter"],
                1,
            )

    def test_server_handles_incomplete_call_with_unsaved_import_overlay(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            library = root / "library.vectis"
            entry = root / "main.vectis"

            library.write_text(
                (
                    "function stale(value) {\n"
                    "    return value;\n"
                    "}\n"
                ),
                encoding="utf-8",
            )
            entry.write_text(
                (
                    'import "library.vectis";\n'
                    'mission "Saved" {\n'
                    "    let result stale(96);\n"
                    "    publish result;\n"
                    "}\n"
                ),
                encoding="utf-8",
            )

            library_uri = library.resolve().as_uri()
            entry_uri = entry.resolve().as_uri()
            library_source = (
                "function ready(value, threshold) {\n"
                "    return value >= threshold;\n"
                "}\n"
            )
            entry_source = (
                'import "library.vectis";\n'
                'mission "Signature" {\n'
                "    let result ready(\n"
            )

            server = LanguageServer()
            server.documents[library_uri] = library_source
            server.documents[entry_uri] = entry_source

            line = 2
            character = len(
                entry_source.splitlines()[line]
            )
            reply = server.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 30,
                    "method": "textDocument/signatureHelp",
                    "params": {
                        "textDocument": {
                            "uri": entry_uri
                        },
                        "position": {
                            "line": line,
                            "character": character,
                        },
                    },
                }
            )[0]

            self.assertEqual(
                reply["result"]["signatures"][0]["label"],
                "ready(value, threshold)",
            )
            self.assertEqual(
                reply["result"]["activeParameter"],
                0,
            )


    def test_typed_user_function_signature_is_exposed(self) -> None:
        source = (
            "function ready(value: number, threshold: number): boolean {\n"
            "    return value >= threshold;\n"
            "}\n"
            'mission "Signature" { let result ready(96, 90); }\n'
        )
        character = source.splitlines()[3].index("90") + 1
        result = signature_help(
            source,
            line=3,
            character=character,
            supplemental_sources=(source,),
        )

        self.assertIsNotNone(result)
        self.assertEqual(
            result["signatures"][0]["label"],
            "ready(value: number, threshold: number): boolean",
        )
        self.assertEqual(result["activeParameter"], 1)

    def test_signature_cursor_uses_utf16_character_units(self) -> None:
        source = 'mission "😀" { let result concat("a", "b"); }'
        target = source.index('"b"') + 1
        character = len(source[:target].encode("utf-16-le")) // 2
        result = signature_help(
            source,
            line=0,
            character=character,
        )
        self.assertIsNotNone(result)
        self.assertEqual(
            result["signatures"][0]["label"],
            "concat(arg1, ...)",
        )
        self.assertEqual(result["activeParameter"], 1)


if __name__ == "__main__":
    unittest.main()
