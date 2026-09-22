<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# Deterministic Modules Example

This example separates reusable pure logic from the executable entry mission.

Run it from the repository root:

```bash
vectis modules examples/modules/main.vectis
vectis check examples/modules/main.vectis
vectis mission examples/modules/main.vectis
```

The imported file contains pure functions only. Import resolution remains inside the repository project root because the root `vectis.toml` defines the boundary for this checkout.
