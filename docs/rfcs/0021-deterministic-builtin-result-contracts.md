<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# RFC 0021: Deterministic Built-in Result Contracts

## Status

Accepted and implemented.

## Problem

Typed function, list, and object contracts can preserve structure across declarations and user-defined calls, but several deterministic polymorphic built-ins still collapse their result to unknown even when source code proves a stable result contract. That weakens return checking and downstream argument validation.

## Contract

VECTIS derives the strongest result contract guaranteed by every statically visible alternative. The operation is conservative: when alternatives disagree at the top-level value kind or static information is unavailable, the result remains unknown.

For compatible lists, item contracts are joined recursively. For compatible object shapes, only fields present in every alternative remain guaranteed. A shared field with incompatible value contracts remains present with an `any` field contract.

## Built-in inference

1. `if_else(condition, left, right)` uses the selected branch when the condition is a boolean literal. Otherwise it joins the two result contracts.
2. `coalesce(...)` joins all visible argument contracts.
3. `object(...)` exposes a structural object shape when keys are unique string literals. Values with unavailable contracts become `any` fields.
4. `get(list, index)` preserves a known list item contract. A supplied default is joined with that item contract because either value may be returned.
5. Existing literal-key object `get` inference remains unchanged because a field named by an object shape is required.
6. `values(object)` uses the same common-contract operation across visible field values.
7. List literals and `list(...)` preserve a common structured item contract when one can be proven.

## Determinism

Result inference depends only on the typed AST, canonical type contracts, and deterministic pure-function graph. It performs no evaluation with external state and does not inspect runtime authority configuration.

## Authority and execution

This RFC changes compile-time result metadata only. Built-in runtime handlers, execution graph structure, scheduling, capabilities, action registration, profiles, adapters, and receipts are unchanged.

## Compatibility

Existing programs remain valid. Unknown or incompatible alternatives stay permissive instead of causing speculative type errors. The package version remains `0.8.0` for this implementation line.

## Validation

Validation covers scalar results, literal-condition selection, shared object fields, nested list and object joins, incompatible alternatives, `coalesce`, literal-key object constructors, typed-list lookup with and without defaults, downstream argument validation, repository policy, public history, privacy boundaries, and the complete unit suite.
