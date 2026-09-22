<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# VECTIS Threat Model

## Assets

VECTIS protects:

* source integrity,
* deterministic compilation,
* execution-graph integrity,
* explicit capability boundaries,
* adapter allowlists and containment rules,
* diagnostic/source-location integrity,
* local Studio access boundary.

## Trust boundaries

### Source → compiler

Untrusted or malformed VECTIS source must be rejected through lexer, parser, or semantic diagnostics rather than interpreted as Python or shell code.

### Graph → runtime

The immutable execution graph defines scheduling and branch relationships. Runtime expression evaluation consumes only the canonical expression subset and explicit node-value environment.

### Runtime → adapters

Filesystem, process, and HTTP effects are not implicit language privileges. They require explicit adapter construction/configuration and named capability availability.

### Browser → Studio local server

Studio binds to loopback by default. Remote binding requires explicit opt-in. API requests are size-bounded JSON and compiler output is rendered without HTML injection.

## Primary threats and controls

### Dynamic-code injection

Control: no Python `eval`/`exec`; process adapter never enables shell interpolation; Studio JavaScript avoids `eval` or dynamic Function construction.

### Filesystem escape

Control: filesystem paths are canonically resolved and must remain under explicit allowed roots.

### Arbitrary process execution

Control: process executables require explicit absolute-path allowlisting; command arguments are structured sequences; parent environment is not implicitly inherited.

### Network authority expansion

Control: HTTP behavior is isolated behind the explicit HTTP adapter with scheme, credential, redirect, proxy, and timeout restrictions. CLI action profiles additionally require exact hostname allowlists.

### Ambient authority through configuration

Control: action profiles are never discovered automatically. The operator supplies a profile path explicitly, process executable paths must be absolute, filesystem roots remain bounded, process environment values are declared rather than inherited, and unknown profile sections are rejected.

### Branch ambiguity

Control: branch edges are explicit in the graph and every node in a branch is condition-gated.

### Failed invariant ignored

Control: `assert` failures create runtime failures and dependency-block later statements in the same block.

### Studio exposed unintentionally

Control: non-loopback binding is denied unless `--allow-remote` is set.
