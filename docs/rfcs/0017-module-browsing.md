<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# RFC 0017: Deterministic Module Browsing

## Summary

VECTIS exposes a project-wide, read-only module browser over the same project boundary and parser contracts used by deterministic source modules.

## Problem

`vectis modules FILE` reports the resolved module set for one entry source. Editors and operators also need to inspect the project as a whole: which `.vectis` files exist, which files import one another, which pure functions each file declares, and which files contain executable statements.

That view must not create a second import system. It must preserve the existing project boundary, relative import rules, `.vectis` extension contract, and source parser while remaining useful when an editor buffer has unsaved changes.

## Project catalog

`vectis.module_browser` defines `MODULE_BROWSER_SCHEMA` and `browse_project_modules()`.

The browser locates the nearest VECTIS project root and recursively catalogs `.vectis` source files inside that root. Results use project-relative paths only.

Each module record includes its relative path, parse and import-resolution status, module kind, importability, declared imports, pure-function names and parameter lists, executable statement count, safe diagnostics, and whether the source came from an editor overlay.

The catalog also includes resolved dependency edges, deterministic import cycles, rejected symbolic-link paths, module count, and edge count.

## Import resolution

Browsing does not change import behavior. Relative imports are resolved against the importing source and must remain inside the project root. Absolute paths, root escapes, non-`.vectis` targets, and missing modules are reported as import-resolution failures.

A module is importable only when it parses successfully, all of its imports resolve, and it contains no executable top-level statements. Resolved dependency edges describe source relationships only. Browsing does not flatten or compile a program.

## CLI

The existing command remains unchanged:

```text
vectis modules FILE
```

Project browsing is additive:

```text
vectis modules PATH --browse
```

`PATH` may identify a project directory or a file within the project. The browser returns a deterministic JSON catalog.

## Editor integration

The language server advertises `vectis.modules.inspect` through `workspace/executeCommand`. Clients provide one argument object containing a file-backed document `uri`. The selected document identifies the project root.

Open VECTIS documents inside that root replace saved source for browsing. An unsaved file-backed `.vectis` document inside the project is included even when it exists only in the open editor overlay. The command is read-only and returns project-relative paths only.

## Path and authority boundaries

The browser does not follow symbolic-link directories or symbolic-link `.vectis` sources. Rejected links are reported by relative path without resolving their external target into the response.

The browser performs no mission execution, graph execution, action-profile selection, capability grant, network request, process creation, package installation, or source write. Runtime filesystem authority is not required because module browsing is a compiler and editor tooling operation bounded to the selected VECTIS project.

## Diagnostics

Parser and lexer failures are projected with stable diagnostic code, severity, message, line, and column. Absolute local source paths are not returned. Import failures use the existing `SEM006` code and safe project-relative target labels where available.

Browsing continues across invalid modules so an editor can present the rest of the project catalog while identifying broken files.

## Determinism

Module discovery order is lexicographic by project-relative path. Imports, dependency edges, cycles, rejected paths, and function declarations preserve deterministic source or sorted order as appropriate. The same disk and overlay state produces the same browsing payload.

## Compatibility

Grammar, AST contracts, compiler IR, runtime scheduling, module loading, capability enforcement, action profiles, execution receipts, package version, and published releases do not change. `vectis modules FILE` retains its existing entry-resolution behavior.

## Test strategy

Tests cover deterministic project-relative catalogs, function and executable classification, safe import failures, safe parser diagnostics, unsaved overlays, cycle reporting, CLI compatibility, LSP advertisement and overlay behavior, repository policy, and the complete repository suite.
