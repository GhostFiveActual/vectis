# GHOST FIVE // VECTIS
# Verifies overlay module resolution and exact pure-function navigation.
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from vectis.compiler import compile_program
from vectis.lsp_workspace import (
    function_definition,
    function_references,
    function_rename,
    load_workspace_program,
)


class LspWorkspaceTests(
    unittest.TestCase
):
    def test_unsaved_import_overlay_replaces_disk_source(
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
                    'mission "Overlay" {\n'
                    "    let result ready(96);\n"
                    "    publish result;\n"
                    "}\n"
                ),
                encoding="utf-8",
            )

            workspace = load_workspace_program(
                entry,
                overlays={
                    library.resolve(): (
                        "function ready(value) {\n"
                        "    return value >= 90;\n"
                        "}\n"
                    )
                },
            )
            compiled = compile_program(
                workspace.program
            )

            self.assertTrue(compiled.ok)
            self.assertIsNotNone(
                compiled.graph
            )

    def test_cross_file_function_navigation_and_rename(
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

            workspace = load_workspace_program(
                entry
            )

            call_line = 2
            call_character = (
                entry_source.splitlines()[
                    call_line
                ].index("ready")
                + 2
            )

            definition = function_definition(
                workspace,
                path=entry,
                line=call_line,
                character=call_character,
            )
            self.assertIsNotNone(
                definition
            )
            self.assertEqual(
                definition["uri"],
                library.resolve().as_uri(),
            )

            references = function_references(
                workspace,
                path=entry,
                line=call_line,
                character=call_character,
                include_declaration=True,
            )
            self.assertEqual(
                len(references),
                2,
            )

            edit = function_rename(
                workspace,
                path=entry,
                line=call_line,
                character=call_character,
                new_name="approved",
            )
            self.assertIsNotNone(edit)
            self.assertEqual(
                set(edit["changes"]),
                {
                    entry.resolve().as_uri(),
                    library.resolve().as_uri(),
                },
            )
            self.assertTrue(
                all(
                    item["newText"]
                    == "approved"
                    for changes in edit[
                        "changes"
                    ].values()
                    for item in changes
                )
            )


if __name__ == "__main__":
    unittest.main()
