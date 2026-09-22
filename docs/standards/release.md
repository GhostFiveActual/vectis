<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# Release Standard

## Release principle

A release is a reproducible, inspectable repository state. Published tags are immutable.

## Required evidence

1. The release commit is identified.
2. The repository quality gate passes.
3. CI passes on every supported Python version.
4. The package builds from a clean checkout.
5. The built package installs outside the source tree.
6. Primary commands execute from the installed package.
7. Security boundaries have regression coverage.
8. Documentation matches shipped behavior.
9. Compatibility impact and migration requirements are documented.
10. The public tree and reachable Git history pass the privacy audit.
11. Release notes state material behavior and known limits.
12. License and attribution metadata match the shipped package.

## Version discipline

Patch releases preserve the documented contract of their current minor line. Before 1.0, deliberate contract revisions belong in a later minor version with migration guidance. At or after 1.0, incompatible stable-contract changes require a major version.

Release decisions follow [COMPATIBILITY.md](../../COMPATIBILITY.md).
