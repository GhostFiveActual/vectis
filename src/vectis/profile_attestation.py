# GHOST FIVE // VECTIS
# Produces deterministic non-secret fingerprints for explicit action profiles.
"""Action profile authority-shape attestation for VECTIS."""

from __future__ import annotations

import hashlib
import json
from typing import Mapping

from vectis.action_profile import (
    ActionProfile,
    profile_manifest,
)


PROFILE_ATTESTATION_SCHEMA = (
    "vectis.action-profile-attestation/v1"
)


def action_profile_descriptor(
    profile: ActionProfile,
) -> dict[str, object]:
    """Return the canonical non-secret authority shape."""
    if not isinstance(profile, ActionProfile):
        raise TypeError(
            "profile must be ActionProfile"
        )

    manifest = profile_manifest(profile)

    operations = sorted(
        (
            {
                "operation": str(item["operation"]),
                "capability": str(item["capability"]),
            }
            for item in manifest["operations"]
        ),
        key=lambda item: (
            item["operation"],
            item["capability"],
        ),
    )

    adapters = sorted(
        (
            _adapter_descriptor(item)
            for item in manifest["adapters"]
        ),
        key=lambda item: item["capability"],
    )

    return {
        "schema": PROFILE_ATTESTATION_SCHEMA,
        "scope": "authority-shape",
        "secret_values_attested": False,
        "capabilities": sorted(
            str(item)
            for item in manifest["capabilities"]
        ),
        "operations": operations,
        "adapters": adapters,
    }


def action_profile_fingerprint(
    profile: ActionProfile,
) -> str:
    """Return the SHA-256 fingerprint of the authority shape."""
    payload = json.dumps(
        action_profile_descriptor(profile),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def action_profile_attestation(
    profile: ActionProfile,
) -> dict[str, object]:
    """Return receipt-safe attestation metadata."""
    if not isinstance(profile, ActionProfile):
        raise TypeError(
            "profile must be ActionProfile"
        )

    return {
        "schema": PROFILE_ATTESTATION_SCHEMA,
        "algorithm": "sha256",
        "scope": "authority-shape",
        "fingerprint": action_profile_fingerprint(
            profile
        ),
        "source": profile.source.name,
        "secret_values_attested": False,
    }


def _adapter_descriptor(
    item: Mapping[str, object],
) -> dict[str, object]:
    capability = item.get("capability")

    if capability == "filesystem":
        return {
            "capability": "filesystem",
            "roots": sorted(
                str(value)
                for value in item.get(
                    "roots",
                    (),
                )
            ),
        }

    if capability == "process":
        return {
            "capability": "process",
            "executables": sorted(
                str(value)
                for value in item.get(
                    "executables",
                    (),
                )
            ),
            "environment_keys": sorted(
                str(value)
                for value in item.get(
                    "environment_keys",
                    (),
                )
            ),
            "default_timeout": float(
                item["default_timeout"]
            ),
            "max_timeout": float(
                item["max_timeout"]
            ),
        }

    if capability == "http":
        return {
            "capability": "http",
            "allowed_hosts": sorted(
                str(value)
                for value in item.get(
                    "allowed_hosts",
                    (),
                )
            ),
            "default_timeout": float(
                item["default_timeout"]
            ),
            "max_timeout": float(
                item["max_timeout"]
            ),
        }

    raise ValueError(
        "unsupported action profile capability "
        f"for attestation: {capability!r}"
    )


__all__ = [
    "PROFILE_ATTESTATION_SCHEMA",
    "action_profile_attestation",
    "action_profile_descriptor",
    "action_profile_fingerprint",
]
