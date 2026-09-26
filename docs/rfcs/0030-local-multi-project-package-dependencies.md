<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# RFC 0030: Local Multi-Project Package Dependencies

## Status

Accepted and implemented.

## Problem

RFC 0027 defines deterministic packages inside one VECTIS project. RFC 0028 gives those packages exact versions and direct dependency contracts. RFC 0029 gives each package a portable SHA-256 fingerprint over its implementation and dependency closure.

Those contracts stop at one `vectis.toml`. A larger local workspace may keep reusable packages in separate VECTIS projects, but importing such source through ordinary relative file paths would weaken project boundaries and make package identity depend on ad hoc filesystem reachability.

VECTIS needs an explicit local multi-project boundary that can name one package in another local project, pin its exact version and RFC 0029 fingerprint, verify the target before source loading, and preserve the provider project as the boundary for all of its own path imports and package dependencies.

## Manifest contract

A consuming project declares external local package bindings under `local_dependencies`:

```toml
[local_dependencies.shared_core]
project = "../shared-core"
package = "core"
version = "1.4.0"
fingerprint = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
```

The table key is the local dependency alias. Source imports that alias through existing RFC 0027 syntax:

```vectis
import package "shared_core";

mission "Release" {
    publish shared_core.ready(96);
}
```

No source grammar change is introduced by this RFC.

## Local dependency fields

Each local dependency declaration has exactly four fields:

1. `project` is a canonical relative path from the consuming project root to another local VECTIS project.
2. `package` is the target package name inside that project's `vectis.toml`.
3. `version` is the exact RFC 0028 `MAJOR.MINOR.PATCH` version expected from the target package.
4. `fingerprint` is the exact lowercase 64-character RFC 0029 SHA-256 package fingerprint expected from the target package.

The local dependency alias and target package name must be valid VECTIS identifiers and cannot be boolean literal names.

## Project path rules

A local dependency project path is explicit local source configuration. It may reference a sibling or nested project and therefore may contain parent segments such as `../shared-core`.

The path must use forward slashes, must be relative, cannot contain drive syntax, cannot contain empty segments, and cannot contain dot segments. The resolved path cannot identify the consuming project itself.

Resolution does not search parent directories, sibling directories, the user home directory, environment paths, installed packages, registries, or network locations. Only the declared project path participates.

## Binding verification

A local dependency binding is accepted only when all of these conditions hold:

1. The declared project directory exists.
2. The target project contains `vectis.toml`.
3. The target manifest is valid under the package rules supported by the current language implementation.
4. The target package exists in that manifest.
5. The target package declares the exact version pinned by the consumer.
6. The target package's computed RFC 0029 fingerprint exactly matches the pinned fingerprint.
7. The target package entry and implementation source satisfy the existing package source rules.

Any mismatch fails before graph generation.

## Namespace and import behavior

The local dependency alias occupies the same import-facing namespace category as a project-local package name. A project cannot declare a project-local package and a local dependency with the same name.

An unaliased import uses the local dependency alias as its qualifier:

```vectis
import package "shared_core";
let allowed shared_core.ready(score);
```

RFC 0025 aliases and RFC 0027 selectors remain available:

```vectis
import package "shared_core" {ready} as core;
let allowed core.ready(score);
```

Package imports remain namespace-only. A local dependency does not inject bare function names.

## Package composition contracts

A project-local package may depend on a local dependency alias through the existing RFC 0028 dependency table:

```toml
[packages.release]
entry = "packages/release.vectis"
version = "2.0.0"

[packages.release.dependencies]
shared_core = "1.4.0"
```

The required version must equal the version pinned by the `local_dependencies.shared_core` declaration.

A project entry source may import a local dependency directly without becoming a package, matching the RFC 0028 rule for project-local packages.

A package implementation that imports a local dependency must declare that alias as a direct dependency. Transitive dependency access remains disallowed.

## Provider-owned resolution boundary

Every loaded source module has one owning project root.

For a module owned by the consuming project, ordinary path imports remain bounded by the consuming project root. For a module loaded from a local dependency project, ordinary path imports are resolved relative to that provider project and must remain inside that provider project root. An ordinary path import also cannot cross into a nested directory that has its own `vectis.toml`; entering another project requires an explicit package binding even when that project is physically below the importing project directory.

Package imports inside provider source are resolved against the provider project's own manifest. They never fall back to the consuming project's manifest.

This ownership rule applies recursively when a provider project has its own local dependencies.

## Transitive local projects

Local multi-project dependencies may form an acyclic chain. For example, an application project may bind `policy_ref`, while the policy project binds `core_ref`.

When application source imports `policy_ref`, VECTIS verifies the policy binding. When policy source imports `core_ref`, VECTIS resolves that alias from the policy project's manifest and verifies the core binding there.

A consuming project does not gain direct access to a provider project's dependency aliases unless it declares its own binding for them.

