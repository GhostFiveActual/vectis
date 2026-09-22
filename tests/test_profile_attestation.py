# GHOST FIVE // VECTIS
# Regression coverage for action profile authority-shape attestation.
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

from vectis.action_profile import load_action_profile
from vectis.profile_attestation import (
    PROFILE_ATTESTATION_SCHEMA,
    action_profile_attestation,
    action_profile_descriptor,
    action_profile_fingerprint,
)


class ActionProfileAttestationTests(
    unittest.TestCase
):
    def write_profile(
        self,
        root: Path,
        *,
        environment_value: str,
        host: str = "example.com",
    ) -> Path:
        workspace = root / "workspace"
        workspace.mkdir(
            exist_ok=True,
        )
        executable = (
            Path(sys.executable)
            .resolve()
            .as_posix()
        )
        path = root / "actions.toml"
        path.write_text(
            (
                "# GHOST FIVE // VECTIS\n"
                "# Explicit authority for attestation tests.\n"
                "[actions.filesystem]\n"
                'roots = ["workspace"]\n'
                "\n"
                "[actions.process]\n"
                "default_timeout = 5\n"
                "max_timeout = 10\n"
                "\n"
                "[actions.process.executables]\n"
                f'python = "{executable}"\n'
                "\n"
                "[actions.process.environment]\n"
                f'VECTIS_SECRET = "{environment_value}"\n'
                "\n"
                "[actions.http]\n"
                f'allowed_hosts = ["{host}"]\n'
            ),
            encoding="utf-8",
        )
        return path

    def test_fingerprint_is_stable(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self.write_profile(
                root,
                environment_value="first-secret",
            )

            first = action_profile_fingerprint(
                load_action_profile(path)
            )
            second = action_profile_fingerprint(
                load_action_profile(path)
            )

            self.assertEqual(first, second)
            self.assertEqual(len(first), 64)

    def test_secret_value_is_not_attested(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self.write_profile(
                root,
                environment_value="first-secret",
            )
            first_profile = load_action_profile(
                path
            )
            first = action_profile_fingerprint(
                first_profile
            )

            self.write_profile(
                root,
                environment_value="second-secret",
            )
            second_profile = load_action_profile(
                path
            )
            second = action_profile_fingerprint(
                second_profile
            )

            self.assertEqual(first, second)
            descriptor = action_profile_descriptor(
                second_profile
            )
            rendered = str(descriptor)
            self.assertNotIn(
                "first-secret",
                rendered,
            )
            self.assertNotIn(
                "second-secret",
                rendered,
            )
            self.assertFalse(
                descriptor[
                    "secret_values_attested"
                ]
            )

    def test_authority_boundary_changes_fingerprint(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self.write_profile(
                root,
                environment_value="secret",
                host="example.com",
            )
            first = action_profile_fingerprint(
                load_action_profile(path)
            )

            self.write_profile(
                root,
                environment_value="secret",
                host="api.example.com",
            )
            second = action_profile_fingerprint(
                load_action_profile(path)
            )

            self.assertNotEqual(first, second)

    def test_attestation_uses_safe_source_label(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self.write_profile(
                root,
                environment_value="secret",
            )
            attestation = (
                action_profile_attestation(
                    load_action_profile(path)
                )
            )

            self.assertEqual(
                attestation["schema"],
                PROFILE_ATTESTATION_SCHEMA,
            )
            self.assertEqual(
                attestation["algorithm"],
                "sha256",
            )
            self.assertEqual(
                attestation["scope"],
                "authority-shape",
            )
            self.assertEqual(
                attestation["source"],
                "actions.toml",
            )
            self.assertFalse(
                attestation[
                    "secret_values_attested"
                ]
            )
            self.assertNotIn(
                str(root),
                str(attestation),
            )


if __name__ == "__main__":
    unittest.main()
