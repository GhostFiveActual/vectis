<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# RFC 0005: Typed Action Contracts

## Status

Accepted for implementation.

## Problem

Explicit actions already bind an operation to a capability, but the operation contract is described only by handler behavior and prose. A mission can therefore reach runtime before discovering a misspelled field, a statically visible type mismatch, or a handler result that does not match the operation shape expected by downstream logic.

VECTIS should make an action operation inspectable before execution while preserving host extensibility and explicit authority.

## Contract

Each typed action contract identifies an operation, required capability, input schema, result schema, and description.

The schema model covers strings, numbers, booleans, lists, objects, and unconstrained VECTIS values. List item schemas and object member schemas may be recursive.

Standard actions carry contracts. Custom host actions may register without a contract for compatibility, or provide a contract when the embedding application wants equivalent validation.

## Semantic behavior

For a standard action whose argument expression is an object literal, semantic analysis validates required fields, unsupported fields, statically inferable field types, list item types, and the authored capability name.

Dynamic expressions remain valid when their exact runtime shape cannot be proven statically. Runtime validation remains authoritative for those values.

The semantic analyzer also assigns the declared result category of a standard action to the bound action result. This allows downstream type checks to use contract information without executing the action.

## Runtime behavior

`ActionRegistry.execute()` validates contract-bound input before invoking the handler and validates the handler result before returning it to the execution graph.

Validation fails closed. A handler is not invoked when its input violates the contract, and a nonconforming result cannot enter downstream VECTIS state.

Custom operations registered without contracts preserve the 0.8 behavior.

## Authority

Contracts do not grant authority. Capability availability, adapter policy, explicit profile selection, and operation registration remain separate requirements.

A contract describes the shape of an operation. It cannot create a capability, register a handler, widen a filesystem root, permit an executable, or expand an HTTP host allowlist.

## Inspection

`vectis actions` exposes the same standard contract metadata used by semantic analysis and runtime validation.

Editor hover uses that manifest to show required capability, input fields, optional fields, and the top-level result category.

## Determinism

Contract manifests are immutable and ordered. Validation depends only on the contract and the VECTIS value being checked.

No schema validation performs I/O.

## Compatibility

The language grammar does not change.

Standard actions become stricter where a contract can prove that authored or runtime data violates the documented operation shape. Valid 0.8 standard action programs remain valid.

Custom host registrations remain compatible when no contract is supplied.

## Test strategy

1. Validate required, unsupported, scalar, list item, and result constraints.
2. Prove standard action result type inference.
3. Prove capability mismatch diagnostics for standard operations.
4. Prove custom operations remain usable without contracts.
5. Verify CLI and editor inspection use the canonical contract manifest.
6. Run the complete repository quality gate across the supported Python matrix.
