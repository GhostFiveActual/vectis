<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# VECTIS Project Direction

VECTIS is designed around deterministic planning, inspectable execution, and explicit authority. Extension areas are evaluated against those constraints.

## Reusable language units

Top-level user-defined pure functions provide reusable expression logic with explicit parameters, acyclic call graphs, static result inference where possible, and compile-time expansion into ordinary execution plans.

Deterministic file imports allow pure functions to be shared across project files with project-bounded path resolution, transitive dependency loading, duplicate-load suppression, module graph inspection, and cycle rejection.

Further reusable-language work includes explicit namespaces, selective imports, module aliases, public and private declaration visibility, typed function signatures, and richer result type checking.

## Structured data

The value model supports deterministic lists and objects, nested structured values, first-class list and object literal syntax, member access, index access, membership checks, key and value projection, collection sizing, and boolean collection gates.

Further language work includes stronger static element typing, deterministic transformation functions, collection pattern validation, and explicitly bounded iteration.

## Action model

Explicit action statements bind structured results while naming both the external operation and the capability required to execute it. Runtime action registration binds every operation to one capability so missing handlers, missing grants, and capability mismatches fail closed.

The standard action registry can bind the bounded filesystem, process, and HTTP adapters without giving pure expressions ambient authority. CLI action profiles make those bindings available through an explicitly selected TOML file with filesystem roots, process executable allowlists, process environment keys, timeout bounds, and HTTP hostname allowlists.

Typed operation schemas and action result contracts provide static validation where operation structure is visible and runtime validation at the action boundary. Execution receipts connect runtime state to the deterministic plan fingerprint while omitting runtime values and local authority configuration.

Further action work includes richer dry run previews, retry policy with deterministic planning semantics, and cryptographic profile attestation.

External authority remains explicit regardless of syntax growth.

## Mission Control

The dependency-free Language Server Protocol surface provides editor diagnostics and canonical formatting through the same compiler used by the CLI. Product direction includes source-aware navigation, completion, hover information, unsaved multi-file overlays, deeper graph inspection, source span synchronization, execution history, capability configuration, templates, and module browsing.

## Compatibility

Published tags remain immutable. Language growth proceeds through documented contracts, tests, and release records.
