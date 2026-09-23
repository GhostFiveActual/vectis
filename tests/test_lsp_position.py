# GHOST FIVE // VECTIS
# Verifies one shared UTF-16 coordinate contract for all LSP editor surfaces.
from __future__ import annotations

import unittest

from vectis.lsp_position import (
    contains_lsp_position,
    lsp_character_to_index,
    lsp_position_to_offset,
    source_position_to_lsp,
    source_span_to_lsp_range,
    utf16_units,
)
from vectis.source_position import SourcePosition
from vectis.source_span import SourceSpan


class LspPositionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = "😀ready\n"
        self.span = SourceSpan(
            start=SourcePosition(
                line=1,
                column=2,
                file="unicode.vectis",
            ),
            end=SourcePosition(
                line=1,
                column=6,
                file="unicode.vectis",
            ),
        )

    def test_utf16_units_count_non_bmp_text(self) -> None:
        self.assertEqual(utf16_units("😀"), 2)
        self.assertEqual(utf16_units("😀ready"), 7)

    def test_source_position_and_span_use_utf16(self) -> None:
        self.assertEqual(
            source_position_to_lsp(self.source, self.span.start),
            {"line": 0, "character": 2},
        )
        self.assertEqual(
            source_span_to_lsp_range(self.source, self.span),
            {
                "start": {"line": 0, "character": 2},
                "end": {"line": 0, "character": 7},
            },
        )

    def test_lsp_character_converts_back_to_python_index(self) -> None:
        self.assertEqual(lsp_character_to_index("😀ready", 2), 1)
        self.assertEqual(lsp_character_to_index("😀ready", 4), 3)
        self.assertEqual(lsp_character_to_index("😀ready", 1), 0)
        self.assertEqual(
            lsp_position_to_offset(self.source, 0, 4),
            3,
        )

    def test_contains_position_uses_end_exclusive_lsp_range(self) -> None:
        self.assertTrue(
            contains_lsp_position(
                self.source,
                self.span,
                line=0,
                character=4,
            )
        )
        self.assertFalse(
            contains_lsp_position(
                self.source,
                self.span,
                line=0,
                character=7,
            )
        )


if __name__ == "__main__":
    unittest.main()
