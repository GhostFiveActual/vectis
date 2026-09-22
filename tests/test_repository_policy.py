# GHOST FIVE // VECTIS
# Regression coverage for the VECTIS repository policy.

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "tools" / "repository-policy.py"


def load_policy():
    """Load the policy script without requiring tools to be a package."""
    spec = importlib.util.spec_from_file_location(
        "vectis_repository_policy",
        POLICY,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load repository policy")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RepositoryPolicyTests(unittest.TestCase):
    """Protect Ghost Five branding and repository cleanliness contracts."""

    def test_policy_passes_current_repository(self):
        policy = load_policy()
        self.assertEqual(policy.main(), 0)

    def test_every_markdown_file_has_brand_marker(self):
        policy = load_policy()

        for path in ROOT.rglob("*.md"):
            if any(part in policy.SKIP_PARTS for part in path.parts):
                continue

            with self.subTest(path=path):
                head = "\n".join(
                    path.read_text(encoding="utf-8").splitlines()[:12]
                )
                self.assertIn(policy.BRAND, head)
                self.assertIn(policy.SLOGAN, head)


if __name__ == "__main__":
    unittest.main()
