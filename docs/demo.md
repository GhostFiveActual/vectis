<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# VECTIS Demonstrations

VECTIS provides two different demonstrations because they prove different parts of the product.

## Scripted compiler and runtime demo

Run:

```bash
python examples/demo/run_demo.py
```

This validates the canonical example through the public parser, compiler, graph, and runtime APIs. Any syntax or semantic diagnostic remains visible through the same public contracts used by the CLI.

The same source can be inspected through the CLI:

```bash
vectis inspect examples/demo/demo.vectis
vectis run examples/demo/demo.vectis
```

## Launch Control application

Run:

```bash
vectis demo
```

Launch Control accepts flight-system, navigation, communications, range, payload, fuel, weather, quality, and risk inputs. The backend generates a multi-gate VECTIS mission, compiles it, executes it, and returns the real graph, gate values, runtime trace, plan metrics, and GO or HOLD decision. Preset scenarios provide nominal, weather HOLD, systems HOLD, and risk HOLD demonstrations.

The application demonstrates that VECTIS can sit inside another product rather than requiring a user to work directly in the language.

## Studio

Run:

```bash
vectis studio
```

Studio is the Mission Control workbench for editing and inspecting VECTIS. Launch Control is a separate application built on the same compiler and runtime.


## Proof report

After a Launch Control scenario executes, **Open Proof Report** produces a standalone HTML execution record from the exact VECTIS graph and runtime result. The report includes plan identity, structural metrics, stages, node states, values, failures, and published output.
