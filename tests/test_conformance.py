# GHOST FIVE // VECTIS
# Regression coverage for the VECTIS conformance contract.
from __future__ import annotations

import subprocess
import sys
import unittest

from vectis.compiler import compile_program
from vectis.lexer import Lexer, LexerError
from vectis.parser import ParserError, parse

from tools.conformance import (
    NEGATIVE_SEMANTIC_FIXTURES,
    NEGATIVE_SYNTAX_FIXTURES,
    POSITIVE_LEXICAL_FIXTURES,
    POSITIVE_SEMANTIC_FIXTURES,
    POSITIVE_SYNTAX_FIXTURES,
    REGRESSION_FIXTURES,
    conformance_passes,
    run_conformance,
)


class TestConformance(unittest.TestCase):
    def test_positive_lexical_fixtures(self):
        for index, source in enumerate(
            POSITIVE_LEXICAL_FIXTURES,
            1,
        ):
            with self.subTest(index=index):
                tokens = Lexer(
                    source,
                    file="<test>",
                ).tokenize()

                self.assertTrue(tokens)

    def test_positive_syntax_fixtures(self):
        for index, source in enumerate(
            POSITIVE_SYNTAX_FIXTURES,
            1,
        ):
            with self.subTest(index=index):
                program = parse(
                    source,
                    file="<test>",
                )

                self.assertIsNotNone(program)

    def test_negative_syntax_fixtures(self):
        for index, source in enumerate(
            NEGATIVE_SYNTAX_FIXTURES,
            1,
        ):
            with self.subTest(index=index):
                with self.assertRaises(
                    (LexerError, ParserError)
                ):
                    parse(
                        source,
                        file="<test>",
                    )

    def test_positive_semantic_fixtures(self):
        for index, source in enumerate(
            POSITIVE_SEMANTIC_FIXTURES,
            1,
        ):
            with self.subTest(index=index):
                program = parse(
                    source,
                    file="<test>",
                )

                result = compile_program(program)

                self.assertEqual(
                    result.diagnostics,
                    (),
                )

                self.assertIsNotNone(
                    result.graph
                )

    def test_negative_semantic_fixtures(self):
        for index, source in enumerate(
            NEGATIVE_SEMANTIC_FIXTURES,
            1,
        ):
            with self.subTest(index=index):
                program = parse(
                    source,
                    file="<test>",
                )

                result = compile_program(program)

                self.assertTrue(
                    result.diagnostics
                )

                self.assertIsNone(
                    result.graph
                )

    def test_regression_fixtures(self):
        for index, source in enumerate(
            REGRESSION_FIXTURES,
            1,
        ):
            with self.subTest(index=index):
                first = compile_program(
                    parse(
                        source,
                        file="<test>",
                    )
                )

                second = compile_program(
                    parse(
                        source,
                        file="<test>",
                    )
                )

                self.assertFalse(
                    first.diagnostics
                )

                self.assertIsNotNone(
                    first.graph
                )

                self.assertEqual(
                    first.graph.to_json(),
                    second.graph.to_json(),
                )

    def test_run_conformance_returns_results(self):
        results = run_conformance()

        self.assertTrue(results)

        phases = {
            item.phase
            for item in results
        }

        self.assertIn(
            "lexical",
            phases,
        )
        self.assertIn(
            "syntax",
            phases,
        )
        self.assertIn(
            "semantic",
            phases,
        )
        self.assertIn(
            "regression",
            phases,
        )

    def test_all_conformance_results_pass(self):
        results = run_conformance()

        failures = [
            result
            for result in results
            if not result.passed
        ]

        self.assertEqual(
            failures,
            [],
        )

    def test_conformance_passes(self):
        self.assertTrue(
            conformance_passes()
        )

    def test_conformance_command(self):
        completed = subprocess.run(
            [
                sys.executable,
                "tools/conformance.py",
            ],
            cwd=".",
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(
            completed.returncode,
            0,
            completed.stderr,
        )

        self.assertIn(
            "VECTIS CONFORMANCE PASSED",
            completed.stdout,
        )


if __name__ == "__main__":
    unittest.main()
