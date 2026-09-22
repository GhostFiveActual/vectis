# GHOST FIVE // VECTIS
# Regression coverage for the VECTIS examples contract.
from __future__ import annotations

from pathlib import Path
import unittest

from vectis.compiler import compile_program
from vectis.parser import ParserError, parse


VALID_DIR = Path("examples/valid")
SYNTAX_INVALID_DIR = Path("examples/invalid")
SEMANTIC_INVALID_DIR = Path(
    "examples/semantic-invalid"
)
SHOWCASE = Path(
    "examples/showcase/full-release-assurance.vectis"
)


def compile_path(path: Path):
    program = parse(
        path.read_text(encoding="utf-8"),
        file=str(path),
    )
    return compile_program(program)


class ExampleTests(unittest.TestCase):
    def test_end_to_end_example_exists(self):
        self.assertTrue(
            (
                VALID_DIR
                / "end-to-end.vectis"
            ).is_file()
        )

    def test_capability_workflow_exists(self):
        self.assertTrue(
            (
                VALID_DIR
                / "capability-workflow.vectis"
            ).is_file()
        )

    def test_all_valid_examples_parse(self):
        paths = sorted(
            VALID_DIR.glob("*.vectis")
        )

        self.assertGreaterEqual(
            len(paths),
            2,
        )

        for path in paths:
            with self.subTest(path=path):
                parse(
                    path.read_text(
                        encoding="utf-8"
                    ),
                    file=str(path),
                )

    def test_dx002_valid_examples_compile(self):
        paths = (
            VALID_DIR / "end-to-end.vectis",
            VALID_DIR / "capability-workflow.vectis",
        )

        for path in paths:
            with self.subTest(path=path):
                result = compile_path(path)

                self.assertEqual(
                    result.diagnostics,
                    (),
                )

                self.assertIsNotNone(
                    result.graph
                )

    def test_end_to_end_compilation_is_deterministic(self):
        path = (
            VALID_DIR
            / "end-to-end.vectis"
        )

        first = compile_path(path)
        second = compile_path(path)

        self.assertIsNotNone(
            first.graph
        )
        self.assertIsNotNone(
            second.graph
        )

        self.assertEqual(
            first.graph.to_json(),
            second.graph.to_json(),
        )

    def test_capability_workflow_compiles(self):
        result = compile_path(
            VALID_DIR
            / "capability-workflow.vectis"
        )

        self.assertFalse(
            result.diagnostics
        )
        self.assertIsNotNone(
            result.graph
        )

    def test_semantic_invalid_examples_parse(self):
        paths = sorted(
            SEMANTIC_INVALID_DIR.glob(
                "*.vectis"
            )
        )

        self.assertGreaterEqual(
            len(paths),
            2,
        )

        for path in paths:
            with self.subTest(path=path):
                parse(
                    path.read_text(
                        encoding="utf-8"
                    ),
                    file=str(path),
                )

    def test_semantic_invalid_examples_have_diagnostics(self):
        for path in sorted(
            SEMANTIC_INVALID_DIR.glob(
                "*.vectis"
            )
        ):
            with self.subTest(path=path):
                result = compile_path(path)

                self.assertTrue(
                    result.diagnostics
                )

    def test_semantic_invalid_examples_do_not_compile(self):
        for path in sorted(
            SEMANTIC_INVALID_DIR.glob(
                "*.vectis"
            )
        ):
            with self.subTest(path=path):
                result = compile_path(path)

                self.assertIsNone(
                    result.graph
                )

    def test_unresolved_reference_is_semantically_invalid(self):
        result = compile_path(
            SEMANTIC_INVALID_DIR
            / "unresolved-reference.vectis"
        )

        self.assertTrue(
            result.diagnostics
        )

    def test_type_mismatch_is_semantically_invalid(self):
        result = compile_path(
            SEMANTIC_INVALID_DIR
            / "type-mismatch.vectis"
        )

        self.assertTrue(
            result.diagnostics
        )

    def test_syntax_invalid_examples_fail_parse(self):
        paths = sorted(
            SYNTAX_INVALID_DIR.glob(
                "*.vectis"
            )
        )

        self.assertTrue(paths)

        for path in paths:
            with self.subTest(path=path):
                with self.assertRaises(
                    ParserError
                ):
                    parse(
                        path.read_text(
                            encoding="utf-8"
                        ),
                        file=str(path),
                    )

    def test_showcase_compiles_and_executes(self):
        self.assertTrue(SHOWCASE.is_file())
        result = compile_path(SHOWCASE)
        self.assertTrue(result.ok)
        self.assertIsNotNone(result.graph)

        from vectis.runtime import Runtime

        runtime = Runtime(result.graph).execute()
        self.assertTrue(runtime.success)
        values = dict(runtime.node_values)
        self.assertTrue(values["release_authorized"])

    def test_showcase_compilation_is_deterministic(self):
        first = compile_path(SHOWCASE)
        second = compile_path(SHOWCASE)
        self.assertEqual(
            first.graph.to_json(),
            second.graph.to_json(),
        )

    def test_examples_documentation_exists(self):
        self.assertTrue(
            Path(
                "docs/examples.md"
            ).is_file()
        )


if __name__ == "__main__":
    unittest.main()
