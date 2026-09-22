# GHOST FIVE // VECTIS
# Verifies compile-time validation for standard action contracts.
from __future__ import annotations

import unittest

from vectis.action_contract import standard_action_manifest
from vectis.diagnostic import DiagnosticCode
from vectis.parser import parse
from vectis.semantic import SemanticAnalyzer, ValueType


class ActionContractSemanticTests(unittest.TestCase):
    def analyze(self, source: str):
        return SemanticAnalyzer(
            parse(
                source,
                file="action-contract.vectis",
            )
        ).result()

    def test_standard_manifest_exposes_schema(self) -> None:
        contracts = {
            item["operation"]: item
            for item in standard_action_manifest()
        }
        read = contracts["filesystem.read_text"]
        self.assertEqual(
            read["input"]["fields"][0]["name"],
            "path",
        )
        self.assertEqual(
            read["result"]["type"],
            "string",
        )

    def test_standard_action_result_type_is_inferred(
        self,
    ) -> None:
        result = self.analyze(
            'mission "Read" {\n'
            '    action content "filesystem.read_text" '
            'using "filesystem" {\n'
            '        path: "input.txt"\n'
            '    };\n'
            '    publish content;\n'
            '}\n'
        )
        self.assertTrue(result.ok)
        self.assertIn(
            ("content", ValueType.STRING),
            result.declarations,
        )

    def test_missing_required_field_is_rejected(
        self,
    ) -> None:
        result = self.analyze(
            'mission "Read" {\n'
            '    action content "filesystem.read_text" '
            'using "filesystem" {};\n'
            '}\n'
        )
        self.assertFalse(result.ok)
        self.assertTrue(
            any(
                item.code
                is DiagnosticCode.SEM_ACTION_CONTRACT
                and "requires field 'path'" in item.message
                for item in result.diagnostics
            )
        )

    def test_static_field_type_is_rejected(self) -> None:
        result = self.analyze(
            'mission "Read" {\n'
            '    action content "filesystem.read_text" '
            'using "filesystem" {\n'
            '        path: 42\n'
            '    };\n'
            '}\n'
        )
        self.assertFalse(result.ok)
        self.assertTrue(
            any(
                item.code
                is DiagnosticCode.SEM_ACTION_CONTRACT
                and "path must be string" in item.message
                for item in result.diagnostics
            )
        )

    def test_unknown_standard_field_is_rejected(
        self,
    ) -> None:
        result = self.analyze(
            'mission "Read" {\n'
            '    action content "filesystem.read_text" '
            'using "filesystem" {\n'
            '        path: "input.txt",\n'
            '        typo: true\n'
            '    };\n'
            '}\n'
        )
        self.assertFalse(result.ok)
        self.assertTrue(
            any(
                item.code
                is DiagnosticCode.SEM_ACTION_CONTRACT
                and "unsupported field 'typo'" in item.message
                for item in result.diagnostics
            )
        )

    def test_standard_capability_mismatch_is_rejected(
        self,
    ) -> None:
        result = self.analyze(
            'mission "Read" {\n'
            '    action content "filesystem.read_text" '
            'using "http" {\n'
            '        path: "input.txt"\n'
            '    };\n'
            '}\n'
        )
        self.assertFalse(result.ok)
        self.assertTrue(
            any(
                item.code
                is DiagnosticCode.SEM_ACTION_CONTRACT
                and "requires capability 'filesystem'"
                in item.message
                for item in result.diagnostics
            )
        )

    def test_collection_item_contract_is_checked(
        self,
    ) -> None:
        result = self.analyze(
            'mission "Process" {\n'
            '    action result "process.run" using "process" {\n'
            '        executable: "python",\n'
            '        arguments: ["ok", 42]\n'
            '    };\n'
            '}\n'
        )
        self.assertFalse(result.ok)
        self.assertTrue(
            any(
                item.code
                is DiagnosticCode.SEM_ACTION_CONTRACT
                and "arguments[1] must be string"
                in item.message
                for item in result.diagnostics
            )
        )

    def test_custom_operation_remains_extensible(
        self,
    ) -> None:
        result = self.analyze(
            'mission "Custom" {\n'
            '    action result "custom.lookup" using "custom" {\n'
            '        key: "value"\n'
            '    };\n'
            '    publish result;\n'
            '}\n'
        )
        self.assertTrue(result.ok)
        self.assertIn(
            ("result", ValueType.UNKNOWN),
            result.declarations,
        )


if __name__ == "__main__":
    unittest.main()
