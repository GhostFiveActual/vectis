<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# RFC 0019: Typed List Element Contracts

## Status

Accepted and implemented.

## Problem

RFC 0018 lets pure functions describe a value as `list`, but that contract cannot distinguish a list of numbers from a list of strings. The runtime value model already supports deterministic nested lists, and static analysis can preserve element information in several common cases without changing runtime representation.

## Source contract

A function type annotation may use `list[TYPE]`, where `TYPE` is another supported contextual type contract. Nested list contracts are recursive.

```vectis
function first_score(scores: list[number]): number {
    return scores[0];
}

function matrix(values: list[list[number]]): list[number] {
    return values[0];
}
```

Plain `list` remains valid and means that no item contract is required. `list[any]` explicitly accepts any statically visible item type.

## Semantic rules

1. The supported base names remain `string`, `number`, `boolean`, `list`, `object`, and `any`.
2. Only `list` may contain a bracketed item contract.
3. A typed list parameter validates a statically known argument list contract before graph generation.
4. List literals are checked item by item when the expected contract contains an item type.
5. Homogeneous list literals infer their item contract. Empty or statically mixed lists infer `list[any]`.
6. Known list contracts propagate through `source`, `let`, and valued `analyze` declarations.
7. Indexing a list with a known item contract produces that item contract for later static checks.
8. A declared typed list result participates in the same function-body result checking established by RFC 0018.
9. Unknown static information remains permissive. This RFC does not introduce implicit runtime coercion or a runtime generic container.

## Determinism

Type contract parsing is local and deterministic. Contract inference depends only on canonical source syntax and the existing deterministic function graph. No external registry or environment input participates in contract resolution.

## Authority and security

Typed list contracts are compile-time metadata. They do not grant capabilities, register actions, select profiles, access files, start processes, perform HTTP requests, or alter runtime authority checks.

## Execution graph

The execution graph representation and scheduling rules are unchanged. Pure-function calls continue to expand into ordinary VECTIS expressions before runtime execution.

## Diagnostics

Unsupported type labels fail semantic analysis. Known list item mismatches fail before graph generation and identify the argument or returned list position when the mismatching element is statically visible.

## Editor behavior

Signature help renders canonical list contracts. Semantic tokens classify each contextual type identifier, including nested item types, as a keyword. Module browsing continues to project the canonical annotation strings already stored in the AST.

## Compatibility

Untyped functions, scalar typed functions, plain `list`, and existing runtime values remain compatible. The package version remains `0.8.0` for this implementation line.

## Alternatives considered

A separate generic type AST was considered. The current AST already stores canonical annotation strings, so this RFC keeps that public shape and centralizes contract parsing in one compile-time helper. Object shape contracts remain separate because named fields require a different compatibility model from homogeneous list elements.

## Validation

Implementation validation covers parser and formatter round trips, nested list contracts, literal mismatch rejection, declaration propagation, index result inference, imported typed functions, signature help, semantic tokens, module browsing, repository policy, public history, privacy boundaries, and the complete unit suite.
