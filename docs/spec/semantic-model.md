<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# VECTIS Semantic Model

Status: normative for the 0.6 language line.

## Purpose

Semantic analysis runs after parsing and before execution graph generation. A program with semantic diagnostics does not produce a graph.

## Declarations

Source, let, and analyze introduce names into the declaration environment.

Duplicate declarations produce SEM002.

References must resolve to an earlier visible declaration. An unresolved reference produces SEM001.

## Value types

The semantic model tracks six coarse types:

1. string
2. number
3. boolean
4. list
5. object
6. unknown

Lists are ordered deterministic values. Objects use string keys and preserve deterministic construction order. Unknown represents a value that cannot be proven statically or may be supplied by a runtime handler.

## Source modules

An import declaration participates in source composition before ordinary semantic analysis.

```vectis
import "../lib/readiness.vectis";
```

The module resolver canonicalizes each imported path, keeps resolution inside the project module root, loads each canonical file once, and rejects cycles. Imported modules may contain imports and top-level pure function declarations only.

After successful resolution, import declarations are removed and imported pure functions become part of the merged compilation program. Calls are then validated and expanded by the same pure-function semantics used in a single file.

A raw AST that still contains an unresolved import fails semantic analysis with SEM006 rather than being compiled with incomplete meaning.

## User-defined pure functions

A top-level function declaration introduces a reusable expression function with an explicit parameter list.

```vectis
function release_ready(score, risk) {
    return score >= 90 && risk <= 25;
}
```

Function parameters form the complete local reference environment for the body. A function cannot capture source, let, analyze, stage, mission, capability, or runtime handler state.

Function names cannot conflict with deterministic built-ins. Duplicate function names and duplicate parameter names are semantic errors. Calls must supply exactly the declared parameter count.

Functions may call other user-defined pure functions regardless of declaration order. The user-function call graph must be acyclic. Direct and indirect recursion are rejected before graph generation.

When the body has a statically inferable result type, function calls participate in ordinary VECTIS type checking. A function body that deterministically returns text therefore cannot be used as a boolean condition.

During compilation, user-function calls are expanded into ordinary VECTIS expressions. The execution graph and runtime do not gain a separate function execution mechanism or additional authority.

## Built in functions

Function calls resolve against the deterministic registry in the evaluator.

An unknown function produces SEM003.

An invalid argument count produces SEM004.

The registry includes text normalization, text tests, concatenation, replacement, bounded repetition, numeric helpers, numeric range checks, aggregate boolean gates, true-value counting, averaging, percentages, coalescing, conversion, conditional selection, deterministic list and object construction, structured lookup, membership checks, key and value projection, collection sizing, and boolean collection gates.

Use the command below for the exact installed registry:

```bash
vectis builtins
```

## Type rules

Known contradictions are rejected before graph generation.

Examples include a nonboolean when condition, a nonboolean assert condition, and a nonnumeric confidence expression.

These failures use SEM005.

## External actions

An action is an explicit effect boundary that binds one result value.

```vectis
action response "http.request" using "http" {
    method: "GET",
    url: endpoint
};
```

The action input must evaluate to an object. Semantic analysis validates input references before graph generation and introduces the action result name as an unknown value so downstream expressions can depend on it.

Compilation emits a dedicated action node containing the operation name, required capability, deterministic input expression, stage metadata, and ordinary dependency edges. The operation name itself grants no authority.

At runtime, action execution requires both an explicit capability grant and an explicitly registered operation. The registered operation is bound to exactly one capability. If source names a different capability, execution fails rather than broadening authority.

Action results must remain inside the VECTIS value model so they can flow into later deterministic expressions, assertions, conditions, publications, reports, and graph evidence.

## Graph eligibility

Compilation occurs only when semantic diagnostics are empty.

References become dependency edges.

Conditional bodies become explicit true or false branch edges.

Assertions become dependency guards for statements that follow them in the same block.

## Runtime values

The runtime resolves serialized expressions against values produced by dependency nodes. Scalar and structured values can therefore flow across source, value, condition, assertion, and publication nodes while preserving deterministic topological scheduling. Structured values do not grant authority and cannot mutate after construction through VECTIS syntax.

## Language boundary

VECTIS supports scalar values, deterministic list and object values, first-class structured syntax, user-defined pure expression functions, and deterministic file imports for sharing pure functions. Function-local statement bodies, recursive functions, runtime imports, package-registry resolution, and bounded iteration remain outside the current language contract.
