# GHOST FIVE // VECTIS
# Verifies the dependency-free VECTIS Language Server Protocol surface.
from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()
