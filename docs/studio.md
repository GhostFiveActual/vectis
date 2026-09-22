<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# VECTIS Mission Control Studio

VECTIS Studio is the visual Mission Control workbench packaged with the VECTIS distribution. It exists to make the language and its execution model visible while preserving the same deterministic compiler and runtime used by the command line.

## Launch

```bash
vectis studio
```

The `vectis app` command remains an alias.

## Mission Control workspace

Studio combines mission source, execution topology, runtime telemetry, diagnostics, resolved values, and the built in language reference in one local interface.

The product should feel active because the execution is visible, not because the interface hides logic behind animation. Nodes, branches, values, and failures remain tied to real compiler and runtime state.

## Operator workflow

1. Load or write a mission.
2. Format the source into canonical VECTIS form.
3. Check syntax and semantics.
4. Compile the execution topology.
5. Execute the mission.
6. Inspect node states and resolved values.
7. Review diagnostics, syntax tree, or raw graph data when deeper analysis is needed.

## Local boundary

Studio binds to loopback by default. Remote binding requires explicit opt in.

The local API exposes health, examples, built ins, check, parse, plan, run, and format operations.

## Product relationship

Studio is Mission Control for authoring and inspection. The Launch Control application launched by `vectis demo` is a separate product demonstration that embeds VECTIS as its decision engine.

Both surfaces use the same canonical language implementation.
