# GHOST FIVE // VECTIS
# Projects explicit value-free execution receipts into deterministic history views.
"""Deterministic execution history over persisted VECTIS receipts."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
import json
from pathlib import Path

from vectis.receipt import RECEIPT_SCHEMA


HISTORY_SCHEMA = "vectis.execution-history/v1"
_MAX_HISTORY_LIMIT = 1000
_SUMMARY_INTEGER_FIELDS = (
    "nodes",
    "edges",
    "branch_edges",
    "stage_count",
    "depth",
    "levels",
    "max_width",
    "max_fan_in",
    "max_fan_out",
)


def execution_history(
    directory: str | Path,
    *,
    limit: int = 50,
) -> dict[str, object]:
    """Project receipt files in one directory into deterministic history entries."""
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise TypeError("limit must be an integer")
    if not 1 <= limit <= _MAX_HISTORY_LIMIT:
        raise ValueError(
            f"limit must be between 1 and {_MAX_HISTORY_LIMIT}"
        )

    root = Path(directory).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("history directory must exist and be a directory")

    entries: list[dict[str, object]] = []
    rejected: list[dict[str, str]] = []

    for candidate in sorted(
        root.iterdir(),
        key=lambda item: item.name,
    ):
        if candidate.suffix.lower() != ".json":
            continue
        if candidate.is_symlink():
            rejected.append(
                {
                    "receipt": candidate.name,
                    "reason": "symlink_not_allowed",
                }
            )
            continue
        if not candidate.is_file():
            continue

        try:
            payload = json.loads(
                candidate.read_text(
                    encoding="utf-8",
                )
            )
            entries.append(
                _history_entry(
                    candidate.name,
                    payload,
                )
            )
        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ):
            rejected.append(
                {
                    "receipt": candidate.name,
                    "reason": "invalid_execution_receipt",
                }
            )

    entries.sort(
        key=lambda item: (
            str(item["recorded_at"]),
            str(item["receipt"]),
        ),
        reverse=True,
    )

    total = len(entries)
    selected = entries[:limit]

    return {
        "schema": HISTORY_SCHEMA,
        "total": total,
        "returned": len(selected),
        "rejected": rejected,
        "entries": selected,
    }


def _history_entry(
    receipt_name: str,
    payload: object,
) -> dict[str, object]:
    receipt = _mapping(
        payload,
        "receipt",
    )
    if receipt.get("schema") != RECEIPT_SCHEMA:
        raise ValueError("unsupported receipt schema")

    plan = _mapping(
        receipt.get("plan"),
        "plan",
    )
    execution = _mapping(
        receipt.get("execution"),
        "execution",
    )
    provenance = _mapping(
        receipt.get("provenance"),
        "provenance",
    )
    evidence = _mapping(
        receipt.get("evidence"),
        "evidence",
    )

    fingerprint = _sha256(
        plan.get("fingerprint"),
        "plan fingerprint",
    )
    summary_input = _mapping(
        plan.get("summary"),
        "plan summary",
    )
    summary_fingerprint = _sha256(
        summary_input.get("fingerprint"),
        "plan summary fingerprint",
    )
    if summary_fingerprint != fingerprint:
        raise ValueError(
            "plan summary fingerprint must match plan fingerprint"
        )
    summary = _summary_projection(
        summary_input
    )

    status = _string(
        execution.get("status"),
        "execution status",
    )
    if status not in {
        "success",
        "failure",
    }:
        raise ValueError(
            "execution status must be success or failure"
        )
    success = execution.get("success")
    dry_run = execution.get("dry_run")
    if not isinstance(success, bool):
        raise TypeError(
            "execution success must be a bool"
        )
    if not isinstance(dry_run, bool):
        raise TypeError(
            "execution dry_run must be a bool"
        )
    if success != (status == "success"):
        raise ValueError(
            "execution status and success flag must agree"
        )

    node_states = execution.get(
        "node_states"
    )
    if not isinstance(node_states, list):
        raise TypeError(
            "execution node_states must be a list"
        )
    state_counts: Counter[str] = Counter()
    for item in node_states:
        record = _mapping(
            item,
            "node state",
        )
        state_counts[
            _string(
                record.get("state"),
                "node state value",
            )
        ] += 1

    failures = execution.get("failures")
    if not isinstance(failures, list):
        raise TypeError(
            "execution failures must be a list"
        )
    failure_categories: set[str] = set()
    for item in failures:
        record = _mapping(
            item,
            "failure",
        )
        failure_categories.add(
            _string(
                record.get("category"),
                "failure category",
            )
        )

    if (
        provenance.get(
            "runtime_values_recorded"
        )
        is not False
    ):
        raise ValueError(
            "receipt must not record runtime values"
        )

    source = _string(
        provenance.get("source"),
        "receipt source",
    )
    capabilities_raw = provenance.get(
        "granted_capabilities"
    )
    if not isinstance(
        capabilities_raw,
        list,
    ):
        raise TypeError(
            "granted_capabilities must be a list"
        )
    capabilities = sorted(
        {
            _string(
                item,
                "capability",
            )
            for item in capabilities_raw
        }
    )

    recorded_at = _string(
        evidence.get("recorded_at"),
        "recorded_at",
    )

    profile = provenance.get(
        "action_profile_attestation"
    )
    profile_fingerprint: str | None = None
    if profile is not None:
        profile_mapping = _mapping(
            profile,
            "action profile attestation",
        )
        profile_fingerprint = _sha256(
            profile_mapping.get(
                "fingerprint"
            ),
            "profile fingerprint",
        )

    entry: dict[str, object] = {
        "receipt": receipt_name,
        "recorded_at": recorded_at,
        "source": source,
        "fingerprint": fingerprint,
        "status": status,
        "success": success,
        "dry_run": dry_run,
        "summary": summary,
        "state_counts": dict(
            sorted(
                state_counts.items()
            )
        ),
        "failure_categories": sorted(
            failure_categories
        ),
        "granted_capabilities": capabilities,
    }
    if profile_fingerprint is not None:
        entry[
            "profile_fingerprint"
        ] = profile_fingerprint
    return entry


def _summary_projection(
    value: object,
) -> dict[str, object]:
    summary = _mapping(
        value,
        "plan summary",
    )
    projected: dict[str, object] = {}

    for key in _SUMMARY_INTEGER_FIELDS:
        item = summary.get(key)
        if (
            isinstance(item, bool)
            or not isinstance(item, int)
            or item < 0
        ):
            raise TypeError(
                f"plan summary {key} must be a non-negative integer"
            )
        projected[key] = item

    node_kinds = _mapping(
        summary.get("node_kinds"),
        "plan summary node_kinds",
    )
    normalized_kinds: dict[str, int] = {}
    for key, value in node_kinds.items():
        name = _string(
            key,
            "node kind",
        )
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
        ):
            raise TypeError(
                "node kind counts must be non-negative integers"
            )
        normalized_kinds[name] = value

    projected["node_kinds"] = dict(
        sorted(
            normalized_kinds.items()
        )
    )
    return projected


def _mapping(
    value: object,
    label: str,
) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(
            f"{label} must be a mapping"
        )
    return value


def _string(
    value: object,
    label: str,
) -> str:
    if (
        not isinstance(value, str)
        or not value
    ):
        raise TypeError(
            f"{label} must be a non-empty string"
        )
    return value


def _sha256(
    value: object,
    label: str,
) -> str:
    text = _string(
        value,
        label,
    )
    if (
        len(text) != 64
        or any(
            character
            not in "0123456789abcdef"
            for character in text
        )
    ):
        raise ValueError(
            f"{label} must be 64 lowercase hexadecimal characters"
        )
    return text


__all__ = [
    "HISTORY_SCHEMA",
    "execution_history",
]
