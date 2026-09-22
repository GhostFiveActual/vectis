<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# Editor Integration

VECTIS includes a Language Server Protocol endpoint that uses only the Python standard library and the installed VECTIS compiler.

## Start the server

```bash
vectis lsp
```

The server communicates over standard input and output using normal Content-Length framed JSON-RPC messages. Editors should start one server process and treat its standard streams as the LSP transport.

## Supported protocol surface

The current server supports:

1. `initialize` and `initialized`.
2. `shutdown` and `exit`.
3. `textDocument/didOpen`.
4. `textDocument/didChange` with full-document synchronization.
5. `textDocument/didSave`.
6. `textDocument/didClose`.
7. `textDocument/formatting`.
8. `textDocument/completion` with keywords, pure built-ins, and standard actions.
9. `textDocument/hover` for language keywords, built-ins, and standard actions.
10. `textDocument/documentSymbol` for functions, missions, stages, values, and actions.
11. `textDocument/publishDiagnostics` notifications.

Diagnostics use the stable VECTIS diagnostic code as the LSP code and report parser, lexer, module-resolution, and semantic failures through the same compiler contracts used by command-line validation.

## Imports and unsaved buffers

When an open document exactly matches its saved file, VECTIS validates it through the deterministic project module loader so imported pure functions and project boundaries are resolved normally.

When an imported document has unsaved edits, the language server validates its syntax directly from the editor buffer but does not substitute stale module files from disk for the edited source. Full project-aware unsaved overlay resolution is a future extension.

## Language intelligence

Completion candidates are generated from the same keyword, built-in function, and standard action registries used by VECTIS itself. Hover information reports language semantics and authority requirements from those registries. Document symbols are derived from the typed AST rather than textual pattern matching.

This shared-source approach is intentional: editor integrations should reflect the installed VECTIS version rather than maintain a parallel language definition.

## Formatting


`textDocument/formatting` delegates to the canonical VECTIS formatter. The server returns one whole-document edit only when the canonical source differs from the current buffer.

## Example client command

Clients that accept an executable array can use:

```text
["vectis", "lsp"]
```

No network port, background daemon, project service, or editor-specific VECTIS process is required.
