<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# RFC 0008: LSP Function Navigation and Unsaved Module Overlays

## Status

Accepted for implementation.

## Problem

The VECTIS language server already provides diagnostics, formatting, completion, hover information, and document symbols. Imported modules are fully resolved only when the open buffer matches the saved file.

When an imported buffer has unsaved edits, the server currently avoids using stale disk content by suppressing project semantic diagnostics. This prevents false diagnostics, but it also means the editor cannot validate the actual multi-file state the user is editing.

The server also lacks source navigation for user-defined pure functions.

## Overlay workspace

The language server maintains the open document text it already receives through full-document synchronization.

For file-backed documents, module resolution uses open document text first and disk content only when no overlay exists for that path.

The same project root, relative import, `.vectis` extension, cycle rejection, and imported-module purity rules remain in force.

An unsaved imported buffer can therefore participate in normal semantic compilation without being written to disk first.

## Navigation scope

This RFC defines navigation for user-defined pure functions.

The supported requests are:

1. `textDocument/definition`.
2. `textDocument/references`.
3. `textDocument/rename`.

Navigation operates over the reachable deterministic import graph.

Built-in functions do not have source definitions.

Mission-local values are outside this RFC and retain their existing editor behavior.

## Definition

When the cursor is on a user-function declaration or call, definition returns the exact identifier range of the corresponding declaration.

A call to an imported function can therefore navigate to the imported source file, including an unsaved open buffer.

## References

References returns exact identifier ranges for reachable calls to the same user-defined function.

The client `includeDeclaration` flag controls whether the function declaration is included.

Results are deterministic by canonical file path and source position.

## Rename

Rename updates the declaration and reachable call sites for one user-defined function.

A rename target must be a valid VECTIS identifier, must not be a language keyword or built-in function name, and must not conflict with another user-function declaration in the reachable workspace.

The server returns a normal LSP `WorkspaceEdit`.

Rename does not modify files itself.

## Workspace selection

When navigation starts from an imported file, the server prefers the widest currently open entry workspace that contains that module.

This allows a function declaration in an open library buffer to find call sites in an open importing mission.

If no wider open workspace contains the file, the file is resolved as its own workspace entry.

## Diagnostics

Opening, changing, or saving a document republishes diagnostics for all currently open documents.

This ensures that an unsaved function change in an imported module can update diagnostics in an open importing mission immediately.

The compiler remains the semantic authority.

## Compatibility

The VECTIS grammar, typed AST, execution graph, runtime, module syntax, package version, and command-line execution behavior remain unchanged.

The LSP continues to use full-document synchronization.

## Test strategy

1. Prove an unsaved imported function can satisfy an importing mission without writing the module to disk.
2. Prove changing an imported overlay updates importer diagnostics.
3. Prove definition crosses from a function call to an imported declaration.
4. Prove references include reachable cross-file calls.
5. Prove rename emits edits for declaration and call sites.
6. Prove built-ins are not treated as user-source navigation targets.
7. Run the complete repository quality gate across every supported Python version.
