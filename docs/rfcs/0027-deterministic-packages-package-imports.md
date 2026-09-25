<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# RFC 0027: Deterministic Packages and Package Imports

## Status

Accepted and implemented.

## Problem

RFC 0026 gives individual source modules stable qualified spellings, but larger projects still depend on file paths at every import site. A project may want several internal files to form one reusable unit with a stable project-level name while retaining deterministic path resolution, direct export boundaries, and project-relative function identity.

VECTIS needs package organization that is local, inspectable, and filesystem bounded. Package resolution must not depend on registries, network requests, environment variables, search paths, installation order, or ambient process state.

## Project manifest

Packages are declared in the nearest project `vectis.toml` under the `packages` table. Each package has one entry module:

```toml
[project]
name = "example"

[packages.release]
entry = "packages/release/index.vectis"

[packages.security]
entry = "packages/security/index.vectis"
```

Package names must be VECTIS identifiers. Entry paths use canonical forward-slash syntax, are relative to the project root, and must reference `.vectis` source files inside that root.

The package declaration has exactly one field in this RFC: `entry`.

## Source syntax

A package is imported with contextual `package` syntax:

```vectis
import package "release";
import package "security" {audit, score};
import package "release" as rel;
```

The package name is a string because it identifies a manifest declaration rather than a source path.

`package` is contextual after `import`. It remains available as an ordinary function or value identifier elsewhere.

## Package qualifier

An unaliased package import uses the manifest package name as its source qualifier:

```vectis
import package "release";

let approved release.ready(score);
```

Package imports are namespace-only. They do not contribute function names to bare-call resolution.

An explicit RFC 0025 alias replaces the local qualifier for that import:

```vectis
import package "release" as rel;

let approved rel.ready(score);
```

The manifest package name remains the project package identity even when a source file chooses a local alias.

## Export surface

The direct public function declarations in the package entry module form the package export surface.

Transitive imports are implementation dependencies and do not become package exports. Private functions are not exports. A selective package import narrows the visible export surface:

```vectis
import package "release" {ready};
```

With that import, `release.ready(...)` is valid and another direct public function such as `release.score(...)` is rejected unless selected.

No separate export statement is introduced by this RFC.

## Relationship to module namespaces

A package entry module may also declare an RFC 0026 namespace. Package import syntax still uses the manifest package name, or an explicit local alias, as the qualifier.

The module namespace remains meaningful when the same source file is imported by path. This keeps module-owned namespace metadata separate from project-owned package organization.

## Function identity

Packages do not replace RFC 0024 `ModuleFunctionId`.

A call such as:

```vectis
import package "release";
let approved release.ready(score);
```

still binds to an identity shaped like:

```text
packages/release/index.vectis::ready
```

Type inference, recursion checks, compiler expansion, definition, references, rename, and signature help continue to consume the same project-relative function identity.

## Resolution rules

1. Package imports require a project root containing `vectis.toml`.
2. The package name must exist in the manifest `packages` table.
3. The package entry path must be canonical, project relative, root bounded, and end in `.vectis`.
4. The resolved package entry must exist as a source file, or as an editor overlay during workspace analysis.
5. Package entries and their imported dependencies remain subject to the pure imported-module contract.
6. Import cycles are detected by canonical source path regardless of whether an edge came from a path import or package import.
7. An unaliased package import exposes one qualifier equal to the package name.
8. An explicit alias exposes only the alias for that import.
9. Repeated unaliased imports of the same package may combine selective export sets deterministically.
10. A package qualifier that collides with another package qualifier, module namespace, or explicit alias fails before graph generation unless it is the same repeated package target.
11. Package imports do not participate in bare-call public-surface traversal.
12. Path imports retain RFC 0002 through RFC 0026 behavior when package syntax is absent.

## Manifest determinism

`vectis.toml` is parsed with the Python standard TOML parser already available in supported runtimes. Package declarations are sorted by package name for inspection output.

Package entry strings reject backslash syntax, absolute paths, empty segments, dot segments, parent segments, and non-VECTIS extensions. Canonical path resolution must remain inside the project root.

Package metadata grants no action authority.

## Editor behavior

Workspace loading resolves package imports through the same project manifest used by file compilation. Open document overlays may provide the package entry source even when that source has not been written to disk.

Definition, references, rename, and signature help operate on package-qualified function members through the existing `ModuleFunctionId` binding.

Semantic tokens classify contextual `package` in `import package "name";` as a keyword. The package name remains a string token. Qualified function members remain function tokens. The semantic-token legend does not change.

Unsaved edits to `vectis.toml` are outside this RFC.

## Module browser

The module browser reports project packages using project-relative information only. Each package record includes its name, entry path, and sorted direct public exports.

Package import records include the package name and resolved project-relative entry target. Invalid package metadata contributes safe project-level diagnostics without exposing absolute local paths.

The module-browser schema identifier remains stable because the package fields are additive.

## Project scaffolds

The starter project and starter template declare the reusable readiness module as a package and consume it through package import syntax. This makes the package contract visible in generated project structure without changing runtime authority.

## Authority and security

Package resolution is a compile-time source operation. It does not acquire filesystem capability and does not authorize runtime actions.

Resolution is limited to the existing project root. No package registry, remote URL, environment lookup, user home lookup, dependency installation, or automatic code download participates in package resolution.

## Compatibility

Projects without `import package` syntax keep their path-import, selective-import, alias, namespace, semantic, compiler, runtime, and editor behavior.

Existing `[project]` manifest fields remain valid. The `packages` table is interpreted only for package organization.

The package version remains `0.8.0`, and published release artifacts remain immutable.

## Alternatives considered

1. A remote package registry was rejected because resolution would depend on network state and external mutation.
2. Searching directories by package name was rejected because search order creates ambient resolution behavior.
3. Treating package imports as bare-name imports was rejected because package boundaries should not pollute the caller's bare namespace.
4. Replacing `ModuleFunctionId` with package identity was rejected because project-relative source identity already provides deterministic compiler and editor semantics.
5. Requiring every package entry to repeat the package name as a module namespace was rejected because project package identity and module namespace serve different scopes.
6. A separate package manifest file was rejected because `vectis.toml` already establishes the project boundary and metadata surface.

## Validation strategy

Coverage includes manifest parsing, canonical entry validation, contextual package syntax, namespace-only imports, direct exports, selective exports, private visibility, transitive isolation, alias overrides, qualifier collisions, repeated package imports, package and namespace interaction, project-relative identity, type validation, missing manifests, unknown packages, missing entries, imported-module purity, cycles, editor overlays, navigation, references, rename, signature help, semantic tokens, module browsing, generated project scaffolds, legacy module regressions, and the complete VECTIS unit suite.
