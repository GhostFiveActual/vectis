<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# RFC 0001: User-defined pure functions

Status: Accepted

Target language line: 0.3

## Problem

Large missions repeatedly express the same deterministic calculations, gates, normalization rules, and structured-value construction. Copying those expressions increases source size and creates more places where logically identical rules can drift.

VECTIS needs reusable computation without introducing hidden state, recursion, implicit authority, or a second runtime model.

## Contract

A function is declared at program top level.

```vectis
function release_ready(score, risk) {
    return score >= 90 && risk <= 25;
}
```

A declaration has a unique function name, an ordered parameter list, and exactly one returned expression.

Calls use ordinary expression syntax.

```vectis
let approved release_ready(quality, risk);
```

Functions may return scalar or structured values.

## Scope

Function parameters are the complete local reference environment for the body. A body cannot capture mission declarations, stage values, analysis nodes, capabilities, runtime handlers, process environment, filesystem state, network state, or other ambient data.

A body may call deterministic built-ins and other user-defined pure functions.

Function declarations may appear in any top-level order.

## Recursion

Direct and indirect recursive call cycles are rejected during semantic analysis.

The language does not provide recursive functions in the 0.3 contract. This keeps function expansion finite and inspectable and avoids introducing an independent stack or runtime recursion model.

## Determinism

Function calls are expanded during compilation. Parameters are replaced with the call arguments, and nested pure-function calls are expanded until the executable expression contains only literals, references to mission values, operators, and deterministic built-ins.

The resulting execution graph therefore uses the same scheduling, fingerprinting, limit checks, dry-run behavior, runtime evaluation, and reporting path as a mission that wrote the expanded expression directly.

## Inspection

When a function call expands, graph metadata retains both forms when they differ:

1. `source_expression` records the expression written by the user.
2. `expression` records the expanded expression executed by the runtime.

This keeps abstraction visible without hiding executable meaning.

## Authority

Function declarations do not create execution nodes and cannot acquire capabilities.

The syntax has no function-local statements for `require`, `request`, process execution, filesystem operations, HTTP operations, publications, analysis handlers, or other effects.

External authority remains controlled by existing mission statements, graph nodes, capability checks, and adapters.

## Type behavior

Function calls participate in semantic type checking when the body result can be inferred.

A function that returns a comparison has boolean type. A function that returns deterministic text has string type. Parameter-dependent results that cannot be proven statically remain `unknown` and are validated by ordinary runtime contracts.

## Errors

Semantic analysis rejects:

1. Duplicate function names.
2. Function names that collide with built-ins.
3. Duplicate parameters.
4. Calls with the wrong argument count.
5. References to names outside the parameter environment.
6. Direct recursion.
7. Indirect recursion.
8. Function declarations inside mission, stage, or conditional blocks.

## Alternatives

A separate function runtime was rejected because it would create another execution model and weaken the relationship between source, graph, fingerprint, and runtime state.

Host-language callbacks were rejected because they would place function meaning outside the VECTIS source and authority model.

Textual macros were rejected because they would weaken typed syntax and source-level diagnostics.

## Compatibility

The feature belongs to the 0.3 minor line because it extends the grammar and semantic model.

Existing 0.2 mission syntax remains valid. No 0.2 statement changes meaning.

## Verification

The implementation requires parser, formatter, semantic, compiler, dependency, structured-value, runtime, recursion, arity, capture, and installed-package regression coverage.
