# GHOST FIVE // VECTIS
# Regression coverage for the VECTIS process adapter contract.
"""Security-focused tests for the VECTIS process capability adapter."""

from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest

from vectis.adapters.process import (
    ProcessAccessDenied,
    ProcessAdapter,
    ProcessResult,
    ProcessTimeoutError,
)


class ProcessAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.python = Path(sys.executable).resolve()
        self.adapter = ProcessAdapter(
            {"python": self.python},
            default_timeout=2.0,
            max_timeout=3.0,
        )

    def test_public_capability_name(self) -> None:
        self.assertEqual(
            ProcessAdapter.capability,
            "process",
        )

    def test_explicit_executable_allowlist_is_canonical(self) -> None:
        self.assertEqual(
            self.adapter.allowed_executables,
            (("python", self.python),),
        )

        self.assertEqual(
            self.adapter.resolve_executable("python"),
            self.python,
        )

    def test_unknown_executable_alias_is_denied(self) -> None:
        with self.assertRaises(ProcessAccessDenied):
            self.adapter.resolve_executable("sh")

        with self.assertRaises(ProcessAccessDenied):
            self.adapter.run(
                "sh",
                ("-c", "echo forbidden"),
            )

    def test_denial_error_is_permission_error(self) -> None:
        self.assertTrue(
            issubclass(
                ProcessAccessDenied,
                PermissionError,
            )
        )

    def test_relative_executable_allowlist_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ProcessAdapter(["python3"])

    def test_structured_arguments_are_preserved_without_shell_interpolation(
        self,
    ) -> None:
        result = self.adapter.run(
            "python",
            (
                "-c",
                "import sys; print(sys.argv[1])",
                "; echo SHOULD_NOT_RUN",
            ),
        )

        self.assertEqual(
            result.stdout,
            "; echo SHOULD_NOT_RUN\n",
        )
        self.assertEqual(
            result.stderr,
            "",
        )
        self.assertEqual(
            result.returncode,
            0,
        )

    def test_string_command_arguments_are_rejected(self) -> None:
        with self.assertRaises(TypeError):
            self.adapter.run(
                "python",
                '-c "print(123)"',  # type: ignore[arg-type]
            )

    def test_stdout_and_stderr_are_captured(self) -> None:
        result = self.adapter.run(
            "python",
            (
                "-c",
                (
                    "import sys; "
                    "print('stdout-value'); "
                    "print('stderr-value', file=sys.stderr)"
                ),
            ),
        )

        self.assertIsInstance(
            result,
            ProcessResult,
        )
        self.assertEqual(
            result.returncode,
            0,
        )
        self.assertEqual(
            result.stdout,
            "stdout-value\n",
        )
        self.assertEqual(
            result.stderr,
            "stderr-value\n",
        )

    def test_nonzero_exit_is_a_structured_result(self) -> None:
        result = self.adapter.run(
            "python",
            (
                "-c",
                "import sys; sys.exit(7)",
            ),
        )

        self.assertIsInstance(
            result,
            ProcessResult,
        )
        self.assertEqual(
            result.returncode,
            7,
        )

    def test_parent_environment_is_not_implicitly_inherited(self) -> None:
        name = "VECTIS_PROCESS_PARENT_ONLY"
        previous = os.environ.get(name)

        try:
            os.environ[name] = "must-not-inherit"

            result = self.adapter.run(
                "python",
                (
                    "-c",
                    (
                        "import os; "
                        f"print(os.environ.get({name!r}, 'ABSENT'))"
                    ),
                ),
            )

            self.assertEqual(
                result.stdout,
                "ABSENT\n",
            )
        finally:
            if previous is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = previous

    def test_explicit_environment_is_available(self) -> None:
        adapter = ProcessAdapter(
            {"python": self.python},
            default_timeout=2.0,
            max_timeout=3.0,
            environment={
                "VECTIS_EXPLICIT": "visible",
            },
        )

        result = adapter.run(
            "python",
            (
                "-c",
                (
                    "import os; "
                    "print(os.environ.get('VECTIS_EXPLICIT', 'ABSENT'))"
                ),
            ),
        )

        self.assertEqual(
            result.stdout,
            "visible\n",
        )

    def test_timeout_above_configured_maximum_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.adapter.run(
                "python",
                (
                    "-c",
                    "print('never-run')",
                ),
                timeout=4.0,
            )

    def test_timeout_is_enforced(self) -> None:
        with self.assertRaises(ProcessTimeoutError) as caught:
            self.adapter.run(
                "python",
                (
                    "-c",
                    "import time; time.sleep(1)",
                ),
                timeout=0.05,
            )

        error = caught.exception

        self.assertEqual(
            error.argv[0],
            str(self.python),
        )
        self.assertEqual(
            error.timeout,
            0.05,
        )

    def test_timeout_error_is_timeout_error(self) -> None:
        self.assertTrue(
            issubclass(
                ProcessTimeoutError,
                TimeoutError,
            )
        )

    def test_successful_execution_is_repeatable(self) -> None:
        first = self.adapter.run(
            "python",
            (
                "-c",
                "print('stable')",
            ),
        )

        second = self.adapter.run(
            "python",
            (
                "-c",
                "print('stable')",
            ),
        )

        self.assertEqual(
            (
                first.returncode,
                first.stdout,
                first.stderr,
            ),
            (
                second.returncode,
                second.stdout,
                second.stderr,
            ),
        )


if __name__ == "__main__":
    unittest.main()
