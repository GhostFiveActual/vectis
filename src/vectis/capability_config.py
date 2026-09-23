# GHOST FIVE // VECTIS
# Compares compiled mission authority requirements with explicit runtime configuration.
"""Read-only capability configuration previews for VECTIS."""

from __future__ import annotations

from collections.abc import Iterable

from vectis.action_profile import ActionProfile
from vectis.ir import ExecutionGraph
from vectis.product import capability_manifest, graph_fingerprint
from vectis.profile_attestation import action_profile_attestation


CAPABILITY_CONFIGURATION_SCHEMA = (
    "vectis.capability-configuration/v1"
)


def capability_configuration(
    graph: ExecutionGraph,
    *,
    profile: ActionProfile | None = None,
    extra_capabilities: Iterable[str] = (),
) -> dict[str, object]:
    """Compare one compiled plan with explicit grants and action bindings."""
    if not isinstance(graph, ExecutionGraph):
        raise TypeError("graph must be an ExecutionGraph")
    if profile is not None and not isinstance(profile, ActionProfile):
        raise TypeError("profile must be an ActionProfile or None")

    extras: set[str] = set()
    for item in extra_capabilities:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(
                "extra capabilities must contain non-empty strings"
            )
        extras.add(item)

    configured = set(extras)
    registered: list[dict[str, str]] = []
    profile_view: dict[str, object] | None = None

    if profile is not None:
        configured.update(profile.capabilities)
        for item in profile.actions.manifest():
            operation = item.get("operation")
            capability = item.get("capability")
            if (
                isinstance(operation, str)
                and operation
                and isinstance(capability, str)
                and capability
            ):
                registered.append(
                    {
                        "operation": operation,
                        "capability": capability,
                    }
                )

        registered.sort(
            key=lambda item: (
                item["operation"],
                item["capability"],
            )
        )
        profile_view = {
            "source": profile.source.name,
            "capabilities": sorted(profile.capabilities),
            "operations": registered,
            "attestation": action_profile_attestation(profile),
        }

    authority = capability_manifest(graph)
    required = sorted(set(authority["required"]))
    requested = sorted(set(authority["requested"]))
    all_plan_capabilities = sorted(
        set(required) | set(requested)
    )

    missing_required = [
        item for item in required if item not in configured
    ]
    missing_requested = [
        item for item in requested if item not in configured
    ]

    registered_pairs = {
        (item["operation"], item["capability"])
        for item in registered
    }
    planned_actions = sorted(
        (
            {
                "node": str(item["node"]),
                "operation": str(item["operation"]),
                "capability": str(item["capability"]),
            }
            for item in authority["actions"]
        ),
        key=lambda item: (
            item["operation"],
            item["capability"],
            item["node"],
        ),
    )
    missing_actions = [
        item
        for item in planned_actions
        if (
            item["operation"],
            item["capability"],
        )
        not in registered_pairs
    ]

    unresolved = sorted(
        str(item)
        for item in authority["unresolved_nodes"]
    )
    configured_sorted = sorted(configured)

    satisfied = not (
        missing_required
        or missing_requested
        or missing_actions
        or unresolved
    )

    return {
        "schema": CAPABILITY_CONFIGURATION_SCHEMA,
        "fingerprint": graph_fingerprint(graph),
        "satisfied": satisfied,
        "plan": {
            "required_capabilities": required,
            "requested_capabilities": requested,
            "capabilities": all_plan_capabilities,
            "actions": planned_actions,
            "unresolved_nodes": unresolved,
        },
        "configuration": {
            "capabilities": configured_sorted,
            "extra_capabilities": sorted(extras),
            "profile": profile_view,
        },
        "missing": {
            "required_capabilities": missing_required,
            "requested_capabilities": missing_requested,
            "action_operations": missing_actions,
        },
        "unused_capabilities": [
            item
            for item in configured_sorted
            if item not in all_plan_capabilities
        ],
    }


__all__ = [
    "CAPABILITY_CONFIGURATION_SCHEMA",
    "capability_configuration",
]
