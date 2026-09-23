<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# RFC 0015: Capability Configuration Preview

## Summary

VECTIS can compare a compiled mission with explicit capability grants and an optional action profile without executing the mission or granting authority.

## Problem

Action profiles describe bounded runtime adapters, while execution graphs describe the authority a mission requires. Operators need one deterministic view that explains whether an explicit configuration can satisfy the compiled plan before execution begins.

The preview must not turn profile inspection into ambient discovery, automatic grants, or hidden execution.

## Configuration contract

`vectis.capability_config` accepts a compiled execution graph, an optional explicit `ActionProfile`, and zero or more explicit capability names.

The preview reports the plan fingerprint, required and requested capability names, planned action operation and capability pairs, configured capability names, registered profile operations, missing authority, unused grants, unresolved authority nodes, and the existing profile-shape attestation when a profile is supplied.

`satisfied` is true only when all required and requested capabilities are configured, all planned action operation and capability pairs are registered by the selected profile, and the compiled capability manifest contains no unresolved authority nodes.

## CLI

`vectis capability-config FILE` compiles one mission and emits the capability configuration preview as JSON.

`--actions-config FILE` selects one explicit action profile. `--capability NAME` adds an explicit capability grant for preview purposes and may be repeated.

The command exits successfully when the preview is satisfied and exits with status 1 when authority is incomplete. It performs no runtime execution.

## Editor integration

The language server advertises `vectis.capabilities.inspect` through `workspace/executeCommand`.

Clients pass one argument object containing a file-backed document `uri`, an optional relative `profile`, and an optional `capabilities` array.

Mission compilation uses the current overlay-aware editor workspace. A profile path is resolved inside the selected document's VECTIS project root. Absolute profile paths and paths that resolve outside that root are rejected.

## Authority and security

Capability preview never creates a `CapabilityRegistry`, invokes an action, grants runtime authority, or selects a profile for later execution.

Profile output includes only the profile filename, capability names, registered operation and capability pairs, and the existing non-secret profile attestation. Filesystem roots, executable paths, environment values, and other local adapter values are excluded.

Execution continues to require explicit runtime options such as `--actions-config` and `--capability`.

## Determinism

Preview output derives only from the compiled execution graph, explicit capability names, and the selected action profile's registered authority shape.

Lists are normalized deterministically, and the plan identity is the canonical graph fingerprint.

## Compatibility

Source syntax, compiler IR, runtime scheduling, action-profile loading, capability enforcement, receipt schemas, package version, and published releases do not change.

The feature is additive to CLI and editor inspection surfaces.

## Test strategy

Tests cover matching profiles, missing capabilities, direct explicit grants, unregistered custom action operations, CLI exit behavior, overlay-aware editor compilation, project-bounded profile resolution, secret-free projection, repository policy, and the complete test suite.
