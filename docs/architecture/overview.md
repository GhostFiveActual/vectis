<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# VECTIS Architecture Overview

VECTIS is a deterministic language toolchain for inspectable automation. It does not translate source into native machine code and it does not contain an optimizer/code-generation stage. Valid source becomes a typed execution graph that the VECTIS runtime schedules directly.

## System pipeline

```text
VECTIS source
    ↓
Lexer
    ↓
Parser
    ↓
AST
    ↓
Semantic analyzer
    ↓
Execution graph (IR)
    ↓
Deterministic runtime
    ↓
Optional explicit capability adapters / handlers
```

## Lexer

`vectis.lexer` converts characters into typed tokens while preserving file, line, and column information. Unsupported characters and malformed strings fail with structured `LEXxxx` diagnostics.

## Parser

`vectis.parser` converts tokens into immutable AST nodes. Parsing has no external side effects and does not execute VECTIS expressions.

## AST and expressions

The AST represents declarations, statements, branches, assertions, references, literals, unary/binary expressions, and deterministic built-in function calls. `let` declarations represent computed values without adding imperative mutation.

## Semantic analysis

`vectis.semantic` validates declarations, references, selected expression types, built-in existence/arity, boolean conditions, assertions, and confidence values before graph generation. Semantic failures use `SEMxxx` diagnostics.

## Execution graph

`vectis.ir.ExecutionGraph` is the runtime boundary. Graph nodes represent operations and values; edges represent dependencies and true/false branch control. The graph rejects cycles and serializes deterministically.

## Runtime

`vectis.runtime.Runtime` executes nodes in deterministic topological order. Expressions are evaluated from canonical metadata plus values produced by dependency nodes. Runtime state is explicit: succeeded, failed, skipped, or blocked.

## Capabilities and adapters

Capabilities are named runtime authority, not ambient permission. `require` and `request` nodes check an explicit capability set. Filesystem, process, and HTTP adapters impose their own containment, allowlist, scheme, and timeout boundaries.

## VECTIS Studio

`vectis studio` runs a local-first browser application backed by the same lexer/parser/semantic/compiler/runtime modules as the CLI. Studio is an interface to the canonical toolchain, not a second implementation of the language.

## Design priorities

1. **Determinism** : stable parsing, graph generation, serialization, and scheduling.
2. **Inspectability** : users can inspect tokens, AST, graph, diagnostics, runtime states, and values.
3. **Explicit authority** : language syntax alone does not grant external effects.
4. **Small semantic surface** : built-ins are pure; external effects are kept at adapter boundaries.
5. **Fail closed** : malformed source, unavailable capabilities, failed assertions, and invalid graph structures stop or block execution rather than being inferred away.
