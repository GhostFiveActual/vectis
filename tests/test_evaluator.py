# GHOST FIVE // VECTIS
# Regression coverage for the VECTIS evaluator contract.
from __future__ import annotations

import unittest

from vectis.evaluator import EvaluationError, builtin_manifest, evaluate_expression
from vectis.parser import parse_expression


class EvaluatorTests(unittest.TestCase):
    def evaluate(self, source: str, values=None):
        return evaluate_expression(
            parse_expression(source, file="<evaluator-test>"),
            values or {},
        )

    def test_arithmetic_and_comparison(self):
        self.assertEqual(self.evaluate("2 + 3 * 4"), 14)
        self.assertTrue(self.evaluate("14 >= 14"))
        self.assertTrue(self.evaluate("15 > 14"))
        self.assertTrue(self.evaluate("13 < 14"))
        self.assertEqual(self.evaluate("14 % 5"), 4)

    def test_boolean_logic(self):
        self.assertTrue(self.evaluate("true && !false"))
        self.assertFalse(self.evaluate("false || false"))

    def test_reference_environment(self):
        self.assertEqual(
            self.evaluate("x + y", {"x": 5, "y": 7}),
            12,
        )

    def test_string_builtins(self):
        self.assertEqual(
            self.evaluate('upper(trim("  vectis  "))'),
            "VECTIS",
        )
        self.assertTrue(
            self.evaluate('contains("Ghost Five", "Five")')
        )
        self.assertEqual(
            self.evaluate('concat("Ghost", " ", "Five")'),
            "Ghost Five",
        )

    def test_numeric_builtins(self):
        self.assertEqual(self.evaluate("max(4, 9, 2)"), 9)
        self.assertEqual(self.evaluate("min(4, 9, 2)"), 2)
        self.assertEqual(self.evaluate("abs(-12)"), 12)
        self.assertEqual(self.evaluate("round(3.14159, 2)"), 3.14)

    def test_conversion_builtins(self):
        self.assertEqual(self.evaluate('number("42")'), 42)
        self.assertEqual(self.evaluate("string(true)"), "true")
        self.assertTrue(self.evaluate('boolean("yes")'))

    def test_aggregate_builtins(self):
        self.assertTrue(
            self.evaluate("all_true(true, true, true)")
        )
        self.assertFalse(
            self.evaluate("all_true(true, false, true)")
        )
        self.assertTrue(
            self.evaluate("any_true(false, false, true)")
        )
        self.assertEqual(
            self.evaluate("count_true(true, false, true, true)"),
            3,
        )
        self.assertEqual(
            self.evaluate("average(80, 90, 100)"),
            90,
        )
        self.assertEqual(
            self.evaluate("percent(45, 60)"),
            75,
        )

    def test_structured_list_and_object_values(self):
        build = self.evaluate(
            'object("passed", true, "coverage", 94, '
            '"checks", list(true, true, false))'
        )
        self.assertEqual(
            build,
            {
                "passed": True,
                "coverage": 94,
                "checks": (True, True, False),
            },
        )
        self.assertTrue(
            self.evaluate(
                'get(build, "passed")',
                {"build": build},
            )
        )
        self.assertEqual(
            self.evaluate(
                'get(build, "coverage")',
                {"build": build},
            ),
            94,
        )
        self.assertEqual(
            self.evaluate(
                'get(get(build, "checks"), 1)',
                {"build": build},
            ),
            True,
        )

    def test_structured_collection_helpers(self):
        value = self.evaluate(
            'object("first", 10, "second", 20)'
        )
        self.assertEqual(
            self.evaluate("keys(value)", {"value": value}),
            ("first", "second"),
        )
        self.assertEqual(
            self.evaluate("values(value)", {"value": value}),
            (10, 20),
        )
        self.assertEqual(
            self.evaluate("size(value)", {"value": value}),
            2,
        )
        self.assertTrue(
            self.evaluate(
                'has(value, "second")',
                {"value": value},
            )
        )
        self.assertTrue(
            self.evaluate("all(list(true, true, true))")
        )
        self.assertTrue(
            self.evaluate("any(list(false, true, false))")
        )

    def test_structured_get_default_and_validation(self):
        self.assertEqual(
            self.evaluate(
                'get(object("ready", true), "missing", "fallback")'
            ),
            "fallback",
        )
        with self.assertRaises(EvaluationError):
            self.evaluate('object("a", 1, "a", 2)')
        with self.assertRaises(EvaluationError):
            self.evaluate('get(list(1, 2), 8)')
        with self.assertRaises(EvaluationError):
            self.evaluate('all(list(true, 1))')

    def test_unknown_builtin_is_rejected(self):
        with self.assertRaises(EvaluationError):
            self.evaluate("does_not_exist(1)")

    def test_builtin_manifest_is_stable_and_nonempty(self):
        manifest = builtin_manifest()
        self.assertGreaterEqual(len(manifest), 10)
        self.assertEqual(
            [item["name"] for item in manifest],
            sorted(item["name"] for item in manifest),
        )


if __name__ == "__main__":
    unittest.main()
