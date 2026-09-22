# GHOST FIVE // VECTIS
# Regression coverage for the VECTIS source span contract.
from unittest import TestCase

from vectis.source_position import SourcePosition
from vectis.source_span import SourceSpan


class TestSourceSpan(TestCase):
    def position(
        self,
        line,
        column,
        file="example.vectis",
    ):
        return SourcePosition(
            line=line,
            column=column,
            file=file,
        )

    def test_creation_and_file(self):
        start = self.position(2, 3)
        end = self.position(2, 9)

        span = SourceSpan(
            start=start,
            end=end,
        )

        self.assertEqual(span.start, start)
        self.assertEqual(span.end, end)
        self.assertEqual(span.file, "example.vectis")

    def test_zero_width_span_is_valid(self):
        position = self.position(4, 5)

        span = SourceSpan(
            start=position,
            end=position,
        )

        self.assertEqual(span.start, span.end)

    def test_cross_file_span_is_invalid(self):
        with self.assertRaises(ValueError):
            SourceSpan(
                start=self.position(
                    1,
                    1,
                    "a.vectis",
                ),
                end=self.position(
                    1,
                    2,
                    "b.vectis",
                ),
            )

    def test_reversed_line_span_is_invalid(self):
        with self.assertRaises(ValueError):
            SourceSpan(
                start=self.position(2, 1),
                end=self.position(1, 9),
            )

    def test_reversed_column_span_is_invalid(self):
        with self.assertRaises(ValueError):
            SourceSpan(
                start=self.position(1, 9),
                end=self.position(1, 3),
            )

    def test_requires_source_positions(self):
        with self.assertRaises(ValueError):
            SourceSpan(
                start=None,
                end=self.position(1, 2),
            )
