# GHOST FIVE // VECTIS
# Regression coverage for the VECTIS release candidate contract.
from __future__ import annotations

from pathlib import Path
import unittest

from vectis.compiler import compile_program
from vectis.parser import parse


ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "demo" / "demo.vectis"
RELEASE = ROOT / "docs" / "release" / "RELEASE.md"
STUDIO = ROOT / "src" / "vectis" / "studio_assets" / "index.html"


def _demo_source() -> str:
    return DEMO.read_text(encoding="utf-8")


class TestReleaseCandidate(unittest.TestCase):
    def test_release_document_exists_and_is_nonempty(self):
        self.assertTrue(RELEASE.is_file())
        self.assertGreater(RELEASE.stat().st_size, 0)

    def test_release_document_is_valid_utf8_text(self):
        text = RELEASE.read_text(encoding="utf-8")
        self.assertTrue(text.strip())
        self.assertNotIn("\x00", text)

    def test_canonical_demo_exists(self):
        self.assertTrue(DEMO.is_file())
        self.assertGreater(DEMO.stat().st_size, 0)

    def test_parse_program(self):
        program = parse(
            _demo_source(),
            file=str(DEMO),
        )

        self.assertEqual(
            type(program).__name__,
            "Program",
        )

    def test_compile_program(self):
        program = parse(
            _demo_source(),
            file=str(DEMO),
        )
        result = compile_program(program)

        self.assertEqual(
            result.diagnostics,
            (),
        )
        self.assertIsNotNone(
            result.graph,
        )

    def test_compilation_is_deterministic(self):
        source = _demo_source()

        first = compile_program(
            parse(source, file=str(DEMO))
        )
        second = compile_program(
            parse(source, file=str(DEMO))
        )

        self.assertEqual(
            first.diagnostics,
            second.diagnostics,
        )
        self.assertEqual(
            first.graph.to_json(),
            second.graph.to_json(),
        )

    def test_studio_surface_is_packaged(self):
        self.assertTrue(STUDIO.is_file())
        self.assertGreater(STUDIO.stat().st_size, 0)

    def test_demo_uses_current_language_syntax(self):
        source = _demo_source()

        self.assertNotIn("```", source)
        self.assertFalse(
            any(
                line.lstrip().startswith("#")
                for line in source.splitlines()
            )
        )
        self.assertIn(
            'mission "VECTIS submission demo"',
            source,
        )


if __name__ == "__main__":
    unittest.main()
