<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# RFC 0018: Typed Pure-Function Signatures

## Summary

VECTIS pure functions may declare optional contextual type annotations for parameters and returned values while preserving the existing untyped function form.

## Problem

Pure functions already expose explicit parameter lists and deterministic bodies, but every parameter enters semantic analysis with an unknown value type. This limits call-site validation and forces callers to rely on body inference alone when reasoning about a function result.

The language needs a compact contract that strengthens static checking without introducing runtime coercion, nominal classes, hidden state, or a second execution model.

## Syntax

Parameter annotations use the existing colon punctuation. A result annotation follows the closing parameter list.

```vectis
function release_ready(
    score: number,
    risk: number
): boolean {
    return score >= 90 && risk <= 25;
}
```

Annotations are optional and may be introduced incrementally.

```vectis
function threshold(value, minimum: number): boolean {
    return value >= minimum;
}
```

The contextual annotation names are `string`, `number`, `boolean`, `list`, `object`, and `any`. They remain ordinary identifiers outside annotation positions so existing built-in calls such as `string(value)`, `number(value)`, `list()`, `object()`, and `any(values)` retain their established meaning.

## AST contract

`FunctionDeclaration` preserves the existing `parameters` tuple and adds `parameter_types` plus `return_type`.

`parameter_types` is either empty for compatibility with manually constructed untyped AST nodes or has exactly one entry per parameter. Each entry is a type name or `None`. `return_type` is a type name or `None`.

The function body and runtime expansion contracts do not change.

## Semantic rules

Known annotations map onto the existing semantic value categories. `any` maps to the existing unknown category.

A known argument type must match an annotated parameter type. Unknown argument types remain valid because VECTIS does not claim proof when static information is unavailable.

When a function declares a result type and the function body has a statically known type, those types must agree. A result annotation also becomes the function's public result type for callers.

Unknown annotation names fail semantic validation with `SEM005`.

No implicit conversion occurs. A string is not converted to a number merely because a parameter declares `number`.

## Modules

Typed functions use the existing deterministic import rules. The module loader keeps the existing path and namespace behavior.

The project module browser adds parameter-type and result-type fields to each function record while preserving the existing function name and parameter-name fields.

## Editor integration

Signature help displays declared annotations when present. Untyped functions retain their existing labels.

Semantic-token analysis treats contextual type names in function signatures as language keywords while preserving parameter declarations and parameter references as parameter tokens. The existing semantic-token legend remains unchanged.

## Determinism

Type checking depends only on the parsed program, deterministic module composition, and existing static inference rules. The same source produces the same diagnostics, formatted output, compiled graph, and signature-help labels.

Annotations do not alter graph node ordering, graph serialization, runtime scheduling, capability requirements, action registration, or receipt generation.

## Authority and security

Typed signatures are authority-free compile-time metadata. They cannot grant capabilities, register actions, read configuration, access files, start processes, perform network requests, or select an action profile.

## Compatibility

Existing untyped function declarations remain valid and format identically. Existing function calls do not require annotations.

The package version remains `0.8.0` for this feature RFC. Published tags and release assets remain unchanged.

## Test strategy

Tests cover parser and formatter round trips, partial annotations, call-site mismatch diagnostics, declared result mismatch diagnostics, `any`, invalid annotation names, imported typed functions, typed signature help, semantic-token parameter identity, module-browser projection, the complete repository suite, repository policy, privacy checks, and version preservation.
