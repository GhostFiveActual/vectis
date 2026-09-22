# GHOST FIVE // VECTIS
# Regression coverage for the VECTIS studio contract.
from __future__ import annotations

from importlib.resources import files
import re
import unittest

from vectis.studio import _compile_payload, run_studio


class StudioTests(unittest.TestCase):
    def test_packaged_assets_exist(self):
        root = files("vectis").joinpath("studio_assets")
        for name in ("index.html", "styles.css", "app.js"):
            target = root.joinpath(name)
            with self.subTest(name=name):
                self.assertTrue(target.is_file())
                self.assertGreater(len(target.read_bytes()), 0)

    def test_ui_has_core_product_controls(self):
        root = files("vectis").joinpath("studio_assets")
        html = root.joinpath("index.html").read_text(encoding="utf-8")
        for marker in (
            "VECTIS <span>Mission Control</span>",
            'id="source"',
            'id="run-button"',
            'id="check-button"',
            'id="plan-button"',
            'id="graph-canvas"',
            'id="function-grid"',
            "A language for turning what you intend to happen into a system that can prove how it will happen.",
        ):
            self.assertIn(marker, html)

    def test_ui_avoids_dynamic_javascript_execution(self):
        root = files("vectis").joinpath("studio_assets")
        app = root.joinpath("app.js").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"\beval\s*\(", app))
        self.assertNotIn("new Function", app)
        self.assertNotIn(".innerHTML", app)

    def test_compile_payload_exposes_graph_and_runtime_values(self):
        source = '''mission "Studio" {
    source score 90;
    let pass score >= 80;
    when pass { publish upper("ok"); }
}
'''
        payload = _compile_payload(source, execute=True)
        self.assertIsNotNone(payload["executionGraph"])
        self.assertTrue(payload["runtime"]["success"])
        values = dict(payload["runtime"]["node_values"])
        self.assertEqual(values["pass"], True)
        self.assertEqual(values["publish:0001"], "OK")

    def test_remote_binding_requires_explicit_opt_in(self):
        with self.assertRaises(ValueError):
            run_studio(
                host="0.0.0.0",
                port=0,
                open_browser=False,
                allow_remote=False,
            )


if __name__ == "__main__":
    unittest.main()
