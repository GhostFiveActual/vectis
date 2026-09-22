# GHOST FIVE // VECTIS
# Regression coverage for explicit CLI action authority profiles.
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

from vectis.action_profile import (
    load_action_profile,
    profile_manifest,
)


class ActionProfileTests(unittest.TestCase):
    def write_profile(
        self,
        root: Path,
        text: str,
    ) -> Path:
        path = root / "actions.toml"
        path.write_text(
            text,
            encoding="utf-8",
        )
        return path

    def test_profile_resolves_bounded_adapters(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "workspace").mkdir()
            executable = Path(sys.executable).resolve()
            profile = load_action_profile(
                self.write_profile(
                    root,
                    (
                        "# GHOST FIVE // VECTIS\n"
                        "# Explicit local action authority for this test.\n"
                        "[actions.filesystem]\n"
                        'roots = ["workspace"]\n'
                        "\n"
                        "[actions.process]\n"
                        "default_timeout = 5\n"
                        "max_timeout = 10\n"
                        "\n"
                        "[actions.process.executables]\n"
                        f'python = "{executable.as_posix()}"\n'
                        "\n"
                        "[actions.process.environment]\n"
                        'VECTIS_TEST = "enabled"\n'
                        "\n"
                        "[actions.http]\n"
                        'allowed_hosts = ["example.com"]\n'
                    ),
                )
            )

            self.assertEqual(
                profile.capabilities,
                (
                    "filesystem",
                    "process",
                    "http",
                ),
            )
            operations = {
                item["operation"]
                for item in profile.actions.manifest()
            }
            self.assertEqual(
                operations,
                {
                    "filesystem.read_text",
                    "filesystem.write_text",
                    "process.run",
                    "http.request",
                },
            )

            manifest = profile_manifest(profile)
            process = next(
                item
                for item in manifest["adapters"]
                if item["capability"] == "process"
            )
            self.assertEqual(
                process["environment_keys"],
                ["VECTIS_TEST"],
            )
            self.assertNotIn(
                "enabled",
                str(manifest),
            )

    def test_profile_requires_http_host_allowlist(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self.write_profile(
                root,
                (
                    "# GHOST FIVE // VECTIS\n"
                    "# Explicit local action authority for this test.\n"
                    "[actions.http]\n"
                    "default_timeout = 5\n"
                ),
            )
            with self.assertRaisesRegex(
                ValueError,
                "allowed_hosts",
            ):
                load_action_profile(path)

    def test_profile_rejects_relative_process_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self.write_profile(
                root,
                (
                    "# GHOST FIVE // VECTIS\n"
                    "# Explicit local action authority for this test.\n"
                    "[actions.process.executables]\n"
                    'python = "python"\n'
                ),
            )
            with self.assertRaisesRegex(
                ValueError,
                "absolute",
            ):
                load_action_profile(path)

    def test_profile_rejects_unknown_authority_section(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self.write_profile(
                root,
                (
                    "# GHOST FIVE // VECTIS\n"
                    "# Explicit local action authority for this test.\n"
                    "[actions.magic]\n"
                    "enabled = true\n"
                ),
            )
            with self.assertRaisesRegex(
                ValueError,
                "unsupported action profile adapters",
            ):
                load_action_profile(path)


if __name__ == "__main__":
    unittest.main()
