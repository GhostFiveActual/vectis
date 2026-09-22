<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# Capability Model

VECTIS uses named capabilities to make runtime authority explicit.

## Principle

Language syntax does not grant ambient host permission. A mission may declare a requirement or request:

```vectis
require "filesystem";
request "http";
```

The runtime checks those names against the capability set supplied by the embedding application.

## Standard capability names

The 0.1 product defines three standard adapter boundaries:

* `filesystem`,
* `process`,
* `http`.

`vectis capabilities` prints the machine-readable registry.

## Capability objects

`vectis.capabilities.Capability` describes a named unit of authority. `CapabilityRegistry` stores explicitly declared capability definitions and preserves the `CapabilityModel` alias for v0.0.x API compatibility.

Capability objects do not perform I/O.

## Failure behavior

Capability validation uses dedicated diagnostics:

* `CAP001` : required capability unavailable,
* `CAP002` : invalid capability value.

`CapabilityDenied` is a subclass of `CapabilityError`, which is a structured `DiagnosticError`.

Runtime `require`/`request` nodes also fail closed when their resolved capability name is not present in the explicit runtime capability set.

## Adapter boundary

Possessing a capability name is not equivalent to unrestricted host access. The adapter still enforces its own concrete policy:

* filesystem roots are contained,
* process executables are allowlisted and arguments are structured,
* HTTP schemes and timeouts are bounded.

Applications embedding VECTIS should grant only the capabilities and adapter configuration required for the mission.
