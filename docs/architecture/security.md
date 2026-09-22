<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# Security Architecture

VECTIS security is based on deterministic interpretation, explicit runtime authority, and bounded adapters. VECTIS does **not** currently implement user authentication, MFA, RBAC, encryption-at-rest, or a key-management service; those concerns belong to applications that embed or expose VECTIS.

## Security boundaries

### Source boundary

VECTIS source is tokenized, parsed, semantically analyzed, and compiled. It is not passed to Python `eval`, Python `exec`, or a shell.

### Capability boundary

Named capabilities represent explicit runtime authority. If a mission requires an unavailable capability, runtime execution fails rather than inferring or acquiring permission.

Capability diagnostics use the `CAPxxx` family:

* `CAP001` : required capability unavailable,
* `CAP002` : invalid capability value.

### Action registry boundary

Action source names an operation and a capability, but neither string grants authority. Runtime action execution requires an explicit capability grant plus an explicitly registered operation bound to the same capability. Missing grants, missing operations, and capability mismatches fail closed.

Action handlers receive resolved structured input and must return values inside the VECTIS value model. Dry runs do not invoke action handlers.

### CLI action profile boundary

The CLI does not discover action authority from project files, environment variables, or user directories. An operator must pass `--actions-config FILE` to an execution command.

Filesystem roots resolve from the selected profile location and remain subject to canonical path confinement. Process executable entries must be absolute and continue through the structured process adapter without shell interpolation or parent-environment inheritance. CLI HTTP profiles require a hostname allowlist in addition to the existing scheme, credential, redirect, proxy, and timeout controls.

`vectis actions --config FILE` exposes operation names, capability names, roots, executable aliases, environment key names, host allowlists, and timeout bounds. It does not display configured process environment values.

### Filesystem adapter

Filesystem access is restricted to explicitly configured roots. Canonical path resolution rejects parent traversal, string-prefix collisions, and symlink escapes outside those roots.

### Process adapter

Process execution requires an explicit executable allowlist and structured argument sequence. Relative executable allowlist entries are rejected, string commands are rejected, `shell=True` is not used, and the parent process environment is not implicitly inherited.

### HTTP adapter

HTTP requests are isolated behind the HTTP adapter. The adapter validates HTTP/HTTPS schemes, enforces timeout limits, and does not automatically follow redirects.

### Studio boundary

VECTIS Studio binds to loopback by default. Non-loopback binding requires explicit `--allow-remote`. API bodies are size-bounded. The browser client renders compiler/runtime output without `eval`, dynamic Function construction, or unsafe HTML-string injection.

## Runtime failure behavior

* semantic errors prevent graph generation,
* graph cycles are rejected,
* failed dependencies block downstream nodes,
* inactive branches are skipped,
* false assertions fail and block dependent statements,
* unavailable capabilities fail closed.

## Non-goals for 0.7

VECTIS 0.7 is not a general sandbox for hostile native code and does not claim to provide operating-system isolation. Applications that expose VECTIS to untrusted users should still apply process/container isolation, authentication, authorization, resource limits, and network policy at the host/application layer.

See [Threat Model](threat-model.md) for concrete threats and controls.
