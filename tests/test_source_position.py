# GHOST FIVE // VECTIS
# Regression coverage for the VECTIS source position contract.
from unittest import TestCase

from vectis.source_position import SourcePosition


class TestSourcePosition(TestCase):
    def test_creation(self):
        position = SourcePosition(
            line=3,
            column=7,
            file="example.vectis",
        )

        self.assertEqual(position.line, 3)
        self.assertEqual(position.column, 7)
        self.assertEqual(position.file, "example.vectis")

    def test_line_is_one_based(self):
        with self.assertRaises(ValueError):
            SourcePosition(
                line=0,
                column=1,
                file="example.vectis",
            )

    def test_column_is_one_based(self):
        with self.assertRaises(ValueError):
            SourcePosition(
                line=1,
                column=0,
                file="example.vectis",
            )

    def test_file_must_not_be_empty(self):
        with self.assertRaises(ValueError):
            SourcePosition(
                line=1,
                column=1,
                file="",
            )

    def test_position_is_immutable(self):
        position = SourcePosition(
            line=1,
            column=1,
            file="example.vectis",
        )

        with self.assertRaises(AttributeError):
            position.line = 2
