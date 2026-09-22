<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# VECTIS Diagnostic System

Diagnostics are deterministic compiler/runtime data, not free-form log strings.

## Contract

Every `Diagnostic` contains:

* a stable `DiagnosticCode`,
* severity (`error` or `warning`),
* a non-empty message,
* canonical `SourceSpan` data.

`Diagnostic.to_dict()` produces JSON-safe data for the CLI, Studio, and editor integrations.

## Stable codes

| Code | Meaning |
| --- | --- |
| `LEX001` | Unterminated string literal |
| `LEX002` | Unsupported bare operator |
| `LEX003` | Unrecognized character |
| `SYN001` | Expected statement / unknown statement start |
| `SYN002` | Standalone `otherwise` |
| `SYN003` | Expected required token or delimiter |
| `SYN004` | Expected expression |
| `SYN005` | Unclosed block |
| `SYN006` | Malformed citation collection |
| `SYN007` | Reserved keyword cannot begin a statement |
| `SEM001` | Undeclared reference |
| `SEM002` | Duplicate declaration |
| `SEM003` | Unknown built-in function |
| `SEM004` | Invalid function arity |
| `SEM005` | Type mismatch |
| `CAP001` | Required capability unavailable |
| `CAP002` | Invalid capability value |

Existing meanings must not be silently repurposed.

## Source spans

Lexer/parser/semantic diagnostics retain the most specific available source span. End-of-input failures use a deterministic point span. Capability-registry compatibility errors that are not tied to user source use `<capability>:1:1`.

## Exceptions

`DiagnosticError` is a `ValueError` compatibility base and exposes `.diagnostic`, `.code`, `.severity`, `.message`, `.span`, `.file`, `.line`, and `.column`.

Lexer and parser errors remain specialized subclasses while sharing the same structured payload.
