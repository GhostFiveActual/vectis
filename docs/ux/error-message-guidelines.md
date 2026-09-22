<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# VECTIS Error Message Guidelines

Diagnostics are part of the public language/tooling contract.

## Required fields

Every structured diagnostic contains:

* stable code,
* severity,
* human-readable message,
* canonical source span.

Human-rendered exceptions retain the compatibility shape:

```text
file:line:column: message
```

Machine-readable output includes the code/severity/message and source start/end positions.

## Code families

| Family | Purpose |
| --- | --- |
| `LEXxxx` | lexical/tokenization failures |
| `SYNxxx` | parser/grammar failures |
| `SEMxxx` | semantic/reference/type/function failures |
| `CAPxxx` | capability validation/authorization failures |

Current examples include:

* `LEX001` unterminated string,
* `SYN003` missing required token/delimiter,
* `SEM001` unresolved reference,
* `SEM003` unknown built-in function,
* `SEM005` type mismatch,
* `CAP001` unavailable required capability.

## Writing rules

Messages should be:

1. specific about the violated contract,
2. deterministic for equivalent input,
3. concise enough for CLI output,
4. complete enough to render in Studio without extra internal context,
5. free of implementation details that users cannot act on.

Do not reuse an existing stable code for a different meaning. Distinct error classes receive distinct codes while established meanings remain frozen.
