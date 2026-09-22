# GHOST FIVE // VECTIS
# Regression coverage for the VECTIS token contract.
from unittest import TestCase

from vectis.source_position import SourcePosition
from vectis.source_span import SourceSpan
from vectis.token import Token


class TestToken(TestCase):
    def span(self):
        return SourceSpan(
            start=SourcePosition(
                line=1,
                column=1,
                file="example.vectis",
            ),
            end=SourcePosition(
                line=1,
                column=7,
                file="example.vectis",
            ),
        )

    def test_creation(self):
        span = self.span()

        token = Token(
            type="identifier",
            value="mission",
            span=span,
        )

        self.assertEqual(
            token.type,
            "identifier",
        )
        self.assertEqual(
            token.value,
            "mission",
        )
        self.assertIs(
            token.span,
            span,
        )

    def test_uses_canonical_source_span(self):
        token = Token(
            type="identifier",
            value="name",
            span=self.span(),
        )

        self.assertIsInstance(
            token.span,
            SourceSpan,
        )
        self.assertIsInstance(
            token.span.start,
            SourcePosition,
        )

    def test_empty_value_is_allowed(self):
        token = Token(
            type="eof",
            value="",
            span=self.span(),
        )

        self.assertEqual(
            token.value,
            "",
        )

    def test_empty_type_is_invalid(self):
        with self.assertRaises(ValueError):
            Token(
                type="",
                value="value",
                span=self.span(),
            )

    def test_span_must_be_source_span(self):
        with self.assertRaises(ValueError):
            Token(
                type="identifier",
                value="name",
                span=None,
            )
