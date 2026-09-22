<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# Compatibility

VECTIS treats language meaning, deterministic planning, explicit authority, and observable runtime behavior as public contracts. Compatibility changes are evaluated against those contracts rather than only against implementation details.

## Version model

VECTIS follows semantic versioning with additional rules for the pre-1.0 language period.

| Version change | Contract |
| --- | --- |
| Patch within a 0.x line | Bug fixes, diagnostics, performance, documentation, and additive behavior that preserves the documented language and public command contracts. |
| Minor before 1.0 | May add language features or deliberately revise a pre-1.0 contract when release notes provide migration guidance. |
| Major at or after 1.0 | Required for incompatible changes to stable public contracts. |
| Minor at or after 1.0 | Additive compatible behavior. |
| Patch at or after 1.0 | Compatible corrections and maintenance. |

## 0.7 compatibility line

Within the 0.7 patch line:

1. Valid 0.2, 0.3, 0.4, 0.5, 0.6, and 0.7 source remains valid unless a security correction requires otherwise.
2. Existing syntax does not silently change meaning.
3. Existing documented CLI commands are not removed.
4. Existing structured JSON fields are not removed or repurposed.
5. Execution graph serialization remains versioned and changes require explicit compatibility handling.
6. Capability names do not acquire additional authority without an explicit contract change.
7. Python 3.11 through 3.14 remain supported unless a documented platform constraint makes continued support impossible.

## Module compatibility

Within the 0.5 patch line, import paths resolve relative to the importing file and remain bounded by the nearest project root containing `vectis.toml`, or the entry file directory when no project manifest exists.

Imported modules may contain only imports and top-level pure function declarations. Import cycles fail closed. The same canonical module path is loaded once per compilation. Module loading remains a compile-time source operation and does not acquire runtime filesystem capability.

## Structured syntax compatibility

Within the 0.5 patch line, list literals, object literals, member access, and index access retain deterministic value semantics. Existing structured-value built-ins such as `list(...)`, `object(...)`, and `get(...)` remain valid and are not silently reinterpreted.

Object member order follows source order for deterministic serialization and reporting. Member access requires an object, list indexing requires an integer, and object indexing requires a string key.

## Pure function compatibility

Within the 0.5 patch line, top-level pure-function declarations preserve their parameter order, exact arity, local-only reference scope, acyclic call requirement, compile-time expansion behavior, and authority-free contract.

Function declarations do not become runtime action nodes. A patch release cannot make a pure function capture ambient mission values or acquire capability authority.

## Action compatibility

Within the 0.6 patch line, an action continues to bind one result identifier, name one operation, explicitly name one required capability, and accept one object input expression.

Action operations do not gain authority from their names. Runtime execution requires an explicit capability grant plus a registered operation bound to that same capability. Missing operations, missing grants, capability mismatches, and results outside the VECTIS value model continue to fail closed.

The standard filesystem, process, and HTTP bindings remain constrained by their adapter boundaries. A patch release cannot silently broaden configured roots, executable allowlists, environment inheritance, timeout ceilings, redirects, proxy use, or equivalent authority boundaries.

## CLI action profile compatibility

Within the 0.7 patch line, action authority profiles remain opt-in through an explicit command-line path. VECTIS does not automatically load an authority profile from the working directory, project manifest, environment, or user home directory.

Filesystem roots remain bounded by the configured profile, process executables remain explicit absolute allowlist entries, and HTTP profile configuration continues to require explicit hostnames. Profile inspection does not expose configured process environment values.

## Determinism contract

For the same VECTIS version, source text, explicit input values, capability configuration, and deterministic handler results, compilation produces the same canonical execution graph and plan fingerprint.

The runtime preserves deterministic graph ordering and branch selection. External systems contacted by explicit adapters can change independently of VECTIS. Their behavior is not represented as deterministic unless the embedding application supplies deterministic results.

## Deprecation

Before 1.0, a documented public contract may be removed only in a later minor version. The deprecation must be recorded in the release record and migration guidance before removal whenever the old behavior can safely remain available.

At or after 1.0, incompatible removal requires a major version.

Security defects can require faster removal or restriction. When that happens, release notes must explain the affected contract, the security reason, and the migration path.

## Python package surface

The command line interface, language specification, serialized public outputs, documented adapters, and explicitly documented Python symbols form the supported surface.

Undocumented internal Python modules and implementation details may change without a compatibility guarantee. Contributors should not expose internal implementation details as stable public APIs without documenting and testing that commitment.

## Serialization

Serialized execution graphs carry a format version. Readers must reject unsupported versions rather than guessing at semantics.

When a future graph format changes incompatibly, VECTIS must either provide an explicit migration path or emit a distinct format version.

## Migration evidence

A compatibility-affecting pull request must include:

1. The public contract being changed.
2. The reason the existing contract is insufficient.
3. Examples showing old and proposed behavior.
4. Determinism and authority analysis.
5. Migration guidance.
6. Regression tests for both preserved and deliberately changed behavior.
