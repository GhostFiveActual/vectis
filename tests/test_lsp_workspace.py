# GHOST FIVE // VECTIS
# Verifies overlay module resolution and exact pure-function navigation.
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from vectis.compiler import compile_program
from vectis.modules import ModuleError
from vectis.lsp_workspace import (
    function_definition,
    function_references,
    function_rename,
    load_workspace_program,
    symbol_definition,
    symbol_references,
    symbol_rename,
    value_occurrences,
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


    def test_mission_value_navigation_and_rename(
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
            entry.write_text(source, encoding="utf-8")
            workspace = load_workspace_program(entry)

            line = 2
            character = source.splitlines()[line].index("quality") + 2

            definition = symbol_definition(
                workspace,
                path=entry,
                line=line,
                character=character,
            )
            self.assertIsNotNone(definition)
            self.assertEqual(
                definition["uri"],
                entry.resolve().as_uri(),
            )
            self.assertEqual(
                definition["range"]["start"]["line"],
                1,
            )

            references = symbol_references(
                workspace,
                path=entry,
                line=line,
                character=character,
                include_declaration=True,
            )
            self.assertEqual(len(references), 2)

            edit = symbol_rename(
                workspace,
                path=entry,
                line=line,
                character=character,
                new_name="score",
            )
            self.assertIsNotNone(edit)
            changes = edit["changes"][entry.resolve().as_uri()]
            self.assertEqual(len(changes), 2)
            self.assertTrue(
                all(item["newText"] == "score" for item in changes)
            )

    def test_all_executable_value_declarations_are_tracked(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entry = root / "main.vectis"
            source = (
                'mission "Values" {\n'
                '    source path "input.txt";\n'
                "    analyze insight path;\n"
                '    action content "filesystem.read_text" '
                'using "filesystem" {path: path};\n'
                "    let output content;\n"
                "    publish output;\n"
                "}\n"
            )
            entry.write_text(source, encoding="utf-8")
            workspace = load_workspace_program(entry)
            occurrences = value_occurrences(workspace)
            declarations = {
                item.name
                for item in occurrences
                if item.declaration
            }

            self.assertEqual(
                declarations,
                {"path", "insight", "content", "output"},
            )
            reference_names = [
                item.name
                for item in occurrences
                if not item.declaration
            ]
            self.assertEqual(reference_names.count("path"), 2)
            self.assertIn("content", reference_names)
            self.assertIn("output", reference_names)

    def test_nested_value_references_keep_entry_identity(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entry = root / "main.vectis"
            source = (
                'mission "Nested" {\n'
                "    source ready true;\n"
                '    stage "Check" {\n'
                "        let score 96;\n"
                "        when ready {\n"
                "            publish score;\n"
                "        }\n"
                "    }\n"
                "}\n"
            )
            entry.write_text(source, encoding="utf-8")
            workspace = load_workspace_program(entry)
            occurrences = value_occurrences(workspace)

            ready = [item for item in occurrences if item.name == "ready"]
            score = [item for item in occurrences if item.name == "score"]
            self.assertEqual(len(ready), 2)
            self.assertEqual(len(score), 2)
            self.assertEqual(sum(item.declaration for item in ready), 1)
            self.assertEqual(sum(item.declaration for item in score), 1)

    def test_function_parameters_are_not_mission_values(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entry = root / "main.vectis"
            source = (
                "function echo(value) {\n"
                "    return value;\n"
                "}\n"
                'mission "Values" {\n'
                '    source value "x";\n'
                "    let output echo(value);\n"
                "    publish output;\n"
                "}\n"
            )
            entry.write_text(source, encoding="utf-8")
            workspace = load_workspace_program(entry)
            occurrences = value_occurrences(workspace)

            value_items = [
                item for item in occurrences if item.name == "value"
            ]
            self.assertEqual(len(value_items), 2)
            self.assertEqual(
                sum(item.declaration for item in value_items),
                1,
            )

    def test_ambiguous_value_declarations_fail_closed(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entry = root / "main.vectis"
            source = (
                'mission "Ambiguous" {\n'
                "    source value 1;\n"
                "    let value 2;\n"
                "    publish value;\n"
                "}\n"
            )
            entry.write_text(source, encoding="utf-8")
            workspace = load_workspace_program(entry)
            line = 3
            character = source.splitlines()[line].index("value") + 2

            self.assertIsNone(
                symbol_definition(
                    workspace,
                    path=entry,
                    line=line,
                    character=character,
                )
            )
            self.assertEqual(
                symbol_references(
                    workspace,
                    path=entry,
                    line=line,
                    character=character,
                    include_declaration=True,
                ),
                [],
            )
            self.assertIsNone(
                symbol_rename(
                    workspace,
                    path=entry,
                    line=line,
                    character=character,
                    new_name="renamed",
                )
            )

    def test_value_rename_rejects_conflicts_and_reserved_names(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entry = root / "main.vectis"
            source = (
                'mission "Values" {\n'
                "    source first 1;\n"
                "    let second first + 1;\n"
                "    publish second;\n"
                "}\n"
            )
            entry.write_text(source, encoding="utf-8")
            workspace = load_workspace_program(entry)
            line = 2
            character = source.splitlines()[line].index("first") + 2

            with self.assertRaises(ValueError):
                symbol_rename(
                    workspace,
                    path=entry,
                    line=line,
                    character=character,
                    new_name="second",
                )

            for reserved in ("mission", "true", "false"):
                with self.assertRaises(ValueError):
                    symbol_rename(
                        workspace,
                        path=entry,
                        line=line,
                        character=character,
                        new_name=reserved,
                    )


    def test_navigation_ranges_and_cursor_use_utf16(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            entry = Path(directory) / "main.vectis"
            source = (
                'mission "😀" { source quality 96; '
                'let approved quality >= 90; publish approved; }'
            )
            entry.write_text(source, encoding="utf-8")
            workspace = load_workspace_program(entry)
            reference_index = source.index("quality", source.index("let")) + 2
            character = len(
                source[:reference_index].encode("utf-16-le")
            ) // 2

            definition = symbol_definition(
                workspace,
                path=entry,
                line=0,
                character=character,
            )
            self.assertIsNotNone(definition)
            declaration_index = source.index("quality")
            expected_start = len(
                source[:declaration_index].encode("utf-16-le")
            ) // 2
            self.assertEqual(
                definition["range"]["start"]["character"],
                expected_start,
            )

            edit = symbol_rename(
                workspace,
                path=entry,
                line=0,
                character=character,
                new_name="score",
            )
            self.assertIsNotNone(edit)
            starts = [
                item["range"]["start"]["character"]
                for item in edit["changes"][entry.resolve().as_uri()]
            ]
            self.assertIn(expected_start, starts)


    def test_private_import_is_rejected_with_unsaved_overlay(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "vectis.toml").write_text("[project]\n", encoding="utf-8")
            library = root / "lib.vectis"
            entry = root / "main.vectis"
            library.write_text(
                "function helper(value) { return value; }\n",
                encoding="utf-8",
            )
            entry.write_text(
                'import "lib.vectis";\n'
                'mission "bad" { publish helper(true); }\n',
                encoding="utf-8",
            )
            overlays = {
                library.resolve(): (
                    "private function helper(value) { return value; }\n"
                )
            }
            with self.assertRaisesRegex(ModuleError, "private to module"):
                load_workspace_program(entry, overlays=overlays)


if __name__ == "__main__":
    unittest.main()
