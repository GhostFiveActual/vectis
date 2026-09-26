<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# RFC 0029: Deterministic Package Fingerprints

## Status

Accepted and implemented.

## Problem

RFC 0027 gives project-local packages stable names and bounded entry modules. RFC 0028 adds exact local versions and direct dependency contracts. Those contracts describe how packages compose, but they do not provide one portable identity for the exact package content and dependency closure that was inspected.

Version strings alone are not content identities. A package can retain the same declared version while its source changes. Absolute paths, checkout locations, timestamps, environment state, and filesystem metadata are also unsuitable inputs because they make identity depend on the machine performing the inspection.

VECTIS needs a deterministic package fingerprint that can be compared across equivalent project checkouts and later used by local multi-project dependency boundaries.

## Fingerprint algorithm

A package fingerprint is the lowercase hexadecimal SHA-256 digest of a canonical JSON package descriptor.

Canonical JSON uses sorted object keys, UTF-8 encoding, no insignificant whitespace, and stable list ordering defined by this RFC.

The schema identifier is:

```text
vectis.package-fingerprint/v1
```

The algorithm identifier is SHA-256. The schema fixes the descriptor shape so future incompatible fingerprint rules require a different schema identifier.

## Package descriptor

The descriptor contains these fields:

1. `schema`, containing `vectis.package-fingerprint/v1`.
2. `name`, containing the project package name.
3. `entry`, containing the canonical project-relative entry path.
4. `version`, containing the exact RFC 0028 version or `null` for an RFC 0027 compatible unversioned package.
5. `files`, containing the package implementation files sorted by project-relative path.
6. `dependencies`, containing direct dependency records in manifest order, which is already sorted by package name.

Each implementation file record contains its project-relative path and the SHA-256 digest of its normalized UTF-8 source text.

Each dependency record contains the dependency package name, the exact required version, and that dependency package's recursively computed fingerprint.

## Implementation source closure

The package implementation source closure uses the same ownership boundary established by RFC 0028.

The closure begins at the package entry module. Ordinary path imports extend the closure. Package imports stop the source closure and are represented through dependency fingerprints instead.

A path-imported helper therefore participates in the owning package fingerprint. A package reached through `import package` participates through its dependency fingerprint rather than being copied into the parent's file list.

If a package implementation imports another package without a direct dependency contract, fingerprinting fails closed using the RFC 0028 composition rule.

## Dependency closure

Direct dependency records participate even when the package source does not currently import that dependency. The dependency table is part of the declared package contract, so removing, replacing, or changing a declared dependency changes the package fingerprint.

Dependency fingerprints are recursive. If package `release` depends on `policy`, and `policy` depends on `core`, a source change in `core` changes the `core` fingerprint, then the `policy` fingerprint, then the `release` fingerprint.

RFC 0028 already rejects dependency cycles, so recursive dependency fingerprinting has a deterministic termination boundary.

## Source normalization

Source text is decoded as UTF-8 and line endings are normalized before hashing:

1. CRLF becomes LF.
2. Remaining CR becomes LF.
3. All other source bytes represented by the decoded text remain significant.

This rule prevents equivalent Git checkouts from receiving different fingerprints solely because one checkout materialized CRLF line endings and another materialized LF line endings.

Comments, spacing, source ordering, and other source text changes remain significant. The fingerprint identifies package content, not formatter equivalence or semantic equivalence.

## Inputs deliberately excluded

The package fingerprint does not contain or derive from:

1. Absolute filesystem paths.
2. Project checkout location.
3. File modification times.
4. File ownership or permission metadata.
5. Environment variables.
6. User home state.
7. Registry state.
8. Network content.
9. Runtime action grants.
10. Unrelated project files outside the package implementation and dependency closure.

The same package content and manifest contract therefore produce the same fingerprint in different checkout roots.

## Unversioned package compatibility

RFC 0027 compatible packages that declare only `entry` can be fingerprinted. Their descriptor contains `version: null`.

An unversioned package still cannot satisfy an RFC 0028 dependency declaration because RFC 0028 requires exact versions for dependency targets. Fingerprinting does not weaken that rule.

## Editor overlays

The public fingerprint API accepts optional source overlays keyed by source path. An overlay replaces the saved source text for fingerprint computation without writing to disk.

This keeps read-only project inspection consistent with editor workflows while leaving `vectis.toml` manifest overlays outside the contract, matching the existing package and workspace rules.

