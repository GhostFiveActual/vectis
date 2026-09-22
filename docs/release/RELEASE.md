<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->
# VECTIS Release Process

## Release contract

A VECTIS release is built from a clean repository state and is accepted only when the source, package, documentation, tests, and runtime behavior agree.

## Verification

Run the repository gate:

```bash
bash tools/quality-gate.sh
```

Build the distributions:

```bash
python -m build
```

Install the wheel into an isolated environment outside the source tree, then verify:

```bash
vectis version
vectis doctor
vectis lsp --help
vectis check examples/showcase/full-release-assurance.vectis
vectis check examples/valid/pure-functions.vectis
vectis check examples/valid/structured-syntax.vectis
vectis check examples/valid/explicit-actions.vectis
vectis actions
vectis actions --config examples/action-profile.toml
vectis test .
vectis modules missions/main.vectis
vectis mission examples/showcase/full-release-assurance.vectis
vectis mission examples/valid/pure-functions.vectis
vectis mission examples/valid/structured-syntax.vectis
```

Launch the packaged applications:

```bash
vectis studio
vectis demo
```

## Release evidence

1. Passing CI on every supported Python version.
2. A successful wheel and source distribution build.
3. A successful isolated wheel installation.
4. Successful CLI execution outside the source tree.
5. Documentation that matches the shipped behavior.
6. Security regression coverage for authority boundaries.
7. A passing public-tree and reachable-history privacy audit.
8. Compatibility and migration documentation for language contract changes.
9. RFC evidence for durable language or authority contract changes.
10. An explicit software license when the project is distributed as open source.
11. An immutable annotated version tag.

## License

Release distributions include the Apache License 2.0 text in `LICENSE` and project attribution in `NOTICE`. Package metadata uses the SPDX expression `Apache-2.0`.
