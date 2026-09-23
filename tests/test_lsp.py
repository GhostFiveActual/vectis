# GHOST FIVE // VECTIS
# Verifies the dependency-free VECTIS Language Server Protocol surface.
from __future__ import annotations

import json
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
        self.assertIn("executeCommandProvider", capabilities)
        self.assertEqual(
            capabilities["executeCommandProvider"]["commands"],
            [
                "vectis.graph.inspect",
                "vectis.history.inspect",
                "vectis.capabilities.inspect",
            ],
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


    def test_graph_inspection_uses_unsaved_document(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entry = root / "main.vectis"
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
            self.server.documents[uri] = (
                'mission "Graph" {\n'
                '    stage "Inputs" {\n'
                '        source ready true;\n'
                '    }\n'
                '    stage "Decision" {\n'
                '        let approved ready;\n'
                '        when approved {\n'
                '            publish "yes";\n'
                '        }\n'
                '    }\n'
                '}\n'
            )

            result = self.server.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 50,
                    "method": "workspace/executeCommand",
                    "params": {
                        "command": "vectis.graph.inspect",
                        "arguments": [{"uri": uri}],
                    },
                }
            )[0]["result"]

            self.assertTrue(result["ok"])
            inspection = result["inspection"]
            ids = {item["id"] for item in inspection["nodes"]}
            self.assertIn("ready", ids)
            self.assertIn("approved", ids)
            self.assertNotIn("stale", ids)
            self.assertEqual(len(inspection["fingerprint"]), 64)
            self.assertTrue(
                all("value" not in item for item in inspection["nodes"])
            )

    def test_graph_inspection_failures_are_structured(self) -> None:
        self.server.documents[self.uri] = 'mission "Broken" {'

        result = self.server.handle(
            {
                "jsonrpc": "2.0",
                "id": 51,
                "method": "workspace/executeCommand",
                "params": {
                    "command": "vectis.graph.inspect",
                    "arguments": [{"uri": self.uri}],
                },
            }
        )[0]["result"]

        self.assertFalse(result["ok"])
        self.assertTrue(result["diagnostics"])

        invalid = self.server.handle(
            {
                "jsonrpc": "2.0",
                "id": 52,
                "method": "workspace/executeCommand",
                "params": {
                    "command": "vectis.graph.inspect",
                    "arguments": [],
                },
            }
        )[0]
        self.assertEqual(invalid["error"]["code"], -32602)


    def test_history_inspection_is_project_bounded_and_value_free(
        self,
    ) -> None:
        sensitive = "LSP-HISTORY-SECRET"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "vectis.toml").write_text(
                "# GHOST FIVE // VECTIS\n",
                encoding="utf-8",
            )
            entry = root / "main.vectis"
            entry.write_text(
                'mission "History" {}\n',
                encoding="utf-8",
            )
            history = root / "history"
            history.mkdir()
            receipt = {
                "schema": "vectis.execution-receipt/v1",
                "plan": {
                    "fingerprint": "b" * 64,
                    "summary": {
                        "nodes": 1,
                        "edges": 0,
                        "branch_edges": 0,
                        "stage_count": 0,
                        "stages": [],
                        "depth": 0,
                        "levels": 1,
                        "max_width": 1,
                        "max_fan_in": 0,
                        "max_fan_out": 0,
                        "sources": ["node"],
                        "sinks": ["node"],
                        "node_kinds": {
                            "source": 1,
                        },
                        "fingerprint": "b" * 64,
                        "topological_order": [
                            "node",
                        ],
                    },
                    "authority": {},
                },
                "execution": {
                    "status": "success",
                    "success": True,
                    "dry_run": False,
                    "execution_order": [
                        "node",
                    ],
                    "node_states": [
                        {
                            "node": "node",
                            "state": "succeeded",
                        }
                    ],
                    "failures": [],
                },
                "provenance": {
                    "vectis_version": "0.8.0",
                    "source": "main.vectis",
                    "granted_capabilities": [],
                    "registered_actions": [],
                    "runtime_values_recorded": False,
                },
                "evidence": {
                    "recorded_at": "2026-09-23T12:00:00Z",
                },
                "runtime_values": {
                    "secret": sensitive,
                },
            }
            (history / "run.json").write_text(
                json.dumps(receipt),
                encoding="utf-8",
            )
            uri = entry.resolve().as_uri()

            result = self.server.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 53,
                    "method": "workspace/executeCommand",
                    "params": {
                        "command": "vectis.history.inspect",
                        "arguments": [
                            {
                                "uri": uri,
                                "directory": "history",
                                "limit": 10,
                            }
                        ],
                    },
                }
            )[0]["result"]

            self.assertTrue(result["ok"])
            rendered = json.dumps(
                result,
                sort_keys=True,
            )
            self.assertNotIn(
                sensitive,
                rendered,
            )
            self.assertEqual(
                result["history"]["entries"][0]["receipt"],
                "run.json",
            )

            escaped = self.server.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 54,
                    "method": "workspace/executeCommand",
                    "params": {
                        "command": "vectis.history.inspect",
                        "arguments": [
                            {
                                "uri": uri,
                                "directory": "..",
                            }
                        ],
                    },
                }
            )[0]["result"]
            self.assertFalse(
                escaped["ok"]
            )

    def test_capability_configuration_uses_overlay_and_project_profile(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "vectis.toml").write_text(
                "# GHOST FIVE // VECTIS\n",
                encoding="utf-8",
            )
            workspace = root / "workspace"
            workspace.mkdir()
            profile = root / "actions.toml"
            profile.write_text(
                (
                    "# GHOST FIVE // VECTIS\n"
                    "# Capability configuration LSP test.\n"
                    "[actions.filesystem]\n"
                    'roots = ["workspace"]\n'
                ),
                encoding="utf-8",
            )
            entry = root / "main.vectis"
            entry.write_text(
                'mission "Saved" { source stale true; publish stale; }\n',
                encoding="utf-8",
            )
            uri = entry.resolve().as_uri()
            self.server.documents[uri] = (
                "// GHOST FIVE // VECTIS\n"
                "// Capability configuration overlay test.\n"
                'mission "Overlay" {\n'
                '    action content "filesystem.read_text" '
                'using "filesystem" {path: "input.txt"};\n'
                '    publish content;\n'
                '}\n'
            )

            result = self.server.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 55,
                    "method": "workspace/executeCommand",
                    "params": {
                        "command": "vectis.capabilities.inspect",
                        "arguments": [
                            {
                                "uri": uri,
                                "profile": "actions.toml",
                            }
                        ],
                    },
                }
            )[0]["result"]

            self.assertTrue(result["ok"])
            preview = result["configuration"]
            self.assertTrue(preview["satisfied"])
            self.assertEqual(
                preview["plan"]["actions"][0]["operation"],
                "filesystem.read_text",
            )
            self.assertEqual(
                preview["configuration"]["profile"]["source"],
                "actions.toml",
            )
            rendered = json.dumps(result, sort_keys=True)
            self.assertNotIn(
                str(root.resolve()),
                rendered,
            )

            escaped = self.server.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 56,
                    "method": "workspace/executeCommand",
                    "params": {
                        "command": "vectis.capabilities.inspect",
                        "arguments": [
                            {
                                "uri": uri,
                                "profile": "../outside.toml",
                            }
                        ],
                    },
                }
            )[0]["result"]
            self.assertFalse(escaped["ok"])

    def test_diagnostic_range_uses_utf16_units(self) -> None:
        source = 'mission "😀" { publish missing; }'
        self.server.documents[self.uri] = source
        replies = self.server.handle(
            {
                "jsonrpc": "2.0",
                "method": "textDocument/didOpen",
                "params": {
                    "textDocument": {
                        "uri": self.uri,
                        "text": source,
                    }
                },
            }
        )
        diagnostic = replies[0]["params"]["diagnostics"][0]
        index = source.index("missing")
        expected = len(source[:index].encode("utf-16-le")) // 2
        self.assertEqual(
            diagnostic["range"]["start"]["character"],
            expected,
        )


if __name__ == "__main__":
    unittest.main()
