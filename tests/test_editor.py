# GHOST FIVE // VECTIS
# Verifies reusable editor intelligence for LSP and future editor integrations.
from __future__ import annotations

import unittest

from vectis.editor import completion_items, document_symbols, hover_info


class EditorIntelligenceTests(unittest.TestCase):
    def test_completion_items_are_stable_and_registry_backed(self) -> None:
        items = completion_items()
        labels = [item["label"] for item in items]

        self.assertEqual(labels, sorted(labels))
        self.assertIn("mission", labels)
        self.assertIn("concat", labels)
        self.assertIn("http.request", labels)

    def test_hover_describes_keyword_builtin_and_action(self) -> None:
        keyword = hover_info("mission", line=0, character=2)
        builtin = hover_info("concat(value)", line=0, character=2)
        action = hover_info(
            "http.request",
            line=0,
            character=4,
        )

        self.assertIn("VECTIS keyword", keyword["contents"]["value"])
        self.assertIn("Pure and deterministic", builtin["contents"]["value"])
        self.assertIn("capability **http**", action["contents"]["value"])

    def test_document_symbols_preserve_language_structure(self) -> None:
        source = """function ready(score) {
    return score >= 90;
}

mission "Release" {
    stage "Inputs" {
        source quality 96;
    }
    let approved ready(quality);
    action receipt "http.request" using "http" {
        method: "GET",
        url: "https://example.invalid"
    };
    publish approved;
}
"""
        symbols = document_symbols(
            source,
            file="release.vectis",
        )

        self.assertEqual(
            [item["name"] for item in symbols],
            ["ready", "Release"],
        )
        mission = symbols[1]
        self.assertEqual(
            [item["name"] for item in mission["children"]],
            ["Inputs", "approved", "receipt"],
        )
        self.assertEqual(
            mission["children"][0]["children"][0]["name"],
            "quality",
        )


if __name__ == "__main__":
    unittest.main()
