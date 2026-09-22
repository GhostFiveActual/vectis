# GHOST FIVE // VECTIS
# Regression coverage for the VECTIS diagnostic contract.
import json
import unittest

from vectis.diagnostic import (
    Diagnostic,
    DiagnosticCode,
    DiagnosticError,
    DiagnosticSeverity,
    error_diagnostic,
    point_span,
)
from vectis.lexer import Lexer, LexerError
from vectis.parser import ParserError, parse
from vectis.source_position import SourcePosition
from vectis.source_span import SourceSpan


class DiagnosticTests(unittest.TestCase):
    def make_span(self):
        return SourceSpan(
            start=SourcePosition(
                line=2,
                column=3,
                file="test.vectis",
            ),
            end=SourcePosition(
                line=2,
                column=8,
                file="test.vectis",
            ),
        )

    def test_stable_code_registry(self):
        self.assertEqual(
            {code.value for code in DiagnosticCode},
            {
                "LEX001",
                "LEX002",
                "LEX003",
                "SYN001",
                "SYN002",
                "SYN003",
                "SYN004",
                "SYN005",
                "SYN006",
                "SYN007",
                "SEM001",
                "SEM002",
                "SEM003",
                "SEM004",
                "SEM005",
                "SEM006",
                "CAP001",
                "CAP002",
            },
        )

    def test_severity_registry(self):
        self.assertEqual(
            {severity.value for severity in DiagnosticSeverity},
            {"error", "warning"},
        )

    def test_machine_readable_diagnostic(self):
        diagnostic = Diagnostic(
            code=DiagnosticCode.SYN_EXPECTED_TOKEN,
            severity=DiagnosticSeverity.ERROR,
            message="expected ';'",
            span=self.make_span(),
        )

        payload = diagnostic.to_dict()
        json.dumps(payload)

        self.assertEqual(payload["code"], "SYN003")
        self.assertEqual(payload["severity"], "error")
        self.assertEqual(payload["source"]["file"], "test.vectis")
        self.assertEqual(
            payload["source"]["start"],
            {"line": 2, "column": 3},
        )
        self.assertEqual(
            payload["source"]["end"],
            {"line": 2, "column": 8},
        )

    def test_warning_is_supported(self):
        diagnostic = Diagnostic(
            code=DiagnosticCode.SYN_EXPECTED_TOKEN,
            severity=DiagnosticSeverity.WARNING,
            message="example warning",
            span=self.make_span(),
        )
        self.assertEqual(
            diagnostic.severity,
            DiagnosticSeverity.WARNING,
        )

    def test_error_compatibility_fields(self):
        diagnostic = error_diagnostic(
            code=DiagnosticCode.SYN_EXPECTED_TOKEN,
            message="expected ';'",
            span=self.make_span(),
        )
        error = DiagnosticError(diagnostic)

        self.assertEqual(error.code, "SYN003")
        self.assertEqual(error.severity, "error")
        self.assertEqual(error.file, "test.vectis")
        self.assertEqual(error.line, 2)
        self.assertEqual(error.column, 3)
        self.assertIs(error.span, diagnostic.span)
        self.assertEqual(error.to_dict(), diagnostic.to_dict())
        self.assertIn("test.vectis:2:3:", str(error))

    def test_point_span(self):
        span = point_span(
            file="point.vectis",
            line=4,
            column=9,
        )
        self.assertEqual(span.start, span.end)
        self.assertEqual(span.file, "point.vectis")

    def test_lexer_codes(self):
        cases = (
            ('"unterminated', "LEX001"),
            ("=", "LEX002"),
            ("@", "LEX003"),
        )

        for source, expected in cases:
            with self.subTest(source=source):
                with self.assertRaises(LexerError) as caught:
                    Lexer(
                        source,
                        file="lex.vectis",
                    ).tokenize()

                error = caught.exception
                self.assertEqual(error.code, expected)
                self.assertEqual(error.severity, "error")
                self.assertIsInstance(error.span, SourceSpan)

    def test_parser_codes(self):
        cases = (
            ("otherwise { publish result; }", "SYN002"),
            ("publish ;", "SYN004"),
            ("publish result", "SYN003"),
            ('mission "x" { publish result;', "SYN005"),
            ("citations [a,];", "SYN006"),
            ("not_a_statement", "SYN001"),
        )

        for source, expected in cases:
            with self.subTest(source=source):
                with self.assertRaises(ParserError) as caught:
                    parse(
                        source,
                        file="parse.vectis",
                    )

                error = caught.exception
                self.assertEqual(error.code, expected)
                self.assertEqual(error.severity, "error")
                self.assertIsInstance(error.span, SourceSpan)


if __name__ == "__main__":
    unittest.main()
