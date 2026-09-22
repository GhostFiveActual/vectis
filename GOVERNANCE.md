<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# Governance

## Project stewardship

VECTIS is maintained under the Ghost Five project identity. Repository maintainers are responsible for language compatibility, security boundaries, release quality, contribution review, and final merge authority.

## Contribution model

Contributions are reviewed on technical merit, compatibility, determinism, security impact, test evidence, and documentation quality.

A contribution does not need to preserve an existing implementation when a stronger design is demonstrated, but it must preserve or deliberately revise the documented contract.

## Decision process

Routine changes are accepted through pull request review and passing CI.

Changes to grammar, semantic meaning, runtime authority, capability boundaries, package compatibility, or security invariants require explicit maintainer approval and supporting regression coverage.

## Compatibility and language evolution

Public contracts are governed by [COMPATIBILITY.md](COMPATIBILITY.md). Durable changes to grammar, semantics, value models, execution graph structure, authority boundaries, serialization, or supported public APIs use the RFC process defined in [docs/rfcs/README.md](docs/rfcs/README.md).

Maintainers may reject a technically working change when it weakens determinism, obscures authority, breaks compatibility without sufficient migration value, or creates a maintenance burden that exceeds its user value.

## Releases

Release tags are immutable. A release is accepted only when the repository quality gate, supported Python matrix, package build, isolated installation, documentation, and security requirements pass.

## Ownership

The repository uses CODEOWNERS to identify the default maintainer review path. Maintainer ownership does not prevent outside contribution, discussion, or design proposals.
