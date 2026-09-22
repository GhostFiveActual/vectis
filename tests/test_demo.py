# GHOST FIVE // VECTIS
# Regression coverage for the VECTIS demo contract.
from __future__ import annotations

import importlib.util
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import unittest

from vectis.compiler import compile_program
from vectis.parser import parse


ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "demo" / "demo.vectis"
RUNNER = ROOT / "examples" / "demo" / "run_demo.py"
DOC = ROOT / "docs" / "demo.md"


def _source() -> str:
    return DEMO.read_text(encoding="utf-8")


def _load_runner():
    spec = importlib.util.spec_from_file_location(
        "vectis_demo_runner",
        RUNNER,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load demo runner")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestDemo(unittest.TestCase):
    def test_required_demo_artifacts_exist(self):
        for path in (DEMO, RUNNER, DOC):
            with self.subTest(path=path):
                self.assertTrue(path.is_file())
                self.assertGreater(path.stat().st_size, 0)

    def test_demo_is_raw_canonical_vectis(self):
        source = _source()

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

    def test_demo_parses_to_program(self):
        program = parse(
            _source(),
            file=str(DEMO),
        )

        self.assertEqual(
            type(program).__name__,
            "Program",
        )

    def test_demo_compiles_without_diagnostics(self):
        program = parse(
            _source(),
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

    def test_demo_compilation_is_deterministic(self):
        source = _source()

        result_a = compile_program(
            parse(
                source,
                file=str(DEMO),
            )
        )
        result_b = compile_program(
            parse(
                source,
                file=str(DEMO),
            )
        )

        self.assertEqual(
            result_a.diagnostics,
            result_b.diagnostics,
        )
        self.assertEqual(
            result_a.graph.to_json(),
            result_b.graph.to_json(),
        )

    def test_demo_contains_explicit_branch_paths(self):
        source = _source()

        self.assertIn(
            "when ready",
            source,
        )
        self.assertIn(
            "otherwise",
            source,
        )
        self.assertIn(
            "publish result;",
            source,
        )
        self.assertIn(
            'request "review";',
            source,
        )

    def test_runner_uses_canonical_demo_path(self):
        runner = _load_runner()

        self.assertEqual(
            runner.DEMO_PATH.resolve(),
            DEMO.resolve(),
        )
        self.assertEqual(
            runner.load_demo(),
            _source(),
        )

    def test_runner_compiles_and_renders_graph(self):
        runner = _load_runner()

        result = runner.compile_demo()
        rendered = runner.render_graph()

        self.assertEqual(
            result.diagnostics,
            (),
        )
        self.assertIsNotNone(
            result.graph,
        )

        decoded = json.loads(rendered)
        self.assertIsInstance(
            decoded,
            dict,
        )

    def test_runner_main_succeeds_with_json_output(self):
        runner = _load_runner()

        output = io.StringIO()

        with redirect_stdout(output):
            rc = runner.main([])

        self.assertEqual(
            rc,
            0,
        )

        decoded = json.loads(
            output.getvalue()
        )

        self.assertIsInstance(
            decoded,
            dict,
        )

    def test_documentation_contains_contract_terms(self):
        text = DOC.read_text(
            encoding="utf-8"
        ).lower()

        for term in (
            "demo",
            "language",
            "compiler",
            "runtime",
            "diagnostic",
        ):
            with self.subTest(term=term):
                self.assertIn(
                    term,
                    text,
                )


if __name__ == "__main__":
    unittest.main()
