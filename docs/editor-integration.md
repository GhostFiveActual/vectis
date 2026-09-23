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
11. `textDocument/definition` for user-defined pure functions and executable values.
12. `textDocument/references` for reachable function calls and executable value references.
13. `textDocument/rename` for supported function and executable value symbols.
14. `textDocument/signatureHelp` for built-ins and user-defined pure functions.
15. `textDocument/semanticTokens/full` for deterministic language roles.
16. `workspace/executeCommand` with `vectis.graph.inspect` for read-only execution graph inspection.
17. `workspace/executeCommand` with `vectis.history.inspect` for project-bounded execution receipt history.
18. `workspace/executeCommand` with `vectis.capabilities.inspect` for project-bounded authority configuration preview.
19. `workspace/executeCommand` with `vectis.templates.inspect` for read-only built-in project template inspection.
20. `workspace/executeCommand` with `vectis.modules.inspect` for project-bounded module browsing.
21. `textDocument/publishDiagnostics` notifications.

Diagnostics use the stable VECTIS diagnostic code as the LSP code and report parser, lexer, module-resolution, and semantic failures through the same compiler contracts used by command-line validation.

## Imports and unsaved buffers

Open file-backed documents form an overlay above disk content. Module resolution uses the open editor buffer first and reads the saved file only when no overlay exists for that path.

The overlay resolver preserves the normal project root, relative import, `.vectis` extension, cycle rejection, and imported-module purity rules. Unsaved imported pure functions therefore participate in the same semantic compilation as saved modules.

Opening, changing, or saving a file republishes diagnostics for all open documents so an imported buffer change can immediately update an open importing mission.

## Source navigation

Definition, references, and rename operate on user-defined pure functions across the reachable deterministic import graph and on executable value bindings in the entry source. Executable values include `source`, `let`, `analyze`, and `action` result declarations, including declarations and references nested in stages and conditional branches.

When navigation starts from an imported module, the server prefers the widest currently open entry workspace containing that file. Imported modules remain pure-function-only, so executable value navigation stays in the entry source. Pure-function parameters are not treated as executable values.

Rename returns a normal LSP `WorkspaceEdit` and does not modify source files itself. Value rename changes only the unique declaration and its canonical `Reference` AST occurrences and rejects ambiguous declarations, declaration collisions, keywords, and contextual boolean literals. Built-in functions have no source definition.

## Signature help

`textDocument/signatureHelp` reports callable information for deterministic pure functions while a call is being written. Built-in labels and arity come from the canonical evaluator registry. User-defined labels preserve the parameter names declared in VECTIS source.

The signature helper uses the same overlay-aware workspace as navigation when the current source graph is complete. If the current call site is temporarily incomplete, declaration headers can still be recovered from open buffers through the canonical lexer. This keeps an unsaved imported function available at the normal `(` and `,` signature triggers without changing parser or compiler behavior.

Nested calls, strings, line comments, list literals, and object literals are tracked so commas inside nested values do not advance the outer active parameter.

## Semantic tokens

`textDocument/semanticTokens/full` reports deterministic language roles from the canonical VECTIS lexer. The server advertises a stable legend for keywords, strings, numbers, operators, functions, parameters, variables, and properties, with `declaration` as the initial modifier.

Function declarations and call targets are reported as functions. Function parameters preserve parameter identity within the pure-function body. Mission values introduced by `source`, `let`, `analyze`, and `action` are reported as variable declarations. Object identifier keys and member names are reported as properties. Contextual boolean literals are reported as keywords.

Semantic token positions use UTF-16 code units. Multi-line lexical tokens are split into line-local records before LSP delta encoding. If lexical analysis fails, semantic highlighting returns an empty token stream and does not alter compiler diagnostics or execution behavior.

## Execution graph inspection

`workspace/executeCommand` with `vectis.graph.inspect` compiles the current editor workspace and returns deterministic plan structure without executing the plan. Clients pass one argument object containing the document `uri`.

