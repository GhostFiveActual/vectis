<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# Language Standard

## Core rules

1. Parse source into typed structures before execution.
2. Preserve source locations through diagnostics.
3. Perform semantic validation before runtime work.
4. Lower valid source into an inspectable intermediate representation.
5. Keep runtime scheduling deterministic.
6. Keep external effects behind explicit adapters or capabilities.
7. Avoid host language dynamic execution and implicit shell execution.
8. Make formatting deterministic.
9. Keep diagnostics stable enough for tools and users.
10. Treat examples as executable contracts and test them.
11. Keep reusable language units finite, explicit, and inspectable.
12. Reject recursive or ambient-state behavior unless a future RFC defines a deterministic contract for it.

## Syntax discipline

Syntax changes require a grammar definition, parser coverage, semantic behavior, formatter behavior, runtime behavior when applicable, examples, tests, compatibility analysis, and RFC review when the change affects a durable language contract.

## Pure function discipline

User-defined pure functions use explicit parameters and one returned expression. Their bodies cannot capture mission state or contain authority-bearing statements. User-function call graphs remain acyclic, and compilation expands calls into ordinary VECTIS expressions before graph execution.

## Runtime discipline

The runtime owns scheduling and value resolution. Adapters own external effects. Source text does not gain host authority merely by naming an operation.