## Module browser

The module browser exposes a `fingerprint` field for every package whose fingerprint can be computed.

The value is the same 64-character lowercase SHA-256 string returned by the package fingerprint API. Browser output remains project relative and must not expose checkout paths.

If fingerprint derivation fails, the browser reports a safe package diagnostic rather than raising an unhandled exception. Existing package version, dependency, export, module, and import fields retain their meaning.

The module-browser schema identifier remains stable because the package fingerprint field is additive.

## Public Python interface

`vectis.package_fingerprint` exposes:

```python
package_descriptor(root, package_name, *, overlays=None, manifest=None)
package_fingerprint(root, package_name, *, overlays=None, manifest=None)
```

`package_descriptor` returns the canonical descriptor. `package_fingerprint` returns its SHA-256 digest.

`PackageFingerprintError` reports deterministic failures such as an unknown package, missing implementation source, escaping path import, path import cycle, parse failure needed for import discovery, or undeclared package import.

## Fingerprint meaning

A package fingerprint is content identity evidence. It is not a signature, trust decision, validity certificate, authorization grant, or proof that the package compiles successfully.

Fingerprint equality means the canonical descriptor inputs are equal under this RFC. It does not establish who authored the package or whether the package should be trusted or executed.

## Function and graph identity

Package fingerprints do not replace RFC 0024 `ModuleFunctionId` and do not enter execution graph node identity.

Compiler expansion, static types, recursion analysis, source navigation, references, rename, signature help, graph fingerprints, and runtime scheduling continue to use their existing contracts.

This separation keeps package content identity available for dependency verification without changing language semantics.

## Determinism properties

The following properties are required:

1. Repeated computation against the same package state yields the same fingerprint.
2. Equivalent package state under different project checkout roots yields the same fingerprint.
3. LF and CRLF materializations of the same source text yield the same fingerprint.
4. A package implementation source change changes the fingerprint.
5. A path-imported implementation source change changes the fingerprint.
6. A declared dependency source change changes the parent fingerprint recursively.
7. A package version change changes the fingerprint.
8. An unrelated project file change does not change the fingerprint.
9. A sibling package change does not change another package unless that sibling participates in its declared dependency closure.
10. Manifest declaration ordering that does not change the validated package contract does not change the fingerprint.

## Authority and security

Fingerprint computation is a read-only project inspection operation. It grants no filesystem, process, HTTP, or other runtime capability.

Resolution remains bounded by the existing project root. The implementation performs no registry access, network request, package installation, environment lookup, or user-home lookup.

Project-relative diagnostic text is preferred so failed fingerprint operations do not expose local checkout paths through public inspection surfaces.

## Compatibility

RFC 0027 and RFC 0028 source syntax and manifest syntax remain unchanged.

Existing package versions, dependency contracts, aliases, selectors, namespaces, visibility, function identity, compiler behavior, runtime scheduling, and authority boundaries remain unchanged.

The package version remains `0.8.0`, and published release artifacts remain immutable.

## Alternatives considered

1. Hashing only `vectis.toml` metadata was rejected because source changes would not affect package identity.
2. Hashing only the package entry file was rejected because path-imported implementation files would be omitted.
3. Hashing absolute paths was rejected because checkout location would affect identity.
4. Hashing raw platform line endings was rejected because equivalent Git materializations could differ across systems.
5. Excluding declared but unused dependencies was rejected because the dependency table is part of the package contract.
6. Hashing only direct dependencies without recursive fingerprints was rejected because transitive package content changes would not reach the parent identity.
7. Replacing `ModuleFunctionId` or execution graph fingerprints was rejected because package content identity serves a different boundary.
8. Treating the fingerprint as a security signature was rejected because SHA-256 content identity alone does not establish authorship or trust.

## Validation strategy

Coverage includes repeated computation, cross-root stability, line-ending normalization, own-source changes, comment changes, path-imported helper changes, unrelated-file isolation, sibling-package isolation, version participation, RFC 0027 unversioned compatibility, manifest-order stability, declared dependency participation, transitive dependency propagation, editor overlays, unknown packages, missing entries, missing path imports, project-root escapes, undeclared package imports, project-relative descriptors, browser exposure, browser privacy, RFC 0027 package regressions, RFC 0028 composition regressions, and the complete VECTIS unit suite.
