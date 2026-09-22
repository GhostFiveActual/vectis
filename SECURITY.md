<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->
# VECTIS Security Policy

VECTIS treats external authority as an explicit capability boundary.

## Supported release

Security fixes are maintained against the current 0.1.x release line.

## Reporting a vulnerability

Do not publish credentials, exploit details, or sensitive deployment information in a public issue.

Use GitHub private vulnerability reporting when it is available for the repository. If that channel is unavailable, contact the repository owner through a private GitHub communication channel before disclosing technical details publicly.

## Security invariants

Contributions preserve these principles:

* no implicit shell execution,
* no dynamic `eval` or `exec` runtime path,
* no implicit inheritance of the parent process environment,
* explicit executable allowlists for process adapters,
* explicit filesystem containment,
* explicit HTTP scheme and timeout constraints,
* unavailable capability is denied,
* semantic validation occurs before execution,
* execution graphs remain deterministic and acyclic.

Security regressions include a test that fails without the fix.
