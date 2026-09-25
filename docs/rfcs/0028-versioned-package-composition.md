<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# RFC 0028: Versioned Package Composition

## Status

Accepted and implemented.

## Problem

RFC 0027 gives a project deterministic package names, bounded entry modules, direct export surfaces, and namespace-only package imports. It does not express which packages a package implementation is allowed to compose with or which exact local package version that composition expects.

Large local projects need dependency contracts that remain inspectable and deterministic without introducing registry lookup, version-range solving, installation order, or ambient search paths.

## Manifest contract

Package declarations may include an exact three-part version and a table of direct package dependencies:

```toml
[packages.core]
entry = "packages/core/index.vectis"
version = "1.4.0"

[packages.release]
entry = "packages/release/index.vectis"
version = "2.0.0"

[packages.release.dependencies]
core = "1.4.0"
```

The `version` field is optional for compatibility with RFC 0027. A package referenced by another package dependency must declare a version.

Dependency values are exact versions. RFC 0028 does not define version ranges, compatibility operators, prerelease identifiers, build metadata, registry coordinates, or dependency installation.

## Exact version syntax

A package version has the form `MAJOR.MINOR.PATCH`. Each component is a nonnegative decimal integer. Leading zeroes are rejected except for the single value `0`.

Examples of valid versions include `0.0.0`, `1.4.0`, and `12.3.27`.

Forms such as `1`, `1.2`, `01.2.3`, `v1.2.3`, and `1.2.3-beta` are outside this RFC and fail manifest validation.

## Dependency declarations

A dependency table maps a direct package name to the exact version required by the importing package.

A dependency declaration is valid only when all of these conditions hold:

1. The dependency name is a valid VECTIS package identifier.
2. The dependency names another package in the same project manifest.
3. The dependency target declares an exact version.
4. The required version exactly equals the target package version.
5. A package does not depend on itself.
6. The manifest dependency graph is acyclic.

Dependency records are sorted by package name for deterministic inspection.

## Source composition rule

Dependencies do not import source code automatically. Source files still use RFC 0027 package import syntax:

```vectis
import package "core";
```

When a package implementation imports another package, the imported package must appear in the importing package's direct dependency table.

A package implementation consists of its entry module plus every module reached from that entry through ordinary path imports only. Package import edges stop the implementation closure and begin the dependency package's own implementation boundary.

This means a helper module reached by path from `release` is still governed by `release` dependency contracts.

## Direct dependency isolation

Dependency contracts do not propagate transitively. If `release` depends on `policy` and `policy` depends on `core`, the `release` implementation may import `policy`. It may not import `core` directly unless `release` also declares an exact dependency on `core`.

This preserves explicit composition at every package boundary.

## Entry-source compatibility

A mission or other project entry source is not itself a package implementation merely because it imports a package. Project entry sources may continue to import declared packages directly without declaring package dependency contracts.

RFC 0028 therefore does not turn the project root into an implicit package.

## Shared implementation modules

A path-imported module may be reachable from more than one package entry. Its package imports must satisfy the dependency contracts of every package implementation closure that reaches it.

This rule avoids assigning hidden ownership to shared source files.

## Function identity

Package versions and dependency contracts do not alter RFC 0024 `ModuleFunctionId`.

A function exported from a versioned package still has project-relative identity such as:

```text
packages/core/index.vectis::ready
```

Version metadata does not become part of function identity, graph node identity, type inference, recursion analysis, navigation, references, rename, or signature help.

## Resolution and validation order

Manifest validation occurs before package composition is accepted. Exact target versions, unknown dependencies, self dependencies, and dependency cycles therefore fail before graph generation.

After source imports resolve, each loaded package implementation closure is checked for package imports that lack a direct dependency contract.

The compiler loader and overlay-aware editor workspace use the same composition validation rule.

## Module browser

The module browser exposes package versions and sorted direct dependency contracts using project-relative information only.

Each package record includes its package name, entry path, optional version, dependency records, and direct public exports.

The browser also reports a package-level diagnostic when a package implementation imports another package without the required direct dependency contract.

The existing module-browser schema identifier remains stable because these fields are additive.

## Project scaffolds

The starter project and starter template declare the readiness package with version `1.0.0`. They do not require dependencies because the readiness package has no package imports.

This keeps generated projects compatible while making exact package version metadata visible in the default manifest.

## Determinism

RFC 0028 adds no resolver search order. All package names, versions, dependency targets, entry paths, and source paths are local project data.

There is no registry access, network access, environment lookup, user-home lookup, package installation, or version solver.

The same manifest and source tree therefore produce the same package composition decisions.

## Authority and security

Version and dependency metadata grant no runtime authority. Package composition remains a compile-time source validation operation and does not acquire filesystem, process, HTTP, or other action capability.

Project-root path boundaries from RFC 0002 and RFC 0027 remain unchanged.

## Compatibility

RFC 0027 package declarations that contain only `entry` remain valid. A package may also declare `version` without declaring dependencies.

Existing project entry sources may import packages directly. Dependency enforcement applies only to package implementation closures.

Package syntax, namespace behavior, selectors, aliases, visibility, project-relative function identity, compiler expansion, runtime scheduling, and action authority remain unchanged.

The package version remains `0.8.0`, and published release artifacts remain immutable.

## Alternatives considered

1. Version ranges were rejected because they require additional solving rules and create more than one acceptable resolution state.
2. Remote package coordinates were rejected because they would introduce external mutable state and network dependency.
3. Automatic imports from dependency tables were rejected because dependency metadata should not hide source-level intent.
4. Transitive dependency access was rejected because it weakens package boundaries and makes composition depend on another package's implementation choices.
5. Embedding versions into `ModuleFunctionId` was rejected because source identity and package compatibility metadata serve different purposes.
6. Requiring a version on every RFC 0027 package was rejected because exact versions are only necessary when another package forms a dependency contract with that package.

## Validation strategy

Coverage includes RFC 0027 compatibility, exact version syntax, dependency parsing and ordering, unknown dependency rejection, unversioned target rejection, exact mismatch rejection, self dependency rejection, cycle rejection, declared and undeclared composition, path-imported implementation modules, direct dependency isolation, shared package boundaries, entry-source compatibility, identity stability, LSP parity, module-browser records and diagnostics, starter scaffolds, package regressions, module regressions, and the complete VECTIS unit suite.
