<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# VECTIS Security Review

This review covers the public VECTIS language/compiler/runtime, packaged Studio, and filesystem/process/HTTP capability adapters.

## Verified architectural properties

* Runtime language evaluation does not use Python `eval` or `exec`.
* Process execution does not use `shell=True`.
* String command arguments are rejected by the process adapter.
* Parent environment variables are not inherited implicitly by the process adapter.
* Filesystem paths are constrained to canonical allowed roots.
* HTTP requests remain behind an explicit adapter boundary.
* Unavailable capabilities are denied.
* Execution graph node kinds remain a closed enum.
* Graphs reject cycles and unknown edge endpoints.
* Studio has no external CDN dependency.
* Studio JavaScript avoids dynamic code execution and HTML injection for result rendering.
* Studio defaults to loopback-only binding.

## Expression and assertion security properties

The deterministic expression evaluator supports pure scalar operations and a closed built-in registry. Unknown function names and invalid arity are rejected during semantic analysis.

Assertions fail closed at runtime and gate subsequent nodes in their block.

Evaluator semantics, capabilities, adapter authority, Studio binding behavior, and process, filesystem, or network boundaries require regression coverage before release.
