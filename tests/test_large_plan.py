# GHOST FIVE // VECTIS
# Regression coverage for large staged deterministic execution plans.

from __future__ import annotations

import unittest

from vectis.compiler import compile_program
from vectis.parser import parse
from vectis.product import graph_summary
from vectis.runtime import Runtime


class LargePlanTests(unittest.TestCase):
    """Protect deterministic behavior as execution plans grow."""

    @staticmethod
    def source(stages: int = 6, per_stage: int = 50) -> str:
        lines = [
            "// GHOST FIVE // VECTIS",
            "// Generated scale fixture for staged execution planning.",
            'mission "Large deterministic plan" {',
            "    source value_0 0;",
        ]
        current = 0

        for stage_index in range(1, stages + 1):
            lines.append(f'    stage "Stage {stage_index}" {{')
            for _ in range(per_stage):
                current += 1
                lines.append(
                    f"        let value_{current} value_{current - 1} + 1;"
                )
            lines.append("    }")

        lines.extend(
            [
                f"    assert value_{current} == {current};",
                f"    publish value_{current};",
                "}",
                "",
            ]
        )
        return "\n".join(lines)

    def test_large_plan_compiles_and_executes(self):
        source = self.source()
        compiled = compile_program(
            parse(source, file="<large-plan>")
        )

        self.assertTrue(compiled.ok, compiled.diagnostics)
        self.assertIsNotNone(compiled.graph)

        summary = graph_summary(compiled.graph)
        self.assertGreater(summary["nodes"], 300)
        self.assertGreater(summary["depth"], 300)
        self.assertGreater(summary["levels"], 300)

        first = Runtime(compiled.graph).execute()
        second = Runtime(compiled.graph).execute()

        self.assertTrue(first.success)
        self.assertTrue(second.success)
        self.assertEqual(first.execution_order, second.execution_order)
        self.assertEqual(first.node_values, second.node_values)
        self.assertEqual(
            dict(first.node_values)["publish:0001"],
            300,
        )

    def test_large_plan_graph_is_byte_stable(self):
        source = self.source(stages=4, per_stage=50)
        first = compile_program(parse(source))
        second = compile_program(parse(source))

        self.assertEqual(
            first.graph.to_json(),
            second.graph.to_json(),
        )


if __name__ == "__main__":
    unittest.main()
