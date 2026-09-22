<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# Runtime Design

The runtime executes the typed `ExecutionGraph` produced by the compiler. Raw VECTIS source is never interpreted directly by the runtime.

## Scheduling

`ExecutionGraph.topological_order()` supplies deterministic scheduling. Dependency edges enforce data/guard ordering; true and false edges enforce branch activation.

A node can finish in one of the public runtime states:

* `succeeded`,
* `failed`,
* `blocked`,
* `skipped`,
* `dry-run`.

Failed dependencies block downstream work. Nodes on an inactive conditional branch are skipped.

## Runtime values

Source declarations and `let` declarations produce scalar values. Runtime expression evaluation resolves references from values produced by dependency nodes. This supports expressions such as:

```vectis
let approved score >= 90 && length(name) > 0;
```

without using Python `eval` or `exec`.

The compiler and runtime use the same pure expression evaluator to keep constant folding and runtime evaluation aligned.

## Assertions

`assert expression;` is a deterministic guard. The expression must be boolean. A false assertion fails the assertion node, and later statements in the same block are dependency-gated so they become blocked.

## Capabilities

The runtime receives an explicit capability set. `require` and `request` statements compare their resolved capability name against that set and fail closed when authority is unavailable.

A capability grant is only authorization metadata. External effects require a configured handler/adapter.

## Handlers

Embedding applications may attach handlers for graph-node kinds. Handlers are where host-specific effects belong. VECTIS keeps that boundary explicit so compiler/runtime semantics remain deterministic even when an application integrates external systems.

## Dry run

Dry run schedules the graph and reports dry-run states without invoking effect handlers. It is an inspection mechanism, not a guarantee that external infrastructure would succeed during a real execution.

## Runtime result

The public result includes:

* `success`,
* `dry_run`,
* execution order,
* node states,
* resolved node values,
* failures.

The CLI and VECTIS Studio expose this same contract.
