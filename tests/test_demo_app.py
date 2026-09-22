# GHOST FIVE // VECTIS
# Regression coverage for the VECTIS Launch Control application.

from __future__ import annotations

from importlib.resources import files
import unittest

from vectis.demo_app import (
    build_readiness_source,
    readiness_report_html,
    run_readiness,
)


class DemoApplicationTests(unittest.TestCase):
    """Verify that Launch Control is backed by the VECTIS compiler and runtime."""

    def test_assets_are_packaged(self):
        root = files("vectis").joinpath("demo_assets")
        for name in ("index.html", "styles.css", "app.js"):
            with self.subTest(name=name):
                self.assertTrue(root.joinpath(name).is_file())

    def test_authorized_mission_runs_through_vectis(self):
        result = run_readiness(
            mission="Orbital demonstration flight",
            operator="Flight Director",
            ready=True,
            quality=94,
            risk=22,
        )

        self.assertEqual(result["diagnostics"], [])
        self.assertIsNotNone(result["graph"])
        self.assertTrue(result["runtime"]["success"])
        self.assertTrue(result["timeline"])
        self.assertEqual(result["timeline"][0]["level"], 0)
        self.assertGreater(result["summary"]["stage_count"], 1)
        self.assertEqual(len(result["summary"]["fingerprint"]), 64)
        self.assertGreater(result["summary"]["nodes"], 20)
        self.assertGreater(result["summary"]["levels"], 3)
        self.assertEqual(result["summary"]["stage_count"], 5)
        self.assertEqual(
            result["summary"]["stages"],
            [
                "Telemetry",
                "Gate computation",
                "Input invariants",
                "Gate results",
                "Launch decision",
            ],
        )

        values = dict(result["runtime"]["node_values"])
        self.assertTrue(values["launch_authorized"])
        self.assertEqual(values["launch_status"], "GO")
        self.assertGreater(values["readiness_score"], 80)

    def test_review_path_runs_through_vectis(self):
        result = run_readiness(
            mission="Production release",
            operator="Release Operator",
            ready=True,
            quality=71,
            risk=22,
        )

        self.assertTrue(result["runtime"]["success"])
        values = dict(result["runtime"]["node_values"])
        self.assertFalse(values["launch_authorized"])
        self.assertEqual(values["launch_status"], "HOLD")

    def test_individual_gate_can_hold_launch(self):
        result = run_readiness(
            mission="Orbital demonstration flight",
            operator="Flight Director",
            ready=True,
            quality=96,
            risk=18,
            navigation_ready=False,
        )

        values = dict(result["runtime"]["node_values"])
        self.assertFalse(values["systems_gate"])
        self.assertFalse(values["launch_authorized"])
        self.assertEqual(values["launch_status"], "HOLD")

    def test_proof_report_uses_real_execution_trace(self):
        report = readiness_report_html(
            mission="Orbital demonstration flight",
            operator="Flight Director",
            ready=True,
            quality=96,
            risk=18,
            navigation_ready=True,
            communications_ready=True,
            range_clear=True,
            payload_ready=True,
            fuel_percent=97,
            weather_score=92,
            vehicle="VECTIS-01",
        )

        self.assertIn("GHOST FIVE // VECTIS", report)
        self.assertIn("Execution Trace", report)
        self.assertIn("Plan Fingerprint", report)
        self.assertIn("VECTIS-01", report)

    def test_demo_exposes_proof_report_control(self):
        root = files("vectis").joinpath("demo_assets")
        html = root.joinpath("index.html").read_text(encoding="utf-8")
        app = root.joinpath("app.js").read_text(encoding="utf-8")

        self.assertIn('id="export-report"', html)
        self.assertIn("/api/report", app)

    def test_scores_are_bounded(self):
        with self.assertRaises(ValueError):
            build_readiness_source(
                mission="Mission",
                operator="Operator",
                ready=True,
                quality=101,
                risk=20,
            )


if __name__ == "__main__":
    unittest.main()
