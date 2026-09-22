# GHOST FIVE // VECTIS
# Regression coverage for the VECTIS semantic contract.
import unittest
from vectis.ast import (
    SourceDeclaration,
    StringLiteral,
    PublishStatement,
    RequestStatement,
    RequireStatement,
    Block,
    WhenStatement,
    BooleanLiteral,
)
from vectis.diagnostic import DiagnosticCode, error_diagnostic
from vectis.source_position import SourcePosition
from vectis.semantic import SemanticAnalyzer, Program
from vectis.source_span import SourceSpan  # Import SourceSpan from vectis.source_span


class TestSemanticAnalyzer(unittest.TestCase):
    def test_publish_statement(self):
        publish = PublishStatement(
            value=StringLiteral(
                value="output",
                span=SourceSpan(
                    start=SourcePosition(line=1, column=1, file="test"),
                    end=SourcePosition(line=1, column=12, file="test"),
                ),
            ),
            span=SourceSpan(
                start=SourcePosition(line=1, column=1, file="test"),
                end=SourcePosition(line=1, column=12, file="test"),
            ),
        )
        program = Program(statements=(publish,), span=SourceSpan(
            start=SourcePosition(line=1, column=1, file="test"),
            end=SourcePosition(line=1, column=12, file="test"),
        ))
        analyzer = SemanticAnalyzer(program)
        diagnostics = analyzer.analyze()
        self.assertEqual(len(diagnostics), 0)  # Ensure diagnostics is empty

    def test_request_statement(self):
        request = RequestStatement(
            capability=StringLiteral(
                value="database",
                span=SourceSpan(
                    start=SourcePosition(line=1, column=1, file="test"),
                    end=SourcePosition(line=1, column=12, file="test"),
                ),
            ),
            span=SourceSpan(
                start=SourcePosition(line=1, column=1, file="test"),
                end=SourcePosition(line=1, column=12, file="test"),
            ),
        )
        program = Program(statements=(request,), span=SourceSpan(
            start=SourcePosition(line=1, column=1, file="test"),
            end=SourcePosition(line=1, column=12, file="test"),
        ))
        analyzer = SemanticAnalyzer(program)
        diagnostics = analyzer.analyze()
        self.assertEqual(len(diagnostics), 0)  # Ensure diagnostics is empty

    def test_require_statement(self):
        require = RequireStatement(
            capability=StringLiteral(
                value="network",
                span=SourceSpan(
                    start=SourcePosition(line=1, column=1, file="test"),
                    end=SourcePosition(line=1, column=12, file="test"),
                ),
            ),
            span=SourceSpan(
                start=SourcePosition(line=1, column=1, file="test"),
                end=SourcePosition(line=1, column=12, file="test"),
            ),
        )
        program = Program(statements=(require,), span=SourceSpan(
            start=SourcePosition(line=1, column=1, file="test"),
            end=SourcePosition(line=1, column=12, file="test"),
        ))
        analyzer = SemanticAnalyzer(program)
        diagnostics = analyzer.analyze()
        self.assertEqual(len(diagnostics), 0)  # Ensure diagnostics is empty

    def test_source_declaration(self):
        source = SourceDeclaration(
            name="data",
            value=StringLiteral(
                value="example",
                span=SourceSpan(
                    start=SourcePosition(line=1, column=1, file="test"),
                    end=SourcePosition(line=1, column=12, file="test"),
                ),
            ),
            span=SourceSpan(
                start=SourcePosition(line=1, column=1, file="test"),
                end=SourcePosition(line=1, column=12, file="test"),
            ),
        )
        program = Program(statements=(source,), span=SourceSpan(
            start=SourcePosition(line=1, column=1, file="test"),
            end=SourcePosition(line=1, column=12, file="test"),
        ))
        analyzer = SemanticAnalyzer(program)
        diagnostics = analyzer.analyze()
        self.assertEqual(len(diagnostics), 0)  # Ensure diagnostics is empty

    def test_when_statement(self):
        condition = BooleanLiteral(
            value=True,
            span=SourceSpan(
                start=SourcePosition(line=1, column=1, file="test"),
                end=SourcePosition(line=1, column=12, file="test"),
            ),
        )
        block = Block(
            statements=(),
            span=SourceSpan(
                start=SourcePosition(line=1, column=1, file="test"),
                end=SourcePosition(line=1, column=12, file="test"),
            ),
        )
        when = WhenStatement(
            condition=condition,
            body=block,
            span=SourceSpan(
                start=SourcePosition(line=1, column=1, file="test"),
                end=SourcePosition(line=1, column=12, file="test"),
            ),
        )
        program = Program(statements=(when,), span=SourceSpan(
            start=SourcePosition(line=1, column=1, file="test"),
            end=SourcePosition(line=1, column=12, file="test"),
        ))
        analyzer = SemanticAnalyzer(program)
        diagnostics = analyzer.analyze()
        self.assertEqual(len(diagnostics), 0)  # Ensure diagnostics is empty



    def test_public_value_type_contract_symbol(self):
        import vectis.semantic as semantic

        self.assertTrue(
            hasattr(
                semantic,
                "ValueType",
            )
        )

        self.assertIsNotNone(
            semantic.ValueType
        )

    def test_public_semantic_result_contract_symbol(self):
        import vectis.semantic as semantic

        self.assertTrue(
            hasattr(
                semantic,
                "SemanticResult",
            )
        )

        self.assertIsNotNone(
            semantic.SemanticResult
        )

    def test_public_analyze_contract_symbol_is_callable(self):
        import vectis.semantic as semantic

        self.assertTrue(
            hasattr(
                semantic,
                "analyze",
            )
        )

        self.assertTrue(
            callable(
                semantic.analyze
            )
        )

    def test_public_analyze_is_deterministic_for_empty_program(self):
        import vectis.semantic as semantic
        from vectis.ast import Program
        from vectis.source_position import SourcePosition
        from vectis.source_span import SourceSpan

        position = SourcePosition(
            line=1,
            column=1,
            file="semantic-contract.vectis",
        )

        span = SourceSpan(
            start=position,
            end=position,
        )

        program = Program(
            statements=(),
            span=span,
        )

        first = semantic.analyze(
            program
        )

        second = semantic.analyze(
            program
        )

        self.assertEqual(
            first,
            second,
        )


if __name__ == "__main__":
    unittest.main()