Cross-project dependency cycles fail closed during recursive fingerprint or source resolution.

## Package fingerprints

RFC 0029 package fingerprints extend across explicit local dependency bindings without changing the `vectis.package-fingerprint/v1` descriptor schema.

When a package dependency name identifies a local dependency alias, the dependency record contains the alias, required version, and the verified fingerprint of the target package. The target fingerprint is computed from the provider project using its own manifest and dependency boundaries.

The pinned fingerprint must match the computed target fingerprint. Source drift in a provider therefore invalidates the consuming binding until the manifest pin is intentionally changed.

Equivalent multi-project layouts with the same relative project paths, package contents, versions, dependency contracts, and fingerprints produce equal package fingerprints regardless of absolute checkout location.

## Function identity

RFC 0024 `ModuleFunctionId` remains the function identity mechanism.

Modules inside the consuming project retain their existing project-relative labels. Modules outside that root use a composition-relative label anchored at the consuming project root. For example:

```text
../shared-core/packages/core.vectis::ready
```

Absolute filesystem paths never become `ModuleFunctionId` labels.

The composition-relative label is determined from explicit local project layout and source location. Version and fingerprint values do not become part of function identity.

## Compiler and runtime

Local multi-project dependency resolution occurs before compilation. Once source is loaded and function identities are bound, compiler expansion and execution graph generation use the existing VECTIS pipeline.

This RFC does not create runtime package nodes, runtime dependency resolution, runtime filesystem authority, or package execution authority.

## Editor behavior

The overlay-aware workspace loader applies the same owning-project and binding-verification rules as the file loader.

Definition, references, rename, signature help, semantic analysis, and compilation continue to use `ModuleFunctionId`. Navigation may therefore resolve to a source file in an explicitly bound local dependency project.

Source overlays participate in RFC 0029 fingerprint verification. An overlay that changes provider package content without a matching manifest fingerprint causes the consuming dependency boundary to fail closed. Manifest overlays remain outside the current editor contract.

## Module browser

The module browser exposes local dependency bindings using project-relative information only. Each local dependency record contains:

1. The local alias.
2. The declared relative project path.
3. The target package name.
4. The exact version.
5. The pinned fingerprint.
6. The composition-relative target entry path when resolution succeeds.
7. A deterministic resolution status.

Package import records can point to an external target using a composition-relative path such as `../shared-core/core.vectis`.

External source modules are not folded into the browsed project's internal module-edge graph. The browser keeps that graph scoped to modules owned by the selected project while exposing the cross-project edge through the import and local dependency records.

The module-browser schema identifier remains stable because the fields are additive.

## Determinism

Local multi-project resolution depends only on explicit project-relative manifest data and local source content.

There is no registry, network request, package installer, environment lookup, home-directory lookup, directory search order, version range solver, or implicit fallback.

Exact version and content fingerprint pins make target drift observable before compilation.

## Authority and security

A local dependency path authorizes compile-time source inspection only for the explicitly referenced local project. It does not grant runtime filesystem capability or any action capability.

Ordinary path imports remain bounded by the project that owns the importing module. An external package cannot use a path import to escape its provider project merely because the consuming project declared a local dependency path.

Package metadata and fingerprints remain non-secret structural data and do not establish authorship, trust, or execution permission.

## Compatibility

Projects without `local_dependencies` keep RFC 0002 through RFC 0029 package, module, compiler, editor, and runtime behavior.

Existing package names, package dependency tables, selectors, aliases, namespaces, public/private visibility, and project entry import behavior remain unchanged.

The package version remains `0.8.0`, and published release artifacts remain immutable.

## Alternatives considered

1. Allowing ordinary file imports to escape the project root was rejected because it would weaken the deterministic module boundary and bypass package identity checks.
2. Searching sibling directories by package name was rejected because filesystem layout and search order would become ambient resolver state.
3. Using version alone was rejected because RFC 0029 established that version strings do not identify exact content.
4. Using fingerprint alone was rejected because exact semantic version contracts remain useful inspectable metadata.
5. Copying provider source into the consuming project was rejected because it would hide the actual ownership boundary and create synchronization ambiguity.
6. Remote Git or registry coordinates were rejected because this RFC is intentionally local and deterministic.
7. Adding separate source syntax for external projects was rejected because the manifest alias already gives package imports an explicit local name without expanding the language grammar.

## Validation strategy

Coverage includes manifest parsing, path canonicalization, exact field validation, alias collisions, version matching, fingerprint matching, missing projects, missing manifests, missing target packages, direct external imports, package-owned external dependencies, undeclared dependency rejection, provider path-import confinement, transitive provider resolution, cross-project cycles, selectors and aliases, composition-relative function identity, compiler execution, editor navigation and rename, module browser records, fingerprint pin refresh, portability across equivalent layouts, RFC 0027 through RFC 0029 regressions, and the complete VECTIS unit suite.
