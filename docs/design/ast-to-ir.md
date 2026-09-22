<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# AST to Execution Graph Compilation

IR-002 defines the deterministic boundary between the validated VECTIS
AST and the canonical execution graph introduced by IR-001.

## Compilation boundary

`compile_program(program)` accepts a canonical `Program`. Semantic
analysis runs before graph generation. If semantic diagnostics are
present, compilation returns a `CompileResult` with no execution graph.
The compiler does not reinterpret or bypass semantic analysis.

A successful result contains the canonical `ExecutionGraph` from
`vectis.ir`. IR-002 does not redefine graph nodes, graph edges,
diagnostics, source spans, or semantic types.

## Deterministic lowering

Compilation is deterministic. The same valid AST produces the same node
identifiers, graph structure, dependency edges, metadata, and serialized
execution graph.

Named declarations retain their declaration names as graph node
identifiers. Statements without a source-level declaration name receive
stable monotonically allocated identifiers such as `publish:0001` and
`condition:0001`.

## Pure function lowering

A `FunctionDeclaration` is a compile-time language unit rather than an execution node.

For each user-function call, arguments are expanded first and then substituted for the function parameters in the returned expression. Nested user-function calls are expanded recursively after semantic analysis has proven that the user-function call graph is acyclic.

The executable graph metadata stores the expanded expression. When the expanded form differs from source, `source_expression` retains the authored call for inspection.

Function expansion happens before dependency discovery. References supplied as call arguments therefore create the same dependency edges that the equivalent manually expanded expression would create.

## Dependency lowering

References inside expressions become explicit dependency edges from the
referenced declaration node to the node that consumes the value.

For example, a declaration equivalent to `source z x + y;` produces
dependency edges from `x` to `z` and from `y` to `z`.

Expression traversal is structural and deterministic. Repeated references
do not create duplicate dependency edges.

## Condition lowering

A `when` statement becomes an explicit condition node. References used by
the condition become normal dependency edges into that node.

The first executable node in the true block is connected through the
canonical true-branch edge. When an `otherwise` block exists, its first
executable node is connected through the canonical false-branch edge.

This preserves conditional control flow in the execution graph rather
than hiding branching behavior inside runtime-specific metadata.

## CompileResult

`CompileResult` is immutable and exposes the generated graph together
with semantic diagnostics. Its `ok` property is true only when a graph
was produced and no semantic diagnostics remain.

`compile_ast_to_execution_graph` is retained as a compatibility helper.
It returns the graph for a valid program and raises `CompilationError`
when semantic validation prevents compilation.

## Invariants

IR-002 preserves these invariants:

* semantic analysis occurs before execution graph construction;
* compiler output uses the canonical IR-001 graph classes;
* dependency direction is producer to consumer;
* condition branches remain explicit;
* graph identifiers are deterministic;
* compilation does not introduce additional diagnostic registries;
* the compiler does not redefine AST, semantic, or IR primitives.
