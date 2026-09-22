# GHOST FIVE // VECTIS
# Regression coverage for the VECTIS runtime compiler integration contract.
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]


def run_vectis(source: str) -> dict:
    with tempfile.TemporaryDirectory() as temporary:
        program = Path(temporary) / "condition.vectis"
        program.write_text(
            textwrap.dedent(source).strip() + "\n",
            encoding="utf-8",
        )

        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT / "src")

        process = subprocess.run(
            [
                sys.executable,
                "-m",
                "vectis.cli",
                "run",
                str(program),
            ],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        if process.returncode != 0:
            raise AssertionError(
                "vectis run command exited nonzero\n"
                f"stdout:\n{process.stdout}\n"
                f"stderr:\n{process.stderr}"
            )

        try:
            return json.loads(process.stdout)
        except json.JSONDecodeError as exc:
            raise AssertionError(
                "vectis run did not emit JSON\n"
                f"stdout:\n{process.stdout}\n"
                f"stderr:\n{process.stderr}"
            ) from exc


class RuntimeCompilerIntegrationTests(unittest.TestCase):
    def test_true_source_reference_selects_true_branch(self):
        result = run_vectis(
            """
            mission "true reference" {
                source ready true;
                source result "TRUE BRANCH";

                when ready {
                    publish result;
                }
            }
            """
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["failures"], [])

        states = dict(result["node_states"])

        self.assertEqual(
            states["condition:0001"],
            "succeeded",
        )
        self.assertEqual(
            states["publish:0001"],
            "succeeded",
        )

    def test_false_source_reference_skips_true_branch(self):
        result = run_vectis(
            """
            mission "false reference" {
                source ready false;
                source result "FALSE BRANCH";

                when ready {
                    publish result;
                }
            }
            """
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["failures"], [])

        states = dict(result["node_states"])

        self.assertEqual(
            states["condition:0001"],
            "succeeded",
        )
        self.assertEqual(
            states["publish:0001"],
            "skipped",
        )


    def test_structured_values_flow_through_runtime(self):
        result = run_vectis(
            """
            mission "structured state" {
                source build object(
                    "passed", true,
                    "coverage", 94,
                    "checks", list(true, true, true)
                );
                let approved get(build, "passed")
                    && get(build, "coverage") >= 90
                    && all(get(build, "checks"));
                assert approved, "Build readiness requirements were not met";
                publish object(
                    "status", if_else(approved, "AUTHORIZED", "REVIEW"),
                    "coverage", get(build, "coverage"),
                    "check_count", size(get(build, "checks"))
                );
            }
            """
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["failures"], [])
        values = dict(result["node_values"])
        self.assertEqual(
            values["build"],
            {
                "passed": True,
                "coverage": 94,
                "checks": [True, True, True],
            },
        )
        self.assertEqual(
            values["publish:0001"],
            {
                "status": "AUTHORIZED",
                "coverage": 94,
                "check_count": 3,
            },
        )


if __name__ == "__main__":
    unittest.main()
