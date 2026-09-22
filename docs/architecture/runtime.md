<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# Runtime Architecture

The VECTIS runtime executes a validated `ExecutionGraph`; it does not execute raw source text.

## Inputs

A runtime receives:

* an immutable execution graph,
* an optional explicit set of available capability names,
* optional handlers for node kinds that require host integration.

## Scheduling

The graph provides a deterministic topological order using an insertion-order-preserving priority queue. Runtime execution indexes nodes, dependencies, branch edges, and scalar values once per run so large plans avoid repeated full-graph scans. A node runs only after its dependency predecessors reach terminal states. Failed dependencies block downstream nodes.

Conditional edges are explicit:

* a true condition activates `true` edges and skips `false` edges,
* a false condition activates `false` edges and skips `true` edges.

Every node compiled inside a branch is condition-gated.

## Value environment

Source and `let` nodes produce values. Runtime expression evaluation resolves references from dependency-node results, so conditions and computed values can depend on earlier runtime results without Python `eval` or `exec`.

Pure built-in functions are evaluated by `vectis.evaluator` using the same deterministic expression model used by compiler constant folding.

## Assertions

`assert expression;` requires a boolean result. A false assertion fails its node. Statements compiled after an assertion in the same block depend on that assertion and become blocked when it fails.

## Runtime result

`Runtime.execute()` returns a structured `RuntimeResult` containing:

* success/failure,
* dry-run status,
* deterministic execution order,
* node states,
* resolved node values,
* failures.

This result is exposed by the CLI, Mission Control Studio, Launch Control, and standalone HTML execution reports.

## Capability checks

`require` and `request` nodes evaluate their capability expression and compare the resulting name to the runtime's explicit capability set. Unavailable authority fails closed.

A capability grant is not itself an external action. Effects require a configured runtime handler/adapter.

## Handlers and adapters

Handlers are the host integration boundary. Standard adapters provide bounded filesystem, process, and HTTP operations. The runtime does not implicitly spawn a shell, inherit arbitrary process authority, or perform network/filesystem work merely because source text names an action.

## Dry run

Dry run validates runtime scheduling without invoking handlers. It is intended for inspection and planning, not as proof that an external adapter action would succeed in a real environment.

## Scale contract

The regression suite compiles and executes a deterministic chain containing 1,000 computed steps, then verifies graph equality across repeated compilation and the final runtime value. This protects practical large-plan behavior while preserving deterministic ordering.
