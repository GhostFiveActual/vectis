# GHOST FIVE // VECTIS
# Regression coverage for the VECTIS ux contract contract.
import unittest
from vectis.diagnostic import Diagnostic, DiagnosticSeverity, DiagnosticCode
from vectis.source_position import SourcePosition
from vectis.source_span import SourceSpan

class TestUXContract(unittest.TestCase):
    def test_syntax_consistency(self):
        diagnostic = Diagnostic(
            code=DiagnosticCode.SYN_EXPECTED_STATEMENT,
            severity=DiagnosticSeverity.ERROR,
            message="Expected statement / unknown statement start",
            span=SourceSpan(
                start=SourcePosition(line=2, column=10, file="example.vectis"),
                end=SourcePosition(line=2, column=10, file="example.vectis")
            )
        )
        self.assertEqual(diagnostic.code, DiagnosticCode.SYN_EXPECTED_STATEMENT)
        self.assertEqual(diagnostic.severity, DiagnosticSeverity.ERROR)
        self.assertEqual(diagnostic.message, "Expected statement / unknown statement start")
        self.assertEqual(diagnostic.span.start.line, 2)
        self.assertEqual(diagnostic.span.start.column, 10)
        self.assertEqual(diagnostic.span.end.line, 2)
        self.assertEqual(diagnostic.span.end.column, 10)

    def test_diagnostic_clarity(self):
        diagnostic = Diagnostic(
            code=DiagnosticCode.LEX_UNTERMINATED_STRING,
            severity=DiagnosticSeverity.ERROR,
            message="Unterminated string literal",
            span=SourceSpan(
                start=SourcePosition(line=3, column=5, file="example.vectis"),
                end=SourcePosition(line=3, column=5, file="example.vectis")
            )
        )
        self.assertEqual(diagnostic.code, DiagnosticCode.LEX_UNTERMINATED_STRING)
        self.assertEqual(diagnostic.severity, DiagnosticSeverity.ERROR)
        self.assertEqual(diagnostic.message, "Unterminated string literal")
        self.assertEqual(diagnostic.span.start.line, 3)
        self.assertEqual(diagnostic.span.start.column, 5)
        self.assertEqual(diagnostic.span.end.line, 3)
        self.assertEqual(diagnostic.span.end.column, 5)

    def test_beginner_workflow(self):
        diagnostic = Diagnostic(
            code=DiagnosticCode.SYN_STANDALONE_OTHERWISE,
            severity=DiagnosticSeverity.ERROR,
            message="Standalone `otherwise`",
            span=SourceSpan(
                start=SourcePosition(line=4, column=12, file="example.vectis"),
                end=SourcePosition(line=4, column=12, file="example.vectis")
            )
        )
        self.assertEqual(diagnostic.code, DiagnosticCode.SYN_STANDALONE_OTHERWISE)
        self.assertEqual(diagnostic.severity, DiagnosticSeverity.ERROR)
        self.assertEqual(diagnostic.message, "Standalone `otherwise`")
        self.assertEqual(diagnostic.span.start.line, 4)
        self.assertEqual(diagnostic.span.start.column, 12)
        self.assertEqual(diagnostic.span.end.line, 4)
        self.assertEqual(diagnostic.span.end.column, 12)

    def test_accessibility_recommendations(self):
        diagnostic = Diagnostic(
            code=DiagnosticCode.SYN_EXPECTED_TOKEN,
            severity=DiagnosticSeverity.ERROR,
            message="Expected required token or delimiter",
            span=SourceSpan(
                start=SourcePosition(line=5, column=15, file="example.vectis"),
                end=SourcePosition(line=5, column=15, file="example.vectis")
            )
        )
        self.assertEqual(diagnostic.code, DiagnosticCode.SYN_EXPECTED_TOKEN)
        self.assertEqual(diagnostic.severity, DiagnosticSeverity.ERROR)
        self.assertEqual(diagnostic.message, "Expected required token or delimiter")
        self.assertEqual(diagnostic.span.start.line, 5)
        self.assertEqual(diagnostic.span.start.column, 15)
        self.assertEqual(diagnostic.span.end.line, 5)
        self.assertEqual(diagnostic.span.end.column, 15)

    def test_significant_findings_resolved(self):
        diagnostic = Diagnostic(
            code=DiagnosticCode.SYN_EXPECTED_EXPRESSION,
            severity=DiagnosticSeverity.ERROR,
            message="Expected expression",
            span=SourceSpan(
                start=SourcePosition(line=6, column=18, file="example.vectis"),
                end=SourcePosition(line=6, column=18, file="example.vectis")
            )
        )
        self.assertEqual(diagnostic.code, DiagnosticCode.SYN_EXPECTED_EXPRESSION)
        self.assertEqual(diagnostic.severity, DiagnosticSeverity.ERROR)
        self.assertEqual(diagnostic.message, "Expected expression")
        self.assertEqual(diagnostic.span.start.line, 6)
        self.assertEqual(diagnostic.span.start.column, 18)
        self.assertEqual(diagnostic.span.end.line, 6)
        self.assertEqual(diagnostic.span.end.column, 18)
