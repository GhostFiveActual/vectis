# GHOST FIVE // VECTIS
# Verifies deterministic value-free execution history projection.
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from vectis.history import (
    HISTORY_SCHEMA,
    execution_history,
)


class ExecutionHistoryTests(unittest.TestCase):
    def receipt(
        self,
        *,
        recorded_at: str,
        source: str = "mission.vectis",
        success: bool = True,
        sensitive: str | None = None,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": "vectis.execution-receipt/v1",
            "plan": {
                "fingerprint": "a" * 64,
                "summary": {
                    "nodes": 3,
                    "edges": 2,
                    "branch_edges": 0,
                    "stage_count": 1,
                    "stages": ["Mission"],
                    "depth": 2,
                    "levels": 3,
                    "max_width": 1,
                    "max_fan_in": 1,
                    "max_fan_out": 1,
                    "sources": ["source"],
                    "sinks": ["publish"],
                    "node_kinds": {
                        "publish": 1,
                        "source": 1,
                        "let": 1,
                    },
                    "fingerprint": "a" * 64,
                    "topological_order": [
                        "source",
                        "let",
                        "publish",
                    ],
                },
                "authority": {},
            },
            "execution": {
                "status": (
                    "success"
                    if success
                    else "failure"
                ),
                "success": success,
                "dry_run": False,
                "execution_order": [
                    "source",
                    "let",
                    "publish",
                ],
                "node_states": [
                    {
                        "node": "source",
                        "state": "succeeded",
                    },
                    {
                        "node": "let",
                        "state": "succeeded",
                    },
                    {
                        "node": "publish",
                        "state": (
                            "succeeded"
                            if success
                            else "failed"
                        ),
                    },
                ],
                "failures": (
                    []
                    if success
                    else [
                        {
                            "node": "publish",
                            "category": "RuntimeFailure",
                        }
                    ]
                ),
            },
            "provenance": {
                "vectis_version": "0.8.0",
                "source": source,
                "granted_capabilities": [
                    "filesystem",
                ],
                "registered_actions": [],
                "runtime_values_recorded": False,
            },
            "evidence": {
                "recorded_at": recorded_at,
            },
        }
        if sensitive is not None:
            payload["runtime_values"] = {
                "secret": sensitive,
            }
        return payload

    def test_history_is_newest_first_and_limited(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, timestamp in (
                ("first.json", "2026-09-23T12:00:00Z"),
                ("second.json", "2026-09-23T13:00:00Z"),
                ("third.json", "2026-09-23T14:00:00Z"),
            ):
                (root / name).write_text(
                    json.dumps(
                        self.receipt(
                            recorded_at=timestamp,
                        )
                    ),
                    encoding="utf-8",
                )

            result = execution_history(
                root,
                limit=2,
            )

            self.assertEqual(
                result["schema"],
                HISTORY_SCHEMA,
            )
            self.assertEqual(
                result["total"],
                3,
            )
            self.assertEqual(
                [
                    item["receipt"]
                    for item
                    in result["entries"]
                ],
                [
                    "third.json",
                    "second.json",
                ],
            )

    def test_history_projects_only_value_free_fields(self) -> None:
        sensitive = "DO-NOT-RETURN-HISTORY-VALUE"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "run.json").write_text(
                json.dumps(
                    self.receipt(
                        recorded_at=(
                            "2026-09-23T12:00:00Z"
                        ),
                        sensitive=sensitive,
                    )
                ),
                encoding="utf-8",
            )

            result = execution_history(root)
            rendered = json.dumps(
                result,
                sort_keys=True,
            )

            self.assertNotIn(
                sensitive,
                rendered,
            )
            entry = result["entries"][0]
            self.assertEqual(
                entry["state_counts"][
                    "succeeded"
                ],
                3,
            )
            self.assertEqual(
                entry["granted_capabilities"],
                ["filesystem"],
            )
            self.assertNotIn(
                "execution_order",
                entry,
            )

    def test_invalid_receipts_are_rejected_without_contents(self) -> None:
        sensitive = "INVALID-JSON-SECRET"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "broken.json").write_text(
                '{"secret":"' + sensitive,
                encoding="utf-8",
            )

            result = execution_history(root)
            rendered = json.dumps(
                result,
                sort_keys=True,
            )

            self.assertEqual(
                result["entries"],
                [],
            )
            self.assertEqual(
                result["rejected"],
                [
                    {
                        "receipt": "broken.json",
                        "reason": (
                            "invalid_execution_receipt"
                        ),
                    }
                ],
            )
            self.assertNotIn(
                sensitive,
                rendered,
            )

    def test_history_rejects_receipts_that_claim_runtime_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = self.receipt(
                recorded_at="2026-09-23T12:00:00Z",
            )
            receipt["provenance"][
                "runtime_values_recorded"
            ] = True
            (root / "unsafe.json").write_text(
                json.dumps(receipt),
                encoding="utf-8",
            )

            result = execution_history(root)

            self.assertEqual(
                result["entries"],
                [],
            )
            self.assertEqual(
                result["rejected"][0][
                    "receipt"
                ],
                "unsafe.json",
            )

    def test_history_limit_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(
                ValueError
            ):
                execution_history(
                    root,
                    limit=0,
                )
            with self.assertRaises(
                ValueError
            ):
                execution_history(
                    root,
                    limit=1001,
                )


if __name__ == "__main__":
    unittest.main()
