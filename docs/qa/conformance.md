<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# VECTIS Conformance

## Purpose

Conformance means the documented language and product contracts match executable behavior.

## Required surfaces

The VECTIS conformance suite covers:

1. Lexing and source positions.
2. Parsing and syntax tree invariants.
3. Semantic diagnostics.
4. Built in function behavior.
5. Compiler lowering.
6. Execution graph serialization and cycle rules.
7. Runtime scheduling and resolved values.
8. Assertions and conditional branches.
9. Capability behavior.
10. Filesystem, process, and HTTP adapter boundaries.
11. Canonical formatting.
12. CLI commands.
13. Project initialization and batch project testing.
14. VECTIS Studio.
15. Launch Control application.
16. HTML execution reporting.
17. Comprehensive showcase mission.
18. Large deterministic execution plans.
19. Documentation and repository policy.

## Source of truth

The executable source of truth is the automated test suite and tools/quality-gate.sh.

Documentation explains the contract. Tests prove the implemented contract.

## Supported Python versions

CI validates the current supported Python matrix declared by the package metadata.

A supported version is not considered validated until the complete repository quality gate, package build, and isolated wheel smoke test pass on that version.
