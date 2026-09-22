<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# RFC 0002: Deterministic Source Modules

Status: Accepted and implemented for VECTIS 0.5.

## Problem

A single source file is sufficient for small missions, but durable projects need reusable pure logic to be shared across multiple files. Reuse must not create hidden execution, ambient authority, nondeterministic discovery, or path behavior that changes by machine.

## Syntax

An entry file may import another VECTIS source file:

```vectis
import "../lib/readiness.vectis";
```

Imported files may contain further imports and top-level pure function declarations.

## Resolution

1. Import paths are relative to the file that contains the import.
2. Paths must identify a `.vectis` file.
3. The module root is the nearest ancestor containing `vectis.toml`.
4. When no project manifest exists, the entry file directory is the module root.
5. Canonical resolved paths must remain inside the module root.
6. A canonical module path is loaded at most once per compilation.
7. Transitive imports are visited deterministically in source order.
8. Import cycles are rejected before semantic analysis and graph generation.

## Imported module contract

Imported modules may contain:

1. Import declarations.
2. Top-level pure function declarations.

Imported modules may not contain missions, stages, sources, values, assertions, publications, capability statements, requests, analysis nodes, or any other executable statement.

The entry file remains the only location that contributes executable mission statements to the compiled program.

## Compilation model

Module loading produces one merged compilation program. Imported pure functions are placed before entry-file functions and executable statements, preserving the existing function semantic analyzer and compile-time function expansion model.

Imports do not produce execution graph nodes. They affect source composition only.

## Determinism

For the same entry source, module files, VECTIS version, and project layout, module resolution produces the same canonical module set and merged program.

Resolution does not search environment paths, user directories, package registries, the network, or process state.

## Authority

Module loading reads source files because compilation from a file necessarily reads source. This is distinct from VECTIS runtime filesystem capability.

An imported module cannot grant or request runtime authority merely by being imported. Imported files cannot contain executable capability statements.

## Failure behavior

Compilation fails before graph generation when:

1. An imported file does not exist.
2. A path is absolute.
3. A path escapes the project root.
4. A path does not reference a `.vectis` file.
5. The module graph contains a cycle.
6. An imported module contains executable statements.

These failures use the module-resolution semantic diagnostic family.

## Inspection

`vectis modules FILE` exposes the resolved entry, project root, ordered module set, and module count.

`vectis inspect FILE` exposes both the authored entry AST and the resolved AST used for compilation.

## Compatibility

The 0.5 patch line preserves relative resolution, project-root confinement, pure-only imported modules, canonical single-load behavior, and fail-closed cycle handling.

Future namespace, alias, selective-import, or package features must remain explicit and require a separate compatibility review.

## Alternatives considered

Implicit file discovery was rejected because it makes source meaning depend on ambient directory contents.

Runtime imports were rejected because they would mix source composition with execution authority.

Allowing missions in imported files was rejected because it would hide executable behavior behind an import statement.

Network package imports were deferred because they require a separate trust, reproducibility, integrity, and version-resolution model.

## Test strategy

Regression coverage verifies direct imports, transitive imports, duplicate suppression, cycle rejection, project-root confinement, missing modules, extension validation, imported-module restrictions, formatting, project scaffolding, installed-wheel CLI behavior, and release artifact behavior.
