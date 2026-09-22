# GHOST FIVE // VECTIS
# Regression coverage for large deterministic execution plans.

from __future__ import annotations

import unittest

from vectis.compiler import compile_program
from vectis.parser import parse
from vectis.product import graph_summary, plan_audit
from vectis.runtime import Runtime


class LargePlanTests(unittest.TestCase):
    """Protect deterministic compilation and execution at practical plan scale."""

    def make_chain(self, steps: int) -> str:
        lines = [
            '// GHOST FIVE // VECTIS',
            '// Generated large-plan regression mission.',
            'mission "Large deterministic plan" {',
            '    source value_0 0;',
        ]
        for index in range(1, steps + 1):
            lines.append(
                f"    let value_{index} value_{index - 1} + 1;"
            )
        lines.extend(
            [
                f"    assert value_{steps} == {steps};",
                f"    publish value_{steps};",
                "}",
                "",
            ]
        )
        return "\n".join(lines)

    def make_wide_plan(self, width: int) -> str:
        """Build a plan with many independent values at one graph level."""
        lines = [
            '// GHOST FIVE // VECTIS',
            '// Generated wide-plan regression mission.',
            'mission "Wide deterministic plan" {',
            '    source root true;',
        ]
        for index in range(width):
            lines.append(
                f"    let branch_{index} root;"
            )
        lines.extend(
            [
                f"    publish branch_{width - 1};",
                "}",
                "",
            ]
        )
        return "\n".join(lines)

    def test_thousand_step_plan_is_deterministic(self):
        source = self.make_chain(1000)

        first = compile_program(
            parse(source, file="<large-plan>")
        )
        second = compile_program(
            parse(source, file="<large-plan>")
        )

        self.assertTrue(first.ok)
        self.assertTrue(second.ok)
        self.assertEqual(
            first.graph.to_json(),
            second.graph.to_json(),
        )
        self.assertGreaterEqual(
            len(first.graph.nodes),
            1002,
        )

        result = Runtime(first.graph).execute()
        self.assertTrue(result.success)
        self.assertEqual(
            result.value_for("value_1000"),
            1000,
        )
        self.assertEqual(
            result.value_for("publish:0001"),
            1000,
        )

    def test_wide_plan_metrics_and_audit_scale_deterministically(self):
        source = self.make_wide_plan(750)

        first = compile_program(
            parse(source, file="<wide-plan>")
        )
        second = compile_program(
            parse(source, file="<wide-plan>")
        )

        self.assertTrue(first.ok)
        self.assertTrue(second.ok)
        self.assertEqual(
            first.graph.to_json(),
            second.graph.to_json(),
        )

        summary = graph_summary(first.graph)
        audit = plan_audit(first.graph)

        self.assertGreaterEqual(summary["nodes"], 752)
        self.assertGreaterEqual(summary["max_width"], 750)
        self.assertEqual(summary["fingerprint"], audit["fingerprint"])
        self.assertEqual(audit, plan_audit(second.graph))
        self.assertTrue(audit["determinism"]["acyclic"])

        result = Runtime(first.graph).execute()
        self.assertTrue(result.success)
        self.assertTrue(
            result.value_for("branch_749")
        )
        self.assertTrue(
            result.value_for("publish:0001")
        )


if __name__ == "__main__":
    unittest.main()
