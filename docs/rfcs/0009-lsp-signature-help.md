<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# RFC 0009: LSP Signature Help

## Summary

This RFC adds Language Server Protocol signature help for deterministic pure-function calls. The feature reports built-in arity from the canonical evaluator registry and user-defined function parameters from the overlay-aware module workspace introduced by RFC 0008.

The language grammar, typed AST, semantic rules, execution graph, runtime, capability model, module syntax, and package version remain unchanged.

## Problem

Completion and hover can identify callable names, but they do not keep parameter information visible while a call is being written. Cross-file user functions also need editor assistance that reflects unsaved imported buffers rather than stale disk content.

Signature help must remain useful while a call expression is temporarily incomplete. A normal parser round trip cannot be required at the exact `(` or `,` trigger because the editor buffer may not form a complete program at that moment.

## Protocol contract

The server advertises `signatureHelpProvider` with `(` and `,` as trigger characters. The server handles `textDocument/signatureHelp` and returns either one deterministic signature or `null` when no supported call is active.

Built-in signatures use the canonical built-in manifest for name, description, minimum arity, and maximum arity. The editor layer does not maintain a second built-in registry.

User-defined signatures use exact `FunctionDeclaration.parameters` from the resolved workspace when the current overlay graph parses successfully. When the current call site is temporarily incomplete, the server may recover declaration headers from open buffers through the canonical lexer so unsaved user-function signatures remain available without changing compiler behavior.

## Active parameter selection

The editor helper scans source text only far enough to identify the innermost unmatched call parenthesis and the number of top-level commas within that call. String contents, line comments, nested calls, list literals, and object literals do not advance the outer active parameter.

For fixed-arity functions, the active parameter is clamped to the final declared parameter. For variadic built-ins, additional arguments map to one stable variadic parameter slot.

## Determinism

Signature help has no execution authority and performs no external work. For identical source text, cursor position, open-buffer set, and installed VECTIS version, the returned signature information is deterministic.

## Authority and security

The feature does not grant capabilities, execute actions, read process environment values, contact network services, or expose action-profile secrets. Disk reads remain bounded to the existing file-backed workspace behavior already used by the language server.

## Compatibility

This is an additive LSP capability. Existing clients that do not request signature help continue using the prior protocol surface unchanged. No language syntax or runtime contract changes are introduced.

## Test strategy

1. Verify fixed-arity built-in labels and active-parameter selection.
2. Verify nested calls select the innermost active signature.
3. Verify variadic built-ins use a stable variadic parameter slot.
4. Verify commas inside strings and nested structured values do not affect the outer call.
5. Verify user-function parameter names come from overlay-aware workspace declarations.
6. Verify an incomplete call can still resolve a user-function signature from an unsaved imported buffer.
7. Verify the LSP initialization capability advertises signature help.
8. Run the complete unit, repository-policy, and public-history gates before publication.
