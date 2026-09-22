<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# VECTIS RFC Process

The RFC process exists so language growth remains deliberate, reviewable, and compatible with VECTIS principles.

## Accepted RFCs

1. [RFC 0001: User-defined pure functions](0001-pure-functions.md)
2. [RFC 0002: Deterministic source modules](0002-deterministic-modules.md)
3. [RFC 0003: Explicit actions](0003-explicit-actions.md)
4. [RFC 0004: Explicit CLI action profiles](0004-action-profiles.md)

## When an RFC is required

An RFC is expected for changes that materially affect one or more of these contracts:

1. Grammar or syntax.
2. Semantic meaning.
3. Type or value models.
4. Execution graph structure or serialization.
5. Runtime scheduling or failure semantics.
6. Capability or authority boundaries.
7. Public CLI removal or incompatible output changes.
8. Public Python APIs that the project intends to support.
9. Module resolution, imports, user-defined functions, or bounded iteration.

A focused bug fix, documentation correction, test improvement, or internal refactor does not require an RFC when public behavior remains unchanged.

## Proposal content

An RFC should explain:

1. The problem and concrete use cases.
2. The proposed source syntax or public interface.
3. Semantic rules.
4. Determinism properties.
5. Authority and security impact.
6. Execution graph representation.
7. Diagnostics and failure behavior.
8. Compatibility and migration.
9. Alternatives considered.
10. Test and implementation strategy.

## Lifecycle

A design begins as a GitHub design proposal. If maintainers determine that the change affects a durable contract, the proposal becomes a numbered document under this directory.

Accepted RFCs describe the intended contract. Acceptance does not require immediate implementation.

An implemented RFC must be reflected in normative specifications, tests, release records, and compatibility documentation before release.

Rejected or superseded proposals may remain in the repository when they provide useful design history.

## Decision standard

A proposal should strengthen at least one of VECTIS core properties: explicit intent, inspectable structure, deterministic behavior, explicit authority, controlled execution, or verifiable outcomes.

Complexity alone is not a reason to add a feature.

## Security changes

Security restrictions may be adopted without waiting for a full RFC when delay would expose users to material risk. The resulting contract change must still be documented after the immediate fix.
