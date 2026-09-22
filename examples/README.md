<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# VECTIS Examples

The example tree serves two purposes: language conformance and complete product demonstration.

## Showcase

`showcase/full-release-assurance.vectis` is the primary public example. It is intentionally large enough to produce a detailed Mission Control trace.

Run it:

```bash
vectis mission examples/showcase/full-release-assurance.vectis
```

Validate it:

```bash
vectis check examples/showcase/full-release-assurance.vectis
```

Inspect the entire compiler surface:

```bash
vectis inspect examples/showcase/full-release-assurance.vectis
```

Export the graph:

```bash
vectis graph examples/showcase/full-release-assurance.vectis --format mermaid
```

## Language fixtures

| Directory | Purpose |
| --- | --- |
| `valid/` | Canonical supported syntax. |
| `semantic-invalid/` | Programs that parse but fail semantic validation. |
| `invalid/` | Lexer and parser failure fixtures. |
| `demo/` | Scripted compiler and runtime demonstration. |
| `showcase/` | Complete end to end product examples. |
