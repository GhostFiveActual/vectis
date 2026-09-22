# GHOST FIVE // VECTIS
# Regression coverage for the VECTIS bootstrap contract.
from __future__ import annotations

import unittest

import vectis
from vectis.cli import build_parser


class BootstrapTests(unittest.TestCase):
    def test_version_is_defined(self) -> None:
        self.assertTrue(vectis.__version__)

    def test_cli_name(self) -> None:
        self.assertEqual(build_parser().prog, "vectis")


if __name__ == "__main__":
    unittest.main()
