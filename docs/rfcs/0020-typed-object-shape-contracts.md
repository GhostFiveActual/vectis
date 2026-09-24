<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# RFC 0020: Typed Object Shape Contracts

## Status

Accepted and implemented.

## Problem

RFC 0019 preserves homogeneous list element contracts, but `object` remains broad even when source code exposes stable field names. Pure functions therefore cannot state that an input must contain a known set of fields or preserve a field contract through member access.

## Source contract

A function type annotation may use `object{FIELD:TYPE,...}`. Each field name is an identifier and each field type is another supported contextual type contract. Object and list contracts may nest recursively.

```vectis
function release_score(
    value: object{name:string,metrics:object{scores:list[number]}}
): number {
    return value.metrics.scores[0];
}
```

A shape contains at least one field. Plain `object` remains the broad object contract.

## Semantic rules

1. Every field named by an object shape is required when the argument or returned object is statically visible.
2. Extra object fields are allowed. Object shape compatibility is structural rather than nominal.
3. Known field contracts propagate through object literals, declarations, pure-function parameters and results, member access, string-key index access, and deterministic `get` calls with a literal key.
4. Nested list and object contracts validate recursively.
5. Access to a field absent from a statically known shape fails semantic analysis.
6. Broad `object`, `any`, or unavailable static information remains permissive.
7. Object shape contracts do not introduce implicit coercion or a runtime record type.

## Determinism

Shape parsing and field compatibility depend only on canonical source syntax and the existing deterministic function graph. Field order in a contract is preserved for formatting and inspection, while structural compatibility is based on field names and contracts.

## Authority and security

Object shape contracts are compile-time metadata. They do not grant capabilities, register actions, select profiles, access files, start processes, perform HTTP requests, or alter runtime authority checks.

## Execution graph

The execution graph representation and scheduling rules are unchanged. Pure-function calls continue to expand into ordinary VECTIS expressions before runtime execution.

## Diagnostics

Known missing fields, incompatible field contracts, and impossible accesses fail before graph generation. Diagnostics identify the argument or result path when the incompatible field is statically visible.

## Editor behavior

Signature help renders canonical object shape contracts. Semantic tokens classify contextual type identifiers as keywords while object shape field identifiers remain properties. Module browsing continues to project the canonical annotation strings already stored in the AST.

## Compatibility

Untyped functions, scalar contracts, list contracts, plain `object`, existing object values, and runtime behavior remain compatible. The package version remains `0.8.0` for this implementation line.

## Alternatives considered

Named record declarations were considered, but they would require declaration visibility and module identity decisions that are outside this contract. Exact-object matching was also considered, but allowing additional fields preserves structural composition and keeps smaller contracts reusable with richer values.

## Validation

Implementation validation covers parser and formatter round trips, required fields, extra fields, nested shapes, field mismatch rejection, member and index propagation, imported functions, signature help, semantic tokens, module browsing, repository policy, public history, privacy boundaries, and the complete unit suite.
