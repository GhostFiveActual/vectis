<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# VECTIS Execution Graph IR

The VECTIS intermediate representation is a typed execution graph positioned
between semantic analysis and runtime execution. The parser determines syntax,
the semantic analyzer determines whether the program is valid, and the IR
records the valid program as explicit nodes and edges without executing it.

## Graph nodes

`GraphNode` represents one executable or structural operation. Every node has a
stable non-empty identifier and a typed `NodeKind`. The initial kinds correspond
to the language surface: mission, source, analyze, require, request, publish,
citations, confidence, and condition.

A node may carry a human-readable label, one JSON-scalar value, and deterministic
scalar metadata. Metadata keys are unique so serialization cannot silently
discard conflicting values.

## Graph edges

`GraphEdge` represents an explicit relationship between two nodes. A dependency
edge means the target depends on the source. Conditional control flow uses
`true` and `false` edge kinds rather than hiding branch behavior in runtime
implementation details.

Every edge endpoint must refer to a node in the same graph. Duplicate edges are
rejected.

## ExecutionGraph invariants

`ExecutionGraph` owns immutable tuples of nodes and edges. Construction enforces
the following invariant set:

* node identifiers are unique;
* every edge source and target exists;
* duplicate typed edges are rejected;
* the graph is acyclic;
* topological ordering is deterministic.

The graph therefore represents a DAG suitable for later runtime scheduling.

## Dependency ordering

`topological_order()` computes a deterministic execution order. When several
nodes are simultaneously ready, their original graph declaration order is used
as the stable tie breaker.

`dependencies_of()` exposes direct dependency edges. `successors_of()` exposes
all direct outgoing control or dependency relationships.

## Conditional execution

Conditional behavior is represented structurally. A condition node may emit
`TRUE_BRANCH` and `FALSE_BRANCH` edges. The runtime can therefore decide which
branch becomes active without changing the meaning of the graph.

IR-001 does not evaluate conditions. Evaluation belongs to the runtime layer.

## Serialization

Execution graphs have a versioned machine-readable serialization contract.
`to_dict()` and `to_json()` produce version `1`. `from_dict()` and `from_json()`
reconstruct the typed graph and re-run all graph invariants.

JSON output uses stable key ordering and compact separators so identical graphs
produce deterministic serialized text.

Serialization contains structure and scalar data only. It does not serialize
Python objects, executable code, adapters, credentials, or runtime state.

## Architectural boundary

The execution graph is deterministic data. It does not perform semantic
analysis, invoke capabilities, execute processes, access files, make network
requests, or call an LLM.

IR-002 is responsible for lowering the validated AST into this graph. Runtime
tasks consume the resulting graph after compilation.
