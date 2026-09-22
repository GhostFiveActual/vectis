# GHOST FIVE // VECTIS
# Regression coverage for value-free execution receipts and provenance.
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from vectis.compiler import compile_program
from vectis.parser import parse
from vectis.product import graph_fingerprint
from vectis.receipt import (
    RECEIPT_SCHEMA,
    execution_receipt,
    write_execution_receipt,
)
from vectis.runtime import Runtime


class ExecutionReceiptTests(unittest.TestCase):
    def compile(self, source: str):
        result = compile_program(
            parse(
                source,
                file="<receipt-test>",
            )
        )
        self.assertTrue(result.ok)
        self.assertIsNotNone(result.graph)
        return result.graph

    def test_receipt_separates_plan_and_run_evidence(
        self,
    ) -> None:
        graph = self.compile(
            'mission "Receipt" { '
            'source ready true; '
            'publish ready; }'
        )
        result = Runtime(graph).execute()

        receipt = execution_receipt(
            graph,
            result,
            source_name="/private/work/mission.vectis",
            recorded_at="2026-09-22T17:00:00Z",
        )

        self.assertEqual(
            receipt["schema"],
            RECEIPT_SCHEMA,
        )
        self.assertEqual(
            receipt["plan"]["fingerprint"],
            graph_fingerprint(graph),
        )
        self.assertEqual(
            receipt["evidence"]["recorded_at"],
            "2026-09-22T17:00:00Z",
        )
        self.assertEqual(
            receipt["provenance"]["source"],
            "mission.vectis",
        )
        self.assertFalse(
            receipt["provenance"][
                "runtime_values_recorded"
            ]
        )

    def test_receipt_does_not_persist_runtime_values(
        self,
    ) -> None:
        sensitive = "SENSITIVE-RECEIPT-VALUE"
        graph = self.compile(
            'mission "Receipt" { '
            f'source token "{sensitive}"; '
            'publish token; }'
        )
        result = Runtime(graph).execute()

        receipt = execution_receipt(
            graph,
            result,
            source_name="mission.vectis",
            recorded_at="2026-09-22T17:00:00Z",
        )
        rendered = json.dumps(
            receipt,
            sort_keys=True,
        )

        self.assertNotIn(sensitive, rendered)
        self.assertNotIn("node_values", rendered)
        self.assertNotIn("environment", rendered)

    def test_timestamp_does_not_change_plan_identity(
        self,
    ) -> None:
        graph = self.compile(
            'mission "Receipt" { '
            'source ready true; '
            'publish ready; }'
        )
        result = Runtime(graph).execute()

        first = execution_receipt(
            graph,
            result,
            source_name="mission.vectis",
            recorded_at="2026-09-22T17:00:00Z",
        )
        second = execution_receipt(
            graph,
            result,
            source_name="mission.vectis",
            recorded_at="2026-09-22T18:00:00Z",
        )

        self.assertEqual(
            first["plan"],
            second["plan"],
        )
        self.assertEqual(
            first["execution"],
            second["execution"],
        )
        self.assertNotEqual(
            first["evidence"],
            second["evidence"],
        )

    def test_failure_receipt_omits_failure_detail(
        self,
    ) -> None:
        graph = self.compile(
            'mission "Denied" { '
            'require "filesystem"; }'
        )
        result = Runtime(graph).execute()
        self.assertFalse(result.success)

        receipt = execution_receipt(
            graph,
            result,
            source_name="denied.vectis",
            recorded_at="2026-09-22T17:00:00Z",
        )
        rendered = json.dumps(
            receipt,
            sort_keys=True,
        )

        self.assertNotIn(
            "Capability 'filesystem' is unavailable",
            rendered,
        )
        self.assertEqual(
            receipt["execution"]["failures"][0][
                "category"
            ],
            "RuntimeExecutionError",
        )

    def test_writer_emits_stable_json(self) -> None:
        graph = self.compile(
            'mission "Receipt" { '
            'source ready true; '
            'publish ready; }'
        )
        result = Runtime(graph).execute()
        receipt = execution_receipt(
            graph,
            result,
            source_name="mission.vectis",
            recorded_at="2026-09-22T17:00:00Z",
        )

        with tempfile.TemporaryDirectory() as directory:
            destination = (
                Path(directory)
                / "evidence"
                / "receipt.json"
            )
            written = write_execution_receipt(
                destination,
                receipt,
            )

            self.assertEqual(
                written,
                destination.resolve(),
            )
            self.assertEqual(
                json.loads(
                    destination.read_text(
                        encoding="utf-8"
                    )
                ),
                receipt,
            )
            self.assertTrue(
                destination.read_text(
                    encoding="utf-8"
                ).endswith("\n")
            )


if __name__ == "__main__":
    unittest.main()
