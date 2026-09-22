# GHOST FIVE // VECTIS
# Builds value-free execution receipts that separate plan identity from run evidence.
"""Execution receipts and provenance for VECTIS."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Iterable, Mapping

from vectis import __version__
from vectis.ir import ExecutionGraph
from vectis.product import (
    capability_manifest,
    graph_fingerprint,
    graph_summary,
)
from vectis.runtime import RuntimeResult


RECEIPT_SCHEMA = "vectis.execution-receipt/v1"


def execution_receipt(
    graph: ExecutionGraph,
    result: RuntimeResult,
    *,
    source_name: str,
    granted_capabilities: Iterable[str] = (),
    registered_actions: Iterable[Mapping[str, object]] = (),
    action_profile_attestation: Mapping[str, object] | None = None,
    recorded_at: str | None = None,
) -> dict[str, object]:
    """Build one value-free execution receipt."""
    if not isinstance(graph, ExecutionGraph):
        raise TypeError("graph must be an ExecutionGraph")
    if not isinstance(result, RuntimeResult):
        raise TypeError("result must be a RuntimeResult")
    if not isinstance(source_name, str) or not source_name:
        raise ValueError("source_name must be a non-empty string")

    timestamp = recorded_at
    if timestamp is None:
        timestamp = (
            datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z")
        )
    if not isinstance(timestamp, str) or not timestamp:
        raise ValueError("recorded_at must be a non-empty string")

    capabilities = sorted(
        {
            item
            for item in granted_capabilities
            if isinstance(item, str) and item
        }
    )

    action_records: list[dict[str, str]] = []
    for item in registered_actions:
        if not isinstance(item, Mapping):
            raise TypeError(
                "registered_actions must contain mapping values"
            )
        operation = item.get("operation")
        capability = item.get("capability")
        if (
            isinstance(operation, str)
            and operation
            and isinstance(capability, str)
            and capability
        ):
            action_records.append(
                {
                    "operation": operation,
                    "capability": capability,
                }
            )

    action_records.sort(
        key=lambda item: (
            item["operation"],
            item["capability"],
        )
    )

    provenance: dict[str, object] = {
        "vectis_version": __version__,
        "source": _safe_source_name(source_name),
        "granted_capabilities": capabilities,
        "registered_actions": action_records,
        "runtime_values_recorded": False,
    }

    if action_profile_attestation is not None:
        provenance[
            "action_profile_attestation"
        ] = _safe_profile_attestation(
            action_profile_attestation
        )

    return {
        "schema": RECEIPT_SCHEMA,
        "plan": {
            "fingerprint": graph_fingerprint(graph),
            "summary": graph_summary(graph),
            "authority": capability_manifest(graph),
        },
        "execution": {
            "status": result.status,
            "success": result.success,
            "dry_run": result.dry_run,
            "execution_order": list(result.execution_order),
            "node_states": [
                {
                    "node": node_id,
                    "state": state.value,
                }
                for node_id, state in result.node_states
            ],
            "failures": [
                {
                    "node": failure.node_id,
                    "category": _failure_category(
                        failure.message
                    ),
                }
                for failure in result.failures
            ],
        },
        "provenance": provenance,
        "evidence": {
            "recorded_at": timestamp,
        },
    }


def write_execution_receipt(
    path: str | Path,
    receipt: Mapping[str, object],
) -> Path:
    """Persist one receipt as stable UTF-8 JSON."""
    if not isinstance(receipt, Mapping):
        raise TypeError("receipt must be a mapping")

    destination = Path(path).expanduser().resolve()
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    destination.write_text(
        json.dumps(
            dict(receipt),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return destination


def _safe_profile_attestation(
    attestation: Mapping[str, object],
) -> dict[str, object]:
    """Copy only receipt-safe profile attestation fields."""
    if not isinstance(attestation, Mapping):
        raise TypeError(
            "action_profile_attestation must be a mapping"
        )

    schema = attestation.get("schema")
    algorithm = attestation.get("algorithm")
    scope = attestation.get("scope")
    fingerprint = attestation.get("fingerprint")
    source = attestation.get("source")
    secret_values = attestation.get(
        "secret_values_attested"
    )

    if not isinstance(schema, str) or not schema:
        raise ValueError(
            "profile attestation schema must be a non-empty string"
        )
    if algorithm != "sha256":
        raise ValueError(
            "profile attestation algorithm must be sha256"
        )
    if scope != "authority-shape":
        raise ValueError(
            "profile attestation scope must be authority-shape"
        )
    if (
        not isinstance(fingerprint, str)
        or len(fingerprint) != 64
        or any(
            character not in "0123456789abcdef"
            for character in fingerprint
        )
    ):
        raise ValueError(
            "profile attestation fingerprint must be 64 lowercase hex characters"
        )
    if not isinstance(source, str) or not source:
        raise ValueError(
            "profile attestation source must be a non-empty string"
        )
    if secret_values is not False:
        raise ValueError(
            "profile attestation must not claim secret value coverage"
        )

    return {
        "schema": schema,
        "algorithm": algorithm,
        "scope": scope,
        "fingerprint": fingerprint,
        "source": Path(source).name,
        "secret_values_attested": False,
    }


def _safe_source_name(source_name: str) -> str:
    """Return a source label without persisting local directory paths."""
    if source_name in {"-", "<stdin>"}:
        return "<stdin>"
    return Path(source_name).name


def _failure_category(message: str) -> str:
    """Return only the exception category from a runtime failure."""
    if not isinstance(message, str) or not message:
        return "RuntimeFailure"
    category, separator, _detail = message.partition(":")
    if separator and category:
        return category
    return "RuntimeFailure"


__all__ = [
    "RECEIPT_SCHEMA",
    "execution_receipt",
    "write_execution_receipt",
]
