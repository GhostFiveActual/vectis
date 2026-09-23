<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# RFC 0010: LSP Semantic Tokens

## Summary

This RFC adds deterministic full-document Language Server Protocol semantic tokens for VECTIS source. The token stream is derived from the canonical lexer and contextual language structure so editors can distinguish syntax roles without maintaining a separate VECTIS grammar.

The language grammar, typed AST, semantic rules, execution graph, runtime, capability model, module behavior, and package version remain unchanged.

## Problem

Diagnostics, completion, hover, navigation, and signature help provide point-in-time language intelligence, but editors still need stable token roles for syntax-aware presentation. A VECTIS integration should not duplicate keyword lists or infer language structure from an editor-specific grammar when the installed compiler already owns that information.

Semantic tokens also need deterministic source coordinates. Multi-line strings must not produce cross-line token records, and LSP token lengths must use UTF-16 code units.

## Protocol contract

The server advertises `semanticTokensProvider` with full-document support. Range and delta requests are outside this RFC.

The semantic token legend contains these token types in stable order:

1. `keyword`.
2. `string`.
3. `number`.
4. `operator`.
5. `function`.
6. `parameter`.
7. `variable`.
8. `property`.

The only token modifier introduced by this RFC is `declaration`.

The server handles `textDocument/semanticTokens/full` and returns the standard delta-encoded integer stream in the `data` field.

## Classification

Canonical lexer tokens provide keyword, string, number, operator, identifier, punctuation, and exact source-span information. Semantic classification adds bounded context over that token stream.

Function declaration names and call targets are `function`. Function parameters are `parameter`, with declaration parameters carrying the `declaration` modifier. Mission value declarations introduced by `source`, `let`, `analyze`, and `action` are `variable` declarations. Member names and object identifier keys are `property`. Other identifiers are `variable`. Contextual boolean literals `true` and `false` are reported as `keyword`.

Punctuation is not emitted as a semantic token.

## Source coordinates

Each semantic token is emitted in deterministic source order using standard LSP relative encoding. Token start positions and lengths use UTF-16 code units.

A lexical token spanning multiple source lines is split into line-local semantic token records. No emitted semantic token crosses a line boundary.

## Failure behavior

Semantic highlighting is advisory editor information and must not change compiler behavior. If lexical analysis fails, the request returns an empty semantic token stream rather than inventing classifications from invalid source.

## Determinism

For identical source text and installed VECTIS version, the semantic token result is byte-for-byte deterministic. Token order comes from the canonical lexer, classification rules are fixed, and encoding contains no timestamps or environment-dependent values.

## Authority and security

Semantic token generation performs no action execution, capability grant, network access, process launch, or environment lookup. The feature only analyzes the document source already available to the language server.

## Compatibility

This is an additive LSP capability. Existing clients that do not request semantic tokens continue using the prior protocol surface unchanged. The VECTIS package remains version 0.8.0 until a release is intentionally prepared.

## Test strategy

1. Verify the semantic token legend and declaration modifier are stable.
2. Verify function, parameter, variable, property, keyword, string, number, and operator roles.
3. Verify multi-line strings are split into line-local tokens.
4. Verify UTF-16 token lengths.
5. Verify lexical failure returns an empty token stream.
6. Verify the language server reads unsaved open-buffer content for full-document semantic tokens.
7. Verify initialization advertises full semantic-token support.
8. Run the complete unit, repository-policy, public-history, and live LSP smoke gates before publication.
