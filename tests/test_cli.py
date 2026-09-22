# GHOST FIVE // VECTIS
# Regression coverage for the VECTIS cli contract.
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from vectis import __version__
from vectis.cli import build_parser, main


class CliTests(unittest.TestCase):
    def invoke(
        self,
        argv: list[str],
        *,
        stdin: str = "",
    ) -> tuple[int, str, str]:
        stdout = StringIO()
        stderr = StringIO()

        with (
            patch.object(
                sys,
                "stdin",
                StringIO(stdin),
            ),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            try:
                code = main(argv)
            except SystemExit as exc:
                code = int(exc.code or 0)

        return (
            int(code),
            stdout.getvalue(),
            stderr.getvalue(),
        )

    def source_file(
        self,
        text: str,
    ):
        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".vectis",
            delete=False,
        )

        tmp.write(text)
        tmp.close()

        self.addCleanup(
            lambda: Path(tmp.name).unlink(
                missing_ok=True
            )
        )

        return tmp.name

    def test_help_lists_all_toolchain_commands(self):
        help_text = build_parser().format_help()

        for command in (
            "check",
            "tokens",
            "parse",
            "plan",
            "inspect",
            "run",
            "mission",
            "audit",
            "fingerprint",
            "verify",
            "limits",
            "timeline",
            "report",
            "fmt",
            "builtins",
            "capabilities",
            "actions",
            "doctor",
            "lsp",
            "studio",
            "app",
        ):
            self.assertIn(command, help_text)

    def test_main_without_command_prints_help(self):
        code, stdout, stderr = self.invoke([])

        self.assertEqual(code, 0)
        self.assertIn(
            "VECTIS deterministic automation language",
            stdout,
        )
        self.assertEqual(stderr, "")

    def test_version_is_exposed(self):
        code, stdout, stderr = self.invoke(
            ["--version"]
        )

        self.assertEqual(code, 0)
        self.assertIn(__version__, stdout)
        self.assertEqual(stderr, "")

    def test_check_accepts_valid_empty_program(self):
        source = self.source_file("")

        code, stdout, stderr = self.invoke(
            ["check", source]
        )

        self.assertEqual(code, 0)
        self.assertEqual(stdout.strip(), "OK")
        self.assertEqual(stderr, "")

    def test_check_details_reports_plan_metrics(self):
        source = self.source_file(
            'mission "Details" { source ready true; when ready { publish "GO"; } }'
        )

        code, stdout, stderr = self.invoke(
            ["check", "--details", source]
        )

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["status"], "ok")
        self.assertGreaterEqual(payload["summary"]["nodes"], 3)
        self.assertGreaterEqual(payload["summary"]["levels"], 2)
        self.assertEqual(len(payload["summary"]["fingerprint"]), 64)

    def test_audit_reports_plan_proof(self):
        source = self.source_file(
            '''mission "Audit" {
    stage "Inputs" {
        source ready true;
    }
    stage "Authority" {
        require "filesystem";
    }
    stage "Decision" {
        when ready {
            publish "AUTHORIZED";
        }
    }
}
'''
        )

        code, stdout, stderr = self.invoke(
            ["audit", "--json", source]
        )

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        audit = payload["audit"]
        self.assertEqual(len(audit["fingerprint"]), 64)
        self.assertEqual(audit["summary"]["stage_count"], 3)
        self.assertEqual(
            audit["capabilities"]["required"],
            ["filesystem"],
        )
        self.assertEqual(
            [stage["name"] for stage in audit["stages"]],
            ["Inputs", "Authority", "Decision"],
        )

    def test_fingerprint_is_stable(self):
        source = self.source_file(
            'mission "Fingerprint" { source ready true; publish ready; }'
        )

        first = self.invoke(["fingerprint", source])
        second = self.invoke(["fingerprint", source])

        self.assertEqual(first[0], 0)
        self.assertEqual(first[1], second[1])
        self.assertEqual(len(first[1].strip()), 64)

    def test_verify_proves_repeated_plan_and_schedule_stability(self):
        source = self.source_file(
            'mission "Verify" { source ready true; let approved ready; publish approved; }'
        )

        code, stdout, stderr = self.invoke(
            ["verify", source, "--runs", "4"]
        )

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertTrue(payload["deterministic"])
        self.assertTrue(payload["fingerprint_stable"])
        self.assertTrue(payload["dry_run_schedule_stable"])
        self.assertEqual(payload["runs"], 4)
        self.assertEqual(len(payload["fingerprint"]), 64)

    def test_diff_compares_plan_identity_and_shape(self):
        left = self.source_file(
            'mission "Left" { source ready true; publish ready; }'
        )
        same = self.source_file(
            'mission "Left" { source ready true; publish ready; }'
        )
        changed = self.source_file(
            'mission "Right" { source ready true; let status if_else(ready, "GO", "HOLD"); publish status; }'
        )

        code, stdout, stderr = self.invoke(
            ["diff", left, same]
        )
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertTrue(json.loads(stdout)["same"])

        code, stdout, stderr = self.invoke(
            ["diff", left, changed]
        )
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertFalse(payload["same"])
        self.assertNotEqual(
            payload["left"]["fingerprint"],
            payload["right"]["fingerprint"],
        )
        self.assertGreater(payload["delta"]["nodes"], 0)

    def test_verify_rejects_invalid_run_count(self):
        source = self.source_file(
            'mission "Verify" { source ready true; publish ready; }'
        )

        code, stdout, stderr = self.invoke(
            ["verify", source, "--runs", "1"]
        )

        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("--runs must be between 2 and 100", stderr)

    def test_limits_fail_closed(self):
        source = self.source_file(
            'mission "Limits" { source ready true; publish ready; }'
        )

        code, stdout, stderr = self.invoke(
            ["limits", source, "--max-nodes", "1"]
        )

        self.assertEqual(code, 1)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertFalse(payload["ok"])
        self.assertTrue(payload["violations"])

    def test_limits_fail_closed_on_excessive_width(self):
        source = self.source_file(
            'mission "Width" { source root true; let a root; let b root; let c root; publish c; }'
        )

        code, stdout, stderr = self.invoke(
            ["limits", source, "--max-width", "2"]
        )

        self.assertEqual(code, 1)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertFalse(payload["ok"])
        self.assertTrue(payload["violations"])

    def test_timeline_reports_level_grouped_runtime_state(self):
        source = self.source_file(
            'mission "Timeline" { source root true; let value root; publish value; }'
        )

        code, stdout, stderr = self.invoke(
            ["timeline", source]
        )

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertTrue(payload["success"])
        self.assertEqual(len(payload["fingerprint"]), 64)
        self.assertTrue(payload["timeline"])
        self.assertEqual(payload["timeline"][0]["level"], 0)

    def test_limits_fail_closed_on_excessive_fan_out(self):
        source = self.source_file(
            'mission "Fan out" { source root true; let a root; let b root; let c root; publish c; }'
        )

        code, stdout, stderr = self.invoke(
            ["limits", source, "--max-fan-out", "2"]
        )

        self.assertEqual(code, 1)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertFalse(payload["ok"])
        self.assertTrue(payload["violations"])

    def test_check_rejects_invalid_source(self):
        source = self.source_file("@")

        code, stdout, stderr = self.invoke(
            ["check", source]
        )

        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertTrue(stderr.strip())

    def test_check_reads_standard_input(self):
        code, stdout, stderr = self.invoke(
            ["check"],
            stdin="",
        )

        self.assertEqual(code, 0)
        self.assertEqual(stdout.strip(), "OK")
        self.assertEqual(stderr, "")

    def test_parse_emits_json(self):
        source = self.source_file("")

        code, stdout, stderr = self.invoke(
            ["parse", source]
        )

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")

        parsed = json.loads(stdout)

        self.assertIsInstance(parsed, dict)

    def test_plan_emits_execution_graph_json(self):
        source = self.source_file("")

        code, stdout, stderr = self.invoke(
            ["plan", source]
        )

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")

        graph = json.loads(stdout)

        self.assertEqual(graph["nodes"], [])
        self.assertEqual(graph["edges"], [])

    def test_run_executes_empty_program(self):
        source = self.source_file("")

        code, stdout, stderr = self.invoke(
            ["run", source]
        )

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")

        result = json.loads(stdout)

        self.assertTrue(result["success"])
        self.assertFalse(result["dry_run"])

    def test_mission_renders_operator_view(self):
        source = self.source_file(
            '''mission "Operator view" {
    stage "Inputs" {
        source ready true;
    }
    stage "Decision" {
        publish "AUTHORIZED";
    }
}
'''
        )

        code, stdout, stderr = self.invoke(
            ["mission", source]
        )

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertIn(
            "GHOST FIVE // VECTIS",
            stdout,
        )
        self.assertIn("MISSION CONTROL", stdout)
        self.assertIn("Operator view", stdout)
        self.assertIn("STAGES         2", stdout)
        self.assertIn("STAGE          Inputs", stdout)
        self.assertIn("STAGE          Decision", stdout)
        self.assertIn("AUTHORIZED", stdout)

    def test_actions_lists_standard_contracts_without_granting_authority(self):
        code, stdout, stderr = self.invoke(
            ["actions"]
        )

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertFalse(payload["configured"])
        self.assertEqual(
            {
                item["operation"]
                for item in payload["standard_actions"]
            },
            {
                "filesystem.read_text",
                "filesystem.write_text",
                "process.run",
                "http.request",
            },
        )

    def test_run_executes_action_through_explicit_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            workspace.mkdir()
            (workspace / "input.txt").write_text(
                "VECTIS ACTION PROFILE",
                encoding="utf-8",
            )
            config = root / "actions.toml"
            config.write_text(
                (
                    "# GHOST FIVE // VECTIS\n"
                    "# Explicit test authority profile.\n"
                    "[actions.filesystem]\n"
                    'roots = ["workspace"]\n'
                ),
                encoding="utf-8",
            )
            mission = root / "read.vectis"
            mission.write_text(
                (
                    "// GHOST FIVE // VECTIS\n"
                    "// CLI action profile integration mission.\n"
                    'mission "Read" {\n'
                    '    action content "filesystem.read_text" '
                    'using "filesystem" {path: "input.txt"};\n'
                    "    publish content;\n"
                    "}\n"
                ),
                encoding="utf-8",
            )

            code, stdout, stderr = self.invoke(
                [
                    "run",
                    "--actions-config",
                    str(config),
                    str(mission),
                ]
            )

            self.assertEqual(code, 0)
            self.assertEqual(stderr, "")
            payload = json.loads(stdout)
            self.assertTrue(payload["success"])
            values = dict(payload["node_values"])
            self.assertEqual(
                values["content"],
                "VECTIS ACTION PROFILE",
            )

    def test_action_fails_without_explicit_profile(self):
        source = self.source_file(
            (
                'mission "Denied" { '
                'action content "filesystem.read_text" '
                'using "filesystem" {path: "input.txt"}; '
                "publish content; }"
            )
        )

        code, stdout, stderr = self.invoke(
            ["run", source]
        )

        self.assertEqual(code, 1)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertFalse(payload["success"])
        self.assertTrue(payload["failures"])

    def test_audit_includes_action_authority(self):
        source = self.source_file(
            (
                'mission "Audit action" { '
                'action response "http.request" using "http" '
                '{method: "GET", url: "https://example.invalid"}; '
                "publish response; }"
            )
        )

        code, stdout, stderr = self.invoke(
            ["audit", "--json", source]
        )

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        capabilities = json.loads(stdout)["audit"]["capabilities"]
        self.assertIn(
            "http",
            capabilities["required"],
        )
        self.assertEqual(
            capabilities["actions"][0]["operation"],
            "http.request",
        )

    def test_run_supports_dry_run(self):
        source = self.source_file("")

        code, stdout, stderr = self.invoke(
            [
                "run",
                "--dry-run",
                source,
            ]
        )

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")

        result = json.loads(stdout)

        self.assertTrue(result["success"])
        self.assertTrue(result["dry_run"])

    def test_missing_source_file_is_user_error(self):
        code, stdout, stderr = self.invoke(
            [
                "check",
                "/definitely/not/a/vectis/file",
            ]
        )

        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("vectis:", stderr)

    def test_cli_entrypoint_remains_in_pyproject(self):
        text = Path(
            "pyproject.toml"
        ).read_text(encoding="utf-8")

        self.assertIn(
            'vectis = "vectis.cli:main"',
            text,
        )


if __name__ == "__main__":
    unittest.main()
