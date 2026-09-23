<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# RFC 0013: LSP Source Span Synchronization

## Summary

VECTIS editor integrations use one shared conversion contract between canonical one-based source positions and zero-based UTF-16 Language Server Protocol coordinates.

## Problem

The compiler intentionally stores source positions as one-based Python string columns. LSP clients use zero-based UTF-16 code units. Semantic tokens already accounted for that difference, while diagnostics, navigation, symbols, hover, and signature help used independent coordinate calculations. ASCII source hid most differences, but non-BMP text could shift editor locations after characters such as emoji.

## Coordinate contract

`vectis.lsp_position` owns editor coordinate conversion. Canonical `SourcePosition` and `SourceSpan` remain unchanged.

A source position converts its zero-based line and the UTF-16 width of the source prefix before its one-based column. A closed VECTIS source span becomes an end-exclusive LSP range. LSP cursor characters convert back to Python string indexes before word, signature, or symbol lookup.

## Synchronized surfaces

The shared contract is used by diagnostics, definition, references, rename edits, document symbols, semantic token encoding, hover cursor lookup, and signature-help cursor lookup.

Overlay-aware navigation converts spans against the same source buffer that produced the AST occurrence. Diagnostics prefer an open buffer for their source file, then saved source, then the current request source when no file mapping exists.

## Determinism

Coordinate conversion is pure and depends only on source text and canonical source positions. UTF-16 width is calculated with the Python standard library. No editor-specific state changes the conversion result.

## Authority and security

Source span synchronization performs no execution, capability registration, file mutation, or external operation. Reading saved source for diagnostic conversion follows the existing LSP workspace behavior and does not expand the module root or authority model.

## Compatibility

The VECTIS grammar, AST, compiler IR, runtime scheduling, action authority, CLI execution, package version, and published releases do not change. ASCII-only coordinates remain equivalent. Unicode-aware clients receive corrected UTF-16 positions.

## Test strategy

Tests cover non-BMP UTF-16 widths, forward and reverse position conversion, end-exclusive ranges, hover and signature cursor lookup, document-symbol ranges, mission-value navigation, rename edits, diagnostics, and existing semantic-token behavior. The complete repository suite remains required before merge.
