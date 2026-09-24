<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# RFC 0022: Module Function Visibility

## Status

Accepted and implemented.

## Problem

Deterministic modules currently flatten every reachable pure function into one compilation program. That makes every imported function callable from every reachable module, so library authors cannot distinguish a supported module surface from internal helpers.

## Syntax

Bare function declarations remain public. A module-local helper uses a contextual modifier:

```vectis
private function threshold(value: number): boolean {
    return value >= 90;
}

function ready(value: number): boolean {
    return threshold(value);
}
```

`private` is contextual only when it directly precedes `function`. It does not enter the global lexer keyword set, so existing identifier usage remains compatible.

## Visibility contract

1. A bare `function` is public.
2. A `private function` may be called from declarations and executable statements in the same source module.
3. A call from another module to a private function fails during module resolution before graph generation.
4. Public functions retain the existing reachable import behavior, including transitive imports.
5. Imported modules remain limited to imports and pure function declarations.
6. Loaded-program function names remain globally unique in this RFC. Module aliases and namespace identity remain separate work.

## Editor and inspection surfaces

Overlay-aware workspace resolution enforces the same visibility rule as disk-backed compilation. Module browsing adds a `visibility` field to each function record while keeping the `vectis.module-browser/v1` schema because the field is additive. Semantic tokens classify the contextual `private` modifier as a keyword. Definition, references, rename, and signature help continue to use the existing globally unique function identity.

## Authority and execution

Visibility is a compile-time module boundary. Runtime handlers, execution graph scheduling, capabilities, action profiles, adapters, receipts, and external authority are unchanged.

## Compatibility

Existing bare function declarations remain public and preserve their current behavior. The package version remains `0.8.0` for this implementation line.

## Validation

Validation covers parser and formatter round trips, contextual identifier compatibility, same-module private helper calls, rejected cross-module calls, transitive module access, overlay workspaces, module browsing, semantic tokens, repository policy, public history, privacy boundaries, and the complete unit suite.
