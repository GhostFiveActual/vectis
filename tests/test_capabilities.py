# GHOST FIVE // VECTIS
# Regression coverage for the VECTIS capabilities contract.
import unittest
from vectis.ir import ExecutionGraph, GraphNode, EdgeKind, NodeKind, GraphEdge
from vectis.ast import RequireStatement, RequestStatement, StringLiteral
from vectis.capabilities import CapabilityModel, Capability, CapabilityError, CapabilityDenied


class TestCapabilities(unittest.TestCase):
    def test_declare_capability(self):
        model = CapabilityModel()
        capability = Capability(name="test_capability", description="A test capability")
        model.declare_capability(capability)
        self.assertTrue(model.has_capability("test_capability"))

    def test_get_capability(self):
        model = CapabilityModel()
        capability = Capability(name="test_capability", description="A test capability")
        model.declare_capability(capability)
        retrieved_capability = model.get_capability("test_capability")
        self.assertEqual(retrieved_capability, capability)

    def test_has_capability(self):
        model = CapabilityModel()
        capability = Capability(name="test_capability", description="A test capability")
        model.declare_capability(capability)
        self.assertTrue(model.has_capability("test_capability"))
        self.assertFalse(model.has_capability("nonexistent_capability"))

    def test_check_capabilities(self):
        model = CapabilityModel()
        capability = Capability(name="test_capability", description="A test capability", required=True)
        model.declare_capability(capability)

        graph = ExecutionGraph(
            nodes=(
                GraphNode(id="node1", kind=NodeKind.MISSION),
                GraphNode(id="node2", kind=NodeKind.SOURCE),
            ),
            edges=(
                GraphEdge(source="node1", target="node2", kind=EdgeKind.DEPENDENCY),
            ),
        )

        errors = model.check_capabilities(graph)
        self.assertEqual(len(errors), 0)

        # Test with an explicitly missing required capability
        graph = ExecutionGraph(
            nodes=(
                GraphNode(id="node1", kind=NodeKind.MISSION, metadata=(("test_capability", None),)),
                GraphNode(id="node2", kind=NodeKind.SOURCE),
            ),
            edges=(
                GraphEdge(source="node1", target="node2", kind=EdgeKind.DEPENDENCY),
            ),
        )

        errors = model.check_capabilities(graph)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], CapabilityError)
        self.assertIn("test_capability", str(errors[0]))

    def test_capability_declaration(self):
        model = CapabilityModel()
        capability = Capability(name="read_file", description="Read a file")
        model.declare_capability(capability)
        self.assertTrue(model.has_capability("read_file"))

    def test_unavailable_capability_denied(self):
        model = CapabilityModel()
        capability = Capability(name="delete_file", description="Delete a file", required=True)
        model.declare_capability(capability)

        graph = ExecutionGraph(
            nodes=(
                GraphNode(id="node1", kind=NodeKind.MISSION, metadata=(("delete_file", None),)),
                GraphNode(id="node2", kind=NodeKind.SOURCE),
            ),
            edges=(
                GraphEdge(source="node1", target="node2", kind=EdgeKind.DEPENDENCY),
            ),
        )

        errors = model.check_capabilities(graph)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], CapabilityDenied)
        self.assertIsInstance(errors[0], CapabilityError)
        self.assertIn("delete_file", str(errors[0]))

    def test_capability_tests(self):
        model = CapabilityModel()
        capability = Capability(name="write_file", description="Write a file", required=True)
        model.declare_capability(capability)

        graph = ExecutionGraph(
            nodes=(
                GraphNode(id="node1", kind=NodeKind.MISSION, metadata=(("write_file", "data"),)),
                GraphNode(id="node2", kind=NodeKind.SOURCE),
            ),
            edges=(
                GraphEdge(source="node1", target="node2", kind=EdgeKind.DEPENDENCY),
            ),
        )

        errors = model.check_capabilities(graph)
        self.assertEqual(len(errors), 0)

        graph = ExecutionGraph(
            nodes=(
                GraphNode(id="node1", kind=NodeKind.MISSION, metadata=(("write_file", None),)),
                GraphNode(id="node2", kind=NodeKind.SOURCE),
            ),
            edges=(
                GraphEdge(source="node1", target="node2", kind=EdgeKind.DEPENDENCY),
            ),
        )

        errors = model.check_capabilities(graph)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], CapabilityError)
        self.assertIn("write_file", str(errors[0]))
