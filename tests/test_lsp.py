# GHOST FIVE // VECTIS
# Verifies the dependency-free VECTIS Language Server Protocol surface.
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from vectis.formatter import format_program
from vectis.lsp import LanguageServer
from vectis.parser import parse


class LanguageServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = LanguageServer()
        self.uri = "file:///tmp/example.vectis"

    def test_initialize_advertises_full_sync_and_formatting(self) -> None:
        replies = self.server.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {},
            }
        )
        capabilities = replies[0]["result"]["capabilities"]
        self.assertEqual(capabilities["textDocumentSync"]["change"], 1)
        self.assertTrue(capabilities["documentFormattingProvider"])
        self.assertTrue(capabilities["hoverProvider"])
        self.assertTrue(capabilities["documentSymbolProvider"])
        self.assertTrue(capabilities["definitionProvider"])
        self.assertTrue(capabilities["referencesProvider"])
        self.assertTrue(capabilities["renameProvider"])
        self.assertIn("signatureHelpProvider", capabilities)
        self.assertEqual(
            capabilities["signatureHelpProvider"]["triggerCharacters"],
            ["(", ","],
        )
        self.assertIn("semanticTokensProvider", capabilities)
        self.assertTrue(
            capabilities["semanticTokensProvider"]["full"]
        )
        self.assertIn("completionProvider", capabilities)

    def test_open_publishes_parser_diagnostic(self) -> None:
        replies = self.server.handle(
            {
                "jsonrpc": "2.0",
                "method": "textDocument/didOpen",
                "params": {
                    "textDocument": {
                        "uri": self.uri,
                        "text": 'mission "Broken" { source ready true;',
                    }
                },
            }
        )
        diagnostics = replies[0]["params"]["diagnostics"]
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0]["source"], "vectis")
        self.assertTrue(diagnostics[0]["code"].startswith("SYN"))

    def test_change_replaces_full_document_and_clears_diagnostic(self) -> None:
        self.server.documents[self.uri] = 'mission "Broken" {'
        valid = 'mission "Ready" { source ready true; publish ready; }'
        replies = self.server.handle(
            {
                "jsonrpc": "2.0",
                "method": "textDocument/didChange",
                "params": {
                    "textDocument": {"uri": self.uri},
                    "contentChanges": [{"text": valid}],
                },
            }
        )
        self.assertEqual(self.server.documents[self.uri], valid)
        self.assertEqual(replies[0]["params"]["diagnostics"], [])

    def test_formatting_uses_canonical_formatter(self) -> None:
        source = 'mission "Ready" { source ready true; publish ready; }'
        self.server.documents[self.uri] = source
        replies = self.server.handle(
            {
                "jsonrpc": "2.0",
                "id": 7,
                "method": "textDocument/formatting",
                "params": {
                    "textDocument": {"uri": self.uri},
                    "options": {"tabSize": 4, "insertSpaces": True},
                },
            }
        )
        edits = replies[0]["result"]
        self.assertEqual(len(edits), 1)
        self.assertEqual(
            edits[0]["newText"],
            format_program(parse(source, file=self.uri)),
        )

    def test_completion_uses_language_registry(self) -> None:
        replies = self.server.handle(
            {
                "jsonrpc": "2.0",
                "id": 8,
                "method": "textDocument/completion",
                "params": {
                    "textDocument": {"uri": self.uri},
                    "position": {"line": 0, "character": 0},
                },
            }
        )
        labels = [
            item["label"]
            for item in replies[0]["result"]["items"]
        ]
        self.assertIn("mission", labels)
        self.assertIn("concat", labels)
        self.assertIn("filesystem.read_text", labels)

    def test_hover_and_document_symbols(self) -> None:
        source = (
            'mission "Ready" { source quality 96; '
            'let label concat("Q", quality); publish label; }'
        )
        self.server.documents[self.uri] = source

        hover = self.server.handle(
            {
                "jsonrpc": "2.0",
                "id": 9,
                "method": "textDocument/hover",
                "params": {
                    "textDocument": {"uri": self.uri},
                    "position": {"line": 0, "character": 47},
                },
            }
        )
        self.assertIn(
            "Pure and deterministic",
            hover[0]["result"]["contents"]["value"],
        )

        symbols = self.server.handle(
            {
                "jsonrpc": "2.0",
                "id": 10,
                "method": "textDocument/documentSymbol",
                "params": {
                    "textDocument": {"uri": self.uri},
                },
            }
        )
        self.assertEqual(symbols[0]["result"][0]["name"], "Ready")
        child_names = [
            item["name"]
            for item in symbols[0]["result"][0]["children"]
        ]
        self.assertEqual(child_names, ["quality", "label"])

    def test_close_clears_diagnostics(self) -> None:
        self.server.documents[self.uri] = 'mission "Ready" {}'
        replies = self.server.handle(
            {
                "jsonrpc": "2.0",
                "method": "textDocument/didClose",
                "params": {"textDocument": {"uri": self.uri}},
            }
        )
        self.assertNotIn(self.uri, self.server.documents)
        self.assertEqual(replies[0]["params"]["diagnostics"], [])


    def test_unsaved_import_overlay_updates_importer_diagnostics(
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
            entry_source = (
                'import "library.vectis";\n'
                'mission "Overlay" {\n'
                "    let result ready(96);\n"
                "    publish result;\n"
                "}\n"
            )
            entry.write_text(
                entry_source,
                encoding="utf-8",
            )

            library_uri = (
                library.resolve().as_uri()
            )
            entry_uri = (
                entry.resolve().as_uri()
            )

            self.server.handle(
                {
                    "jsonrpc": "2.0",
                    "method": "textDocument/didOpen",
                    "params": {
                        "textDocument": {
                            "uri": library_uri,
                            "text": (
                                "function ready(value) {\n"
                                "    return value >= 90;\n"
                                "}\n"
                            ),
                        }
                    },
                }
            )
            replies = self.server.handle(
                {
                    "jsonrpc": "2.0",
                    "method": "textDocument/didOpen",
                    "params": {
                        "textDocument": {
                            "uri": entry_uri,
                            "text": entry_source,
                        }
                    },
                }
            )

            entry_diagnostics = next(
                item["params"]["diagnostics"]
                for item in replies
                if item["params"]["uri"]
                == entry_uri
            )
            self.assertEqual(
                entry_diagnostics,
                [],
            )

            changed = self.server.handle(
                {
                    "jsonrpc": "2.0",
                    "method": "textDocument/didChange",
                    "params": {
                        "textDocument": {
                            "uri": library_uri
                        },
                        "contentChanges": [
                            {
                                "text": (
                                    "function denied(value) {\n"
                                    "    return value >= 90;\n"
                                    "}\n"
                                )
                            }
                        ],
                    },
                }
            )

            importer = next(
                item["params"]["diagnostics"]
                for item in changed
                if item["params"]["uri"]
                == entry_uri
            )
            self.assertTrue(importer)

    def test_definition_references_and_rename_cross_import(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            library = root / "library.vectis"
            entry = root / "main.vectis"

            library_source = (
                "function ready(value) {\n"
                "    return value >= 90;\n"
                "}\n"
            )
            entry_source = (
                'import "library.vectis";\n'
                'mission "Navigation" {\n'
                "    let result ready(96);\n"
                "    publish result;\n"
                "}\n"
            )
            library.write_text(
                library_source,
                encoding="utf-8",
            )
            entry.write_text(
                entry_source,
                encoding="utf-8",
            )

            library_uri = (
                library.resolve().as_uri()
            )
            entry_uri = (
                entry.resolve().as_uri()
            )
            self.server.documents[
                library_uri
            ] = library_source
            self.server.documents[
                entry_uri
            ] = entry_source

            line = 2
            character = (
                entry_source.splitlines()[
                    line
                ].index("ready")
                + 2
            )

            definition = self.server.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 20,
                    "method": (
                        "textDocument/definition"
                    ),
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
            )[0]["result"]
            self.assertEqual(
                definition["uri"],
                library_uri,
            )

            references = self.server.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 21,
                    "method": (
                        "textDocument/references"
                    ),
                    "params": {
                        "textDocument": {
                            "uri": entry_uri
                        },
                        "position": {
                            "line": line,
                            "character": character,
                        },
                        "context": {
                            "includeDeclaration": True
                        },
                    },
                }
            )[0]["result"]
            self.assertEqual(
                len(references),
                2,
            )

            rename = self.server.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 22,
                    "method": (
                        "textDocument/rename"
                    ),
                    "params": {
                        "textDocument": {
                            "uri": entry_uri
                        },
                        "position": {
                            "line": line,
                            "character": character,
                        },
                        "newName": "approved",
                    },
                }
            )[0]["result"]
            self.assertEqual(
                set(rename["changes"]),
                {
                    entry_uri,
                    library_uri,
                },
            )
            self.assertTrue(
                all(
                    edit["newText"]
                    == "approved"
                    for edits in rename[
                        "changes"
                    ].values()
                    for edit in edits
                )
            )


    def test_mission_value_definition_references_and_rename(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entry = root / "main.vectis"
            source = (
                'mission "Values" {\n'
                "    source quality 96;\n"
                "    let approved quality >= 90;\n"
                "    publish approved;\n"
                "}\n"
            )
            entry.write_text(
                (
                    'mission "Saved" {\n'
                    '    source stale 1;\n'
                    '    publish stale;\n'
                    '}\n'
                ),
                encoding="utf-8",
            )
            uri = entry.resolve().as_uri()
            self.server.documents[uri] = source

            line = 2
            character = source.splitlines()[line].index("quality") + 2

            definition = self.server.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 40,
                    "method": "textDocument/definition",
                    "params": {
                        "textDocument": {"uri": uri},
                        "position": {
                            "line": line,
                            "character": character,
                        },
                    },
                }
            )[0]["result"]
            self.assertEqual(
                definition["range"]["start"]["line"],
                1,
            )

            references = self.server.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 41,
                    "method": "textDocument/references",
                    "params": {
                        "textDocument": {"uri": uri},
                        "position": {
                            "line": line,
                            "character": character,
                        },
                        "context": {"includeDeclaration": True},
                    },
                }
            )[0]["result"]
            self.assertEqual(len(references), 2)

            rename = self.server.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 42,
                    "method": "textDocument/rename",
                    "params": {
                        "textDocument": {"uri": uri},
                        "position": {
                            "line": line,
                            "character": character,
                        },
                        "newName": "score",
                    },
                }
            )[0]["result"]
            self.assertEqual(len(rename["changes"][uri]), 2)


if __name__ == "__main__":
    unittest.main()