The response includes the canonical graph fingerprint and summary, stage and capability manifests, and nodes in deterministic topological order. Each node reports its identifier, kind, label, stage, metadata, dependencies, successors, and typed incoming and outgoing edges.

Open buffers replace saved source before module resolution. When the selected file participates in an open importing workspace, inspection uses the same widest reachable overlay workspace as source navigation.

Graph node values and runtime state are omitted from the inspection payload. Invalid source returns translated VECTIS diagnostics rather than a partial graph.

## Execution history

`workspace/executeCommand` with `vectis.history.inspect` projects explicitly persisted execution receipts into a deterministic history response. Clients pass one argument object containing a file-backed document `uri`, a relative receipt `directory`, and an optional integer `limit`.

The receipt directory is resolved inside the selected document's VECTIS project root. Absolute directories and paths that escape the project root are rejected. Receipt discovery is non-recursive, and receipt symlinks are rejected.

History returns an allowlisted projection rather than raw receipt JSON. Entries include receipt filename, recorded time, safe source label, plan fingerprint and numeric summary, execution status, dry-run state, node-state counts, failure categories, granted capability names, and a profile fingerprint when present. Runtime values, failure details, local paths, and arbitrary receipt fields are not returned.

The history command performs no execution and creates no receipts. Receipts appear only when an operator explicitly persists them through existing receipt options.

## Capability configuration

`workspace/executeCommand` with `vectis.capabilities.inspect` compares the current compiled mission with explicit capability grants and an optional action profile. Clients pass one argument object containing a file-backed document `uri`, an optional relative `profile`, and an optional `capabilities` array.

Mission compilation uses the current open-buffer workspace. Relative profiles are resolved inside the selected document's VECTIS project root, while absolute paths and paths that resolve outside the project root are rejected.

The response reports the plan fingerprint, required and requested capabilities, planned action operation and capability pairs, configured capability names, registered profile operations, missing authority, unused grants, unresolved authority nodes, and the existing profile-shape attestation when a profile is supplied.

The command is read-only. It does not create runtime capability grants, select a profile for later execution, invoke actions, or expose filesystem roots, executable paths, or environment values. Runtime authority still requires explicit execution options.

## Project templates

`workspace/executeCommand` with `vectis.templates.inspect` returns the deterministic built-in project template catalog or one template preview. Clients pass one argument object and may include a string `name`.

An omitted name returns catalog metadata. A named preview includes the ordered relative file paths, UTF-8 content, and SHA-256 digest for each file.

The editor command is read-only. It does not write project files, download templates, discover remote registries, execute missions, or activate action profiles.

## Module browsing

`workspace/executeCommand` with `vectis.modules.inspect` returns a deterministic project module catalog. Clients pass one argument object containing a file-backed document `uri`.

The selected document identifies the nearest VECTIS project root. The response uses project-relative paths and reports each `.vectis` file, declared imports, resolved dependency edges, pure-function signatures, executable statement counts, safe diagnostics, importability, cycles, and rejected symbolic-link paths.

Open file-backed VECTIS documents inside the project replace saved source. Unsaved file-backed `.vectis` documents inside the root are included in the catalog even when they do not exist on disk.

The command is read-only. It does not execute missions, compile an execution graph, grant capabilities, select action profiles, follow source symlinks, write files, or access a remote module registry.

## Source coordinates

All editor-facing positions use one shared UTF-16 LSP conversion contract. Diagnostics, definition, references, rename edits, document symbols, semantic tokens, hover cursor lookup, and signature-help cursor lookup therefore agree even when source contains non-BMP Unicode text.

Canonical compiler `SourcePosition` and `SourceSpan` objects remain one-based source coordinates. The editor layer converts them at the protocol boundary and converts incoming UTF-16 cursor characters back to Python source indexes before lookup.

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
