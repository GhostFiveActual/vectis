# GHOST FIVE // VECTIS
# Regression coverage for the VECTIS security architecture contract.
from __future__ import annotations

import ast
import inspect
from pathlib import Path
import subprocess
import sys
import unittest

from vectis.capabilities import (
    Capability,
    CapabilityDenied,
    CapabilityError,
    CapabilityRegistry,
)
from vectis.ir import NodeKind


ROOT = Path(__file__).resolve().parents[1]

PROCESS_ADAPTER = (
    ROOT
    / "src"
    / "vectis"
    / "adapters"
    / "process.py"
)

FILESYSTEM_ADAPTER = (
    ROOT
    / "src"
    / "vectis"
    / "adapters"
    / "filesystem.py"
)

HTTP_ADAPTER = (
    ROOT
    / "src"
    / "vectis"
    / "adapters"
    / "http.py"
)

RUNTIME = (
    ROOT
    / "src"
    / "vectis"
    / "runtime.py"
)


def parse_python(path: Path) -> ast.Module:
    return ast.parse(
        path.read_text(encoding="utf-8"),
        filename=str(path),
    )


def dotted_name(node: ast.AST) -> str:
    parts: list[str] = []

    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value

    if isinstance(node, ast.Name):
        parts.append(node.id)

    return ".".join(reversed(parts))


def calls_in(path: Path) -> list[ast.Call]:
    tree = parse_python(path)

    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    ]


def run_existing_test(name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "unittest",
            "-v",
            name,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


class TestSecurityArchitecture(unittest.TestCase):
    def test_node_kind_is_closed(self):
        with self.assertRaises(ValueError):
            NodeKind(
                "__security_review_invalid_kind__"
            )

    def test_node_kind_has_real_members(self):
        members = tuple(NodeKind)

        self.assertTrue(members)

        for member in members:
            self.assertIsInstance(
                member,
                NodeKind,
            )

    def test_capability_denial_is_capability_error(self):
        self.assertTrue(
            issubclass(
                CapabilityDenied,
                CapabilityError,
            )
        )

    def test_capability_registry_accepts_explicit_declaration(self):
        registry = CapabilityRegistry()

        capability = Capability(
            "security_review_capability",
            "Security review capability",
            required=True,
        )

        registry.declare_capability(
            capability
        )

    def test_process_adapter_never_enables_shell_true(self):
        for call in calls_in(
            PROCESS_ADAPTER
        ):
            for keyword in call.keywords:
                if keyword.arg != "shell":
                    continue

                self.assertFalse(
                    isinstance(
                        keyword.value,
                        ast.Constant,
                    )
                    and keyword.value.value is True,
                    "process adapter must not invoke shell=True",
                )

    def test_adapters_do_not_call_os_system(self):
        for path in (
            PROCESS_ADAPTER,
            FILESYSTEM_ADAPTER,
            HTTP_ADAPTER,
        ):
            with self.subTest(path=path):
                names = {
                    dotted_name(call.func)
                    for call in calls_in(path)
                }

                self.assertNotIn(
                    "os.system",
                    names,
                )

    def test_filesystem_and_http_do_not_spawn_processes(self):
        forbidden = {
            "subprocess.Popen",
            "subprocess.run",
            "subprocess.call",
            "subprocess.check_call",
            "subprocess.check_output",
            "os.system",
        }

        for path in (
            FILESYSTEM_ADAPTER,
            HTTP_ADAPTER,
        ):
            with self.subTest(path=path):
                names = {
                    dotted_name(call.func)
                    for call in calls_in(path)
                }

                self.assertTrue(
                    names.isdisjoint(
                        forbidden
                    ),
                    sorted(
                        names & forbidden
                    ),
                )

    def test_runtime_does_not_use_dynamic_eval_or_exec(self):
        names = {
            dotted_name(call.func)
            for call in calls_in(
                RUNTIME
            )
        }

        self.assertNotIn(
            "eval",
            names,
        )

        self.assertNotIn(
            "exec",
            names,
        )

    def test_process_string_commands_remain_rejected(self):
        completed = run_existing_test(
            "tests.test_process_adapter."
            "ProcessAdapterTests."
            "test_string_command_arguments_are_rejected"
        )

        self.assertEqual(
            completed.returncode,
            0,
            completed.stdout + completed.stderr,
        )

    def test_relative_process_allowlist_remains_rejected(self):
        completed = run_existing_test(
            "tests.test_process_adapter."
            "ProcessAdapterTests."
            "test_relative_executable_allowlist_is_rejected"
        )

        self.assertEqual(
            completed.returncode,
            0,
            completed.stdout + completed.stderr,
        )

    def test_parent_environment_is_not_inherited(self):
        completed = run_existing_test(
            "tests.test_process_adapter."
            "ProcessAdapterTests."
            "test_parent_environment_is_not_implicitly_inherited"
        )

        self.assertEqual(
            completed.returncode,
            0,
            completed.stdout + completed.stderr,
        )

    def test_runtime_denies_unavailable_capability(self):
        completed = run_existing_test(
            "tests.test_runtime."
            "RuntimeTests."
            "test_unavailable_capability_is_denied"
        )

        self.assertEqual(
            completed.returncode,
            0,
            completed.stdout + completed.stderr,
        )

    def test_capability_public_types_are_real_classes(self):
        for value in (
            Capability,
            CapabilityRegistry,
            CapabilityError,
            CapabilityDenied,
        ):
            self.assertTrue(
                inspect.isclass(value)
            )


if __name__ == "__main__":
    unittest.main()
