<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# VECTIS Language Vision

## Mission

VECTIS exists to make automation inspectable before execution.

A VECTIS program should answer four questions clearly:

1. What values and conditions exist?
2. What operations depend on them?
3. What authority is required?
4. What will execute when a condition changes the path?

## Direction

VECTIS is not trying to replace a general purpose programming language.

It is a focused automation language with a deterministic compiler and runtime boundary.

The language should grow where additional syntax improves automation clarity. It should not grow merely to reproduce host language features.

## Design rules

1. Keep syntax small and documented.
2. Preserve typed structure from source through execution.
3. Reject invalid meaning before runtime work.
4. Keep the execution graph inspectable.
5. Keep pure computation separate from external effects.
6. Make authority explicit.
7. Make tooling part of the language product.
8. Test examples as contracts.
9. Keep formatting deterministic.
10. Preserve published compatibility intentionally.

## Product rule

A language is not usable because it parses. A usable language needs formatting, validation, execution, diagnostics, project workflow, examples, inspection, packaging, and a clear application path.

VECTIS 0.1 establishes that baseline for VECTIS.
