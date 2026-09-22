<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# RFC 0004: Explicit CLI Action Profiles

Status: Accepted and implemented for VECTIS 0.7.

## Problem

First-class actions make external work visible in VECTIS source and execution graphs, but command-line users need a safe way to bind those operations to local adapters without writing an embedding application.

Configuration must not silently acquire machine authority, search the environment, inherit unrestricted process state, or turn project metadata into an implicit permission grant.

## Profile selection

Execution commands accept an explicit profile path:

```bash
vectis run --actions-config actions.toml mission.vectis
vectis mission --actions-config actions.toml mission.vectis
vectis timeline --actions-config actions.toml mission.vectis
vectis report --actions-config actions.toml mission.vectis
```

No action profile is discovered automatically. A file named `actions.toml` has no effect unless the operator selects it.

## Profile format

```toml
[actions.filesystem]
roots = ["./workspace"]

[actions.process]
default_timeout = 30
max_timeout = 120

[actions.process.executables]
python = "/usr/bin/python3"

[actions.process.environment]
LANG = "C.UTF-8"

[actions.http]
allowed_hosts = ["api.example.com"]
default_timeout = 10
max_timeout = 30
```

Relative filesystem roots resolve from the profile directory. Process executable paths must be absolute. HTTP profiles require a non-empty hostname allowlist.

## Authority model

Selecting a configured adapter grants only that adapter's named capability for that invocation. The VECTIS action source must still name the same capability and the action registry must still bind the operation to that capability.

Manual `--capability` grants remain available and are combined with capabilities explicitly configured by the selected profile.

The profile cannot define arbitrary Python handlers, import code, execute setup commands, interpolate environment variables, or register unknown adapter types.

## Filesystem

The filesystem section requires one or more roots. The existing canonical root confinement remains authoritative, including traversal and symlink escape checks.

## Process

The process section requires an executable table. Executable values must be absolute paths and continue through the existing allowlisted process adapter.

The parent environment is not inherited. Only key/value pairs written in the profile are supplied to child processes.

## HTTP

The HTTP section requires explicit hostnames. URL schemes remain limited to HTTP and HTTPS, embedded credentials remain denied, proxy inheritance remains disabled, redirects remain disabled, and request timeouts remain bounded.

Host matching is exact after lowercase normalization and removal of a trailing dot. Profile entries are hostnames only, not URLs or host-and-port strings.

## Inspection

```bash
vectis actions
vectis actions --config actions.toml
```

The first command describes standard action contracts without granting them. The second validates the selected profile and shows capabilities, operations, roots, executable aliases, environment key names, host allowlists, and timeout bounds.

Environment values are not included in the inspection manifest.

## Plan audit

Action nodes contribute their capabilities to the required authority footprint reported by `vectis audit`. The audit also identifies each action node, operation, and capability without executing the plan.

## Project scaffolding

`vectis init` writes `actions.example.toml` as an inert example. It is never loaded automatically.

## Compatibility

The 0.7 patch line preserves explicit profile selection, exact action-to-capability checks, relative filesystem-root resolution, absolute process executable requirements, required HTTP host allowlists, and the absence of ambient profile discovery.

## Alternatives considered

Automatically loading `vectis.toml` was rejected because project metadata should not become an authority grant.

Environment-variable configuration was rejected as a default because it makes authority depend on ambient process state.

Executable lookup through `PATH` was rejected because process authority must identify explicit executable files.

Unrestricted HTTP configuration was rejected for the CLI because a reusable local profile should state its network destinations.

## Test strategy

Regression coverage verifies profile parsing, unknown-key rejection, bounded path resolution, absolute executable enforcement, HTTP hostname allowlists, redacted inspection output, standard action discovery, CLI action execution, missing-profile failure, action-aware plan auditing, project scaffolding, package builds, and the supported Python matrix.
