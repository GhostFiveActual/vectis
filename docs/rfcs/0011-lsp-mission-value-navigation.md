<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# RFC 0011: LSP Mission Value Navigation

## Summary

This RFC extends the existing Language Server Protocol definition, references, and rename operations to executable VECTIS value bindings. The supported declarations are `source`, `let`, `analyze`, and `action` result bindings in the entry source, including declarations and references nested inside stages and conditional branches.

Pure-function navigation from RFC 0008 remains unchanged. Imported modules remain pure-function-only, so executable value navigation never crosses module files.

## Problem

VECTIS editors can navigate user-defined pure functions, but mission and executable values are still text without symbol identity. A user can inspect a mission value through document symbols or semantic highlighting, but cannot jump from a reference to its declaration, enumerate its uses, or safely prepare a rename.

Editor navigation must follow the language that the compiler actually accepts. It must not introduce a separate lexical scope model, treat function parameters as mission values, or rename unrelated identifiers that happen to use the same text.

## Symbol contract

The language server resolves two navigation symbol families:

1. User-defined pure functions across the reachable deterministic import graph.
2. Executable value bindings in the entry source.

Executable value declarations are `SourceDeclaration`, `LetDeclaration`, `AnalyzeDeclaration`, and `ActionStatement`. References are canonical `Reference` AST nodes outside pure-function declarations.

Pure-function parameters and their references are excluded from executable value navigation. They remain function-local language elements rather than mission values.

## Definition and references

`textDocument/definition` returns the declaration location for a supported function or executable value under the cursor.

`textDocument/references` returns deterministic occurrences for that exact symbol family. When `includeDeclaration` is true, the declaration is included.

Executable value navigation requires exactly one matching declaration. If invalid source contains ambiguous duplicate declarations, definition and references fail closed instead of selecting one arbitrarily.

## Rename

`textDocument/rename` continues to return a standard `WorkspaceEdit` without modifying source files.

Executable value rename changes the unique declaration and its `Reference` AST occurrences only. Function names, function parameters, object properties, member names, strings, and unrelated identifiers are not changed.

A value rename is rejected when the target is not a valid VECTIS identifier, is a language keyword, is a contextual boolean literal, or conflicts with another executable value declaration.

## Determinism

For identical source text, cursor position, open-buffer overlays, and installed VECTIS version, definition, references, and rename return deterministic results. Occurrences are sorted by canonical path and source position.

## Authority and security

Navigation performs no action execution, capability grant, process launch, network access, environment lookup, or source mutation. It analyzes the same overlay-aware AST and source spans already used by the language server.

## Compatibility

This is an additive editor capability. The grammar, typed AST, semantic rules, compiler, execution graph, runtime, capability model, module behavior, and package version remain unchanged.

## Test strategy

1. Verify mission value definition, references, and rename.
2. Verify all four executable value declaration forms are recognized.
3. Verify nested stage and conditional references retain the same value identity.
4. Verify pure-function parameters are excluded from executable value occurrences.
5. Verify ambiguous declarations fail closed.
6. Verify conflicting and reserved rename targets are rejected.
7. Verify existing cross-file pure-function navigation remains unchanged.
8. Verify language-server requests use unsaved entry-source content.
9. Run the complete unit, repository-policy, public-history, and live LSP smoke gates before publication.
