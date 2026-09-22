# GHOST FIVE // VECTIS
# Regression coverage for the VECTIS architecture docs contract.
from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ARCH = ROOT / "docs" / "architecture"


class TestArchitectureDocs(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.docs = {
            path.name: path.read_text(encoding="utf-8")
            for path in ARCH.glob("*.md")
        }

    def test_required_architecture_documents_exist(self):
        for name in (
            "overview.md",
            "compiler-pipeline.md",
            "runtime.md",
            "security.md",
            "threat-model.md",
        ):
            with self.subTest(name=name):
                self.assertIn(name, self.docs)
                self.assertTrue(self.docs[name].strip())

    def test_system_architecture_documents_real_pipeline(self):
        text = self.docs["overview.md"].lower()
        for term in (
            "lexer",
            "parser",
            "semantic",
            "execution graph",
            "runtime",
            "studio",
        ):
            with self.subTest(term=term):
                self.assertIn(term, text)

    def test_compiler_pipeline_documents_new_language_surface(self):
        text = self.docs["compiler-pipeline.md"].lower()
        for term in (
            "callexpression",
            "letdeclaration",
            "assertstatement",
            "constant folding",
            "true/false",
        ):
            with self.subTest(term=term):
                self.assertIn(term, text)

    def test_runtime_design_documents_values_and_assertions(self):
        text = self.docs["runtime.md"].lower()
        for term in (
            "topological",
            "node values",
            "assert",
            "blocked",
            "dry run",
            "capability",
        ):
            with self.subTest(term=term):
                self.assertIn(term, text)

    def test_security_model_does_not_claim_unimplemented_identity_features(self):
        text = self.docs["security.md"].lower()
        self.assertIn("does **not** currently implement", text)
        for false_claim in (
            "vectis uses a multi-factor",
            "vectis uses a role-based",
            "vectis uses end-to-end encryption",
        ):
            with self.subTest(false_claim=false_claim):
                self.assertNotIn(false_claim, text)

    def test_security_model_documents_concrete_controls(self):
        text = self.docs["security.md"].lower()
        for term in (
            "cap001",
            "cap002",
            "shell=true",
            "symlink",
            "loopback",
            "eval",
            "exec",
        ):
            with self.subTest(term=term):
                self.assertIn(term, text)

    def test_threat_model_documents_studio_and_adapter_boundaries(self):
        text = self.docs["threat-model.md"].lower()
        for term in (
            "source → compiler",
            "graph → runtime",
            "runtime → adapters",
            "browser → studio local server",
        ):
            with self.subTest(term=term):
                self.assertIn(term, text)


if __name__ == "__main__":
    unittest.main()
