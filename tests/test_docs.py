# GHOST FIVE // VECTIS
# Regression coverage for the VECTIS docs contract.
from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
USER_GUIDE = ROOT / "docs" / "user-guide.md"
QUICKSTART = ROOT / "docs" / "quickstart.md"


class TestDocumentationContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.readme = README.read_text(encoding="utf-8")
        cls.user_guide = USER_GUIDE.read_text(encoding="utf-8")
        cls.quickstart = QUICKSTART.read_text(encoding="utf-8")

    def test_required_documentation_files_exist(self):
        for path in (
            README,
            USER_GUIDE,
            QUICKSTART,
        ):
            with self.subTest(path=path):
                self.assertTrue(path.is_file())
                self.assertGreater(path.stat().st_size, 0)

    def test_readme_mentions_vectis(self):
        self.assertIn(
            "vectis",
            self.readme.lower(),
        )

    def test_user_guide_mentions_vectis(self):
        self.assertIn(
            "vectis",
            self.user_guide.lower(),
        )

    def test_quickstart_mentions_vectis(self):
        self.assertIn(
            "vectis",
            self.quickstart.lower(),
        )

    def test_user_guide_documents_installation(self):
        self.assertIn(
            "install",
            self.user_guide.lower(),
        )

    def test_user_guide_documents_syntax(self):
        self.assertIn(
            "syntax",
            self.user_guide.lower(),
        )

    def test_user_guide_contains_example_concept(self):
        self.assertIn(
            "example",
            self.user_guide.lower(),
        )

    def test_user_guide_documents_diagnostics(self):
        self.assertIn(
            "diagnostic",
            self.user_guide.lower(),
        )

    def test_user_guide_documents_capabilities(self):
        self.assertIn(
            "capability",
            self.user_guide.lower(),
        )

    def test_user_guide_documents_run_workflow(self):
        self.assertIn(
            "run",
            self.user_guide.lower(),
        )

    def test_documentation_mentions_cli_commands(self):
        combined = (
            self.readme
            + "\n"
            + self.user_guide
            + "\n"
            + self.quickstart
        ).lower()

        for command in (
            "check",
            "parse",
            "plan",
            "run",
        ):
            with self.subTest(command=command):
                self.assertIn(command, combined)

    def test_documentation_mentions_source(self):
        combined = (
            self.user_guide
            + "\n"
            + self.quickstart
        ).lower()

        self.assertIn(
            "source",
            combined,
        )

    def test_documentation_mentions_runtime_or_execution(self):
        combined = (
            self.user_guide
            + "\n"
            + self.quickstart
        ).lower()

        self.assertTrue(
            "runtime" in combined
            or "execution" in combined
        )


if __name__ == "__main__":
    unittest.main()
