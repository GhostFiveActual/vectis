# GHOST FIVE // VECTIS
# Regression coverage for project tooling, graph exports, and expanded built in functions.

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from vectis.compiler import compile_program
from vectis.evaluator import evaluate_expression
from vectis.modules import load_program_file
from vectis.parser import parse, parse_expression
from vectis.product import (
    enforce_graph_limits,
    execution_report_html,
    execution_timeline,
    graph_fingerprint,
    graph_summary,
    graph_to_dot,
    graph_to_mermaid,
    initialize_project,
    plan_audit,
    test_project,
)
from vectis.runtime import Runtime


class ProductToolingTests(unittest.TestCase):
    """Protect the operational product surface added for the 0.1 line."""

    def evaluate(self, source: str):
        """Evaluate one deterministic expression for focused assertions."""
        return evaluate_expression(
            parse_expression(source, file="<product-test>"),
            {},
        )

    def test_expanded_builtins(self):
        self.assertEqual(
            self.evaluate('replace("GHOST FIVE", "FIVE", "CORE")'),
            "GHOST CORE",
        )
        self.assertEqual(
            self.evaluate('repeat("V", 3)'),
            "VVV",
        )
        self.assertEqual(
            self.evaluate("clamp(108, 0, 100)"),
            100,
        )
        self.assertTrue(
            self.evaluate("between(94, 80, 100)")
        )
        self.assertEqual(
            self.evaluate(
                'if_else(94 >= 80, "AUTHORIZED", "REVIEW")'
            ),
            "AUTHORIZED",
        )
        self.assertEqual(
            self.evaluate('capitalize("mission control")'),
            "Mission control",
        )
        self.assertEqual(
            self.evaluate('title("mission control")'),
            "Mission Control",
        )

    def test_project_scaffold_is_branded_and_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "vectis-project"
            created = initialize_project(root)

            self.assertEqual(len(created), 5)
            self.assertIn(
                "GHOST FIVE // VECTIS",
                (root / "README.md").read_text(encoding="utf-8"),
            )
            self.assertIn(
                "GHOST FIVE // VECTIS",
                (root / "vectis.toml").read_text(encoding="utf-8"),
            )
            self.assertIn(
                "[actions.filesystem]",
                (root / "actions.example.toml").read_text(
                    encoding="utf-8"
                ),
            )

            result = test_project(root)
            self.assertEqual(result["files"], 2)
            self.assertEqual(result["failed"], 0)
            self.assertTrue(
                (root / "lib" / "readiness.vectis").is_file()
            )
            self.assertIn(
                'import "../lib/readiness.vectis";',
                (root / "missions" / "main.vectis").read_text(
                    encoding="utf-8"
                ),
            )

    def test_graph_exports_are_deterministic(self):
        source = """mission "Graph" {
    source ready true;
    let label upper("vectis");
    when ready {
        publish label;
    }
}
"""
        compiled = compile_program(
            parse(source, file="<graph-test>")
        )
        self.assertTrue(compiled.ok)
        graph = compiled.graph
        self.assertIsNotNone(graph)

        summary = graph_summary(graph)
        self.assertEqual(summary["nodes"], 4)
        self.assertGreaterEqual(summary["edges"], 2)
        self.assertGreaterEqual(summary["levels"], 2)
        self.assertGreaterEqual(summary["max_width"], 1)
        self.assertGreaterEqual(summary["max_fan_out"], 1)
        self.assertTrue(summary["sources"])
        self.assertTrue(summary["sinks"])
        self.assertEqual(len(summary["fingerprint"]), 64)
        self.assertEqual(
            summary["fingerprint"],
            graph_fingerprint(graph),
        )

        limits = enforce_graph_limits(
            graph,
            max_nodes=20,
            max_edges=30,
            max_depth=20,
            max_width=20,
            max_fan_in=20,
            max_fan_out=20,
        )
        self.assertTrue(limits["ok"])
        self.assertFalse(
            enforce_graph_limits(graph, max_nodes=1)["ok"]
        )
        self.assertFalse(
            enforce_graph_limits(graph, max_width=1)["ok"]
        )

        dot = graph_to_dot(graph)
        mermaid = graph_to_mermaid(graph)

        self.assertIn("digraph vectis", dot)
        self.assertIn("flowchart LR", mermaid)
        self.assertIn("condition:0001", dot)
        self.assertIn("condition:0001", mermaid)

    def test_timeline_groups_runtime_by_graph_level(self):
        source = """mission "Timeline" {
    source root true;
    let left root;
    let right root;
    let approved left && right;
    publish approved;
}
"""
        compiled = compile_program(
            parse(source, file="<timeline-test>")
        )
        self.assertTrue(compiled.ok)
        result = Runtime(compiled.graph).execute()
        timeline = execution_timeline(compiled.graph, result)

        self.assertGreaterEqual(len(timeline), 3)
        self.assertEqual(timeline[0]["level"], 0)
        self.assertTrue(
            any(
                node["id"] == "root"
                for node in timeline[0]["nodes"]
            )
        )
        flattened = [
            node
            for level in timeline
            for node in level["nodes"]
        ]
        self.assertTrue(
            any(node["id"] == "approved" for node in flattened)
        )
        self.assertTrue(
            all("state" in node for node in flattened)
        )

    def test_fan_limits_fail_closed(self):
        source = """mission "Fan limits" {
    source root true;
    let a root;
    let b root;
    let c root;
    let joined a && b && c;
    publish joined;
}
"""
        compiled = compile_program(parse(source))
        self.assertTrue(compiled.ok)

        fan_out = enforce_graph_limits(
            compiled.graph,
            max_fan_out=2,
        )
        fan_in = enforce_graph_limits(
            compiled.graph,
            max_fan_in=2,
        )

        self.assertFalse(fan_out["ok"])
        self.assertFalse(fan_in["ok"])

    def test_plan_audit_is_deterministic_and_stage_aware(self):
        source = """mission "Audit" {
    stage "Inputs" {
        source ready true;
        source score 96;
    }

    stage "Authority" {
        require "filesystem";
        request "http";
    }

    stage "Decision" {
        let approved ready && score >= 90;
        when approved {
            publish "AUTHORIZED";
        }
    }
}
"""
        compiled = compile_program(
            parse(source, file="<audit-test>")
        )
        self.assertTrue(compiled.ok)

        first = plan_audit(compiled.graph)
        second = plan_audit(compiled.graph)

        self.assertEqual(first, second)
        self.assertEqual(len(first["fingerprint"]), 64)
        self.assertEqual(first["summary"]["stage_count"], 3)
        self.assertEqual(
            first["capabilities"]["required"],
            ["filesystem"],
        )
        self.assertEqual(
            first["capabilities"]["requested"],
            ["http"],
        )
        self.assertEqual(
            [stage["name"] for stage in first["stages"]],
            ["Inputs", "Authority", "Decision"],
        )

    def test_execution_report_contains_trace_and_brand(self):
        source = """mission "Report" {
    stage "Inputs" {
        source ready true;
    }

    stage "Decision" {
        let status if_else(ready, "AUTHORIZED", "REVIEW");
        publish status;
    }
}
"""
        compiled = compile_program(
            parse(source, file="<report-test>")
        )
        self.assertTrue(compiled.ok)
        result = Runtime(compiled.graph).execute()
        report = execution_report_html(
            compiled.graph,
            result,
            mission_name="Report",
            source_name="<report-test>",
        )

        self.assertIn("GHOST FIVE // VECTIS", report)
        self.assertIn("Execution Trace", report)
        self.assertIn("Plan Fingerprint", report)
        self.assertIn("Inputs", report)
        self.assertIn("Decision", report)
        self.assertIn(graph_fingerprint(compiled.graph), report)
        self.assertIn("AUTHORIZED", report)

    def test_deep_plan_with_six_hundred_steps_is_deterministic(self):
        steps = 600
        lines = [
            'mission "Deep deterministic plan" {',
            "    source step_0 0;",
        ]
        for index in range(1, steps + 1):
            lines.append(
                f"    let step_{index} step_{index - 1} + 1;"
            )
        lines.extend(
            [
                f"    publish step_{steps};",
                "}",
            ]
        )
        source = "\n".join(lines) + "\n"

        first = compile_program(
            parse(source, file="<deep-plan>")
        )
        second = compile_program(
            parse(source, file="<deep-plan>")
        )

        self.assertTrue(first.ok, first.diagnostics)
        self.assertTrue(second.ok, second.diagnostics)
        self.assertIsNotNone(first.graph)
        self.assertIsNotNone(second.graph)
        self.assertGreater(len(first.graph.nodes), 600)
        self.assertGreater(len(first.graph.edges), 599)
        self.assertEqual(
            graph_fingerprint(first.graph),
            graph_fingerprint(second.graph),
        )

        summary = graph_summary(first.graph)
        self.assertGreaterEqual(summary["depth"], 600)

        result = Runtime(first.graph).execute()
        self.assertTrue(result.success)
        self.assertEqual(
            result.value_for(f"step_{steps}"),
            steps,
        )

    def test_project_scaffold_executes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initialize_project(root)
            loaded = load_program_file(
                root / "missions" / "main.vectis"
            )
            compiled = compile_program(
                loaded.program
            )
            self.assertTrue(compiled.ok)
            result = Runtime(compiled.graph).execute()
            self.assertTrue(result.success)


if __name__ == "__main__":
    unittest.main()
