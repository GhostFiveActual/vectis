<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# VECTIS Examples

The canonical examples live under `examples/` and are covered by automated tests.

For the current language surface, start with:

```text
examples/valid/release-gate.vectis
examples/valid/functions.vectis
examples/valid/structured-values.vectis
examples/valid/pure-functions.vectis
examples/valid/assertions.vectis
```

Use:

```bash
vectis inspect examples/valid/pure-functions.vectis
vectis run examples/valid/pure-functions.vectis
```

The invalid and semantic-invalid directories provide deterministic negative fixtures for diagnostics and conformance testing.
