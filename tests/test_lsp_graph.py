# GHOST FIVE // VECTIS
# Verifies deterministic read-only graph inspection payloads for editor clients.
from __future__ import annotations

import unittest

from vectis.compiler import compile_program
from vectis.lsp_graph import GRAPH_INSPECTION_VERSION, graph_inspection
from vectis.parser import parse


class LspGraphInspectionTests(unittest.TestCase):
    def _inspection(self) -> dict[str, object]:
        source = """mission "Inspect" {
    stage "Inputs" {
        source ready true;
    }

    stage "Authority" {
        require "filesystem";
    }

    stage "Decision" {
        let approved ready;
        when approved {
            publish "yes";
        } otherwise {
            publish "no";
        }
    }
}
"""
        compiled = compile_program(
            parse(source, file="<graph-inspection-test>")
        )
        self.assertTrue(compiled.ok)
        self.assertIsNotNone(compiled.graph)
        return graph_inspection(compiled.graph)

    def test_payload_is_deterministic(self) -> None:
        first = self._inspection()
        second = self._inspection()
        self.assertEqual(first, second)
        self.assertEqual(first["version"], GRAPH_INSPECTION_VERSION)
        self.assertEqual(len(first["fingerprint"]), 64)
        self.assertEqual(
            first["fingerprint"],
            first["summary"]["fingerprint"],
        )

    def test_nodes_expose_structure_without_values(self) -> None:
        inspection = self._inspection()
        nodes = {item["id"]: item for item in inspection["nodes"]}
        self.assertIn("ready", nodes)
        self.assertIn("approved", nodes)
        self.assertIn("condition:0001", nodes)

        for item in nodes.values():
            self.assertNotIn("value", item)
            self.assertNotIn("state", item)

        self.assertEqual(
            nodes["approved"]["dependencies"],
            ["ready"],
        )
        self.assertIn("approved", nodes["ready"]["successors"])

    def test_branch_edges_preserve_edge_kind(self) -> None:
        inspection = self._inspection()
        condition = next(
            item
            for item in inspection["nodes"]
            if item["id"] == "condition:0001"
        )
        kinds = {edge["kind"] for edge in condition["outgoing"]}
        self.assertEqual(kinds, {"true", "false"})

    def test_stage_and_capability_manifests_are_preserved(self) -> None:
        inspection = self._inspection()
        self.assertEqual(
            [item["name"] for item in inspection["stages"]],
            ["Inputs", "Authority", "Decision"],
        )
        self.assertEqual(
            inspection["capabilities"]["required"],
            ["filesystem"],
        )


if __name__ == "__main__":
    unittest.main()
