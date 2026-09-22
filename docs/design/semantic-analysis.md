<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# Semantic Analysis

Semantic analysis is the compiler stage between parsing and execution-graph generation. It validates relationships that are syntactically valid but not meaningful under the VECTIS language contract.

## Responsibilities

The semantic analyzer currently validates:

* duplicate declarations,
* unresolved references,
* built-in function names,
* built-in function arity,
* boolean `when` conditions,
* boolean `assert` expressions,
* numeric `confidence` expressions,
* selected expression type mismatches.

It does **not** execute a mission, acquire capabilities, or perform filesystem/process/network effects.

## Deterministic scope

Declarations enter scope in source order. A reference resolves only to a declaration that is visible at the point where the expression is analyzed. Mission and branch blocks are analyzed deterministically; semantic resolution does not use inference or external state.

## Value types

The current semantic type model covers scalar values used by the 0.1 language:

* string,
* number,
* boolean,
* unknown/deferred when a value cannot be proven statically.

Runtime evaluation may resolve a deferred value from dependency-node results, but a known semantic contradiction is rejected before compilation.

## Function validation

Function calls use the shared deterministic built-in registry from `vectis.evaluator`. Unknown names produce `SEM003`; invalid arity produces `SEM004`.

The analyzer validates function shape without executing external effects because all standard built-ins are pure.

## Diagnostics

Semantic failures use stable `SEMxxx` diagnostics with canonical source spans:

* `SEM001` unresolved reference,
* `SEM002` duplicate declaration,
* `SEM003` unknown function,
* `SEM004` invalid function arity,
* `SEM005` type mismatch.

The semantic result is deterministic for the same AST.
