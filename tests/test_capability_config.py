# GHOST FIVE // VECTIS
# Verifies deterministic, non-executing capability configuration previews.
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from vectis.action_profile import load_action_profile
from vectis.capability_config import capability_configuration
from vectis.compiler import compile_program
from vectis.parser import parse


class CapabilityConfigurationTests(unittest.TestCase):
    def graph(self, source: str):
        result = compile_program(
            parse(source, file="<capability-config-test>")
        )
        self.assertTrue(result.ok)
        self.assertIsNotNone(result.graph)
        return result.graph

    def test_matching_profile_satisfies_action_plan(self) -> None:
        graph = self.graph(
            'mission "Configured" { '
            'action content "filesystem.read_text" '
            'using "filesystem" {path: "input.txt"}; '
            "publish content; }"
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "workspace").mkdir()
            profile_path = root / "actions.toml"
            profile_path.write_text(
                (
                    "# GHOST FIVE // VECTIS\n"
                    "# Explicit capability configuration test.\n"
                    "[actions.filesystem]\n"
                    'roots = ["workspace"]\n'
                ),
                encoding="utf-8",
            )
            profile = load_action_profile(profile_path)
            preview = capability_configuration(
                graph,
                profile=profile,
            )

        self.assertTrue(preview["satisfied"])
        self.assertEqual(
            preview["configuration"]["profile"]["source"],
            "actions.toml",
        )
        self.assertEqual(
            preview["missing"]["action_operations"],
            [],
        )
        self.assertEqual(len(preview["fingerprint"]), 64)

    def test_missing_capability_is_reported_without_execution(self) -> None:
        graph = self.graph(
            'mission "Missing" { require "custom"; publish "x"; }'
        )
        preview = capability_configuration(graph)

        self.assertFalse(preview["satisfied"])
        self.assertEqual(
            preview["missing"]["required_capabilities"],
            ["custom"],
        )

    def test_direct_capability_grant_can_satisfy_non_action_requirement(self) -> None:
        graph = self.graph(
            'mission "Direct" { require "custom"; publish "x"; }'
        )
        preview = capability_configuration(
            graph,
            extra_capabilities=("custom",),
        )

        self.assertTrue(preview["satisfied"])
        self.assertEqual(
            preview["configuration"]["extra_capabilities"],
            ["custom"],
        )

    def test_profile_does_not_imply_unregistered_custom_operation(self) -> None:
        graph = self.graph(
            'mission "Custom operation" { '
            'action result "custom.operation" '
            'using "filesystem" {value: 1}; '
            "publish result; }"
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "workspace").mkdir()
            profile_path = root / "actions.toml"
            profile_path.write_text(
                (
                    "# GHOST FIVE // VECTIS\n"
                    "# Explicit capability configuration test.\n"
                    "[actions.filesystem]\n"
                    'roots = ["workspace"]\n'
                ),
                encoding="utf-8",
            )
            preview = capability_configuration(
                graph,
                profile=load_action_profile(profile_path),
            )

        self.assertFalse(preview["satisfied"])
        self.assertEqual(
            preview["missing"]["required_capabilities"],
            [],
        )
        self.assertEqual(
            preview["missing"]["action_operations"][0]["operation"],
            "custom.operation",
        )
        rendered = json.dumps(preview, sort_keys=True)
        self.assertNotIn(str(root), rendered)


if __name__ == "__main__":
    unittest.main()
