<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# VECTIS Process Adapter

## Purpose

`ProcessAdapter` is the explicit VECTIS process capability boundary. It permits controlled execution only for executables named in an explicit allowlist.

## Executable allowlist

Every executable must be explicitly granted when the adapter is constructed. Allowlisted executable paths are canonical absolute paths. Relative executable paths are rejected so process execution does not silently use `PATH` lookup.

An unknown executable alias is denied with `ProcessAccessDenied`, which is a `PermissionError`. The adapter does not broaden its allowlist automatically.

## Structured arguments

Process arguments are supplied as a structured argument sequence. A single command string is rejected. Shell metacharacters remain ordinary argument data rather than executable syntax.

## Shell boundary

Normal execution uses `subprocess.run` with `shell=False`. The adapter does not perform shell interpolation and does not automatically fall back to a shell.

## Results

Standard output and standard error are captured as text. A completed process returns a structured `ProcessResult` containing the executed argument vector, return code, stdout, and stderr. A nonzero return code remains a structured result rather than becoming an implicit shell exception.

## Timeout handling

Every process execution has an explicit timeout. The adapter provides a default timeout and a configured maximum timeout. A per-call timeout above that maximum is rejected.

When execution exceeds its timeout, the adapter raises `ProcessTimeoutError`, which is a `TimeoutError` and retains the command, timeout value, and captured output made available by Python.

## Environment

The parent process environment is not implicitly inherited. Environment variables are available to the child only when they are explicitly configured for the adapter. This prevents ambient host state from silently increasing process authority.

## Capability boundary

The public capability identifier is `process`. Granting this capability does not grant arbitrary shell access, filesystem capability, HTTP capability, or permission to execute programs outside the executable allowlist.

## Security properties

The automated adapter tests verify explicit executable allowlisting, denial of unknown aliases, rejection of relative executable paths, structured arguments, rejection of command strings, no shell interpolation, deterministic stdout and stderr capture, structured nonzero exits, repeatable execution, parent-environment isolation, explicit environment access, timeout enforcement, maximum-timeout validation, timeout error typing, and process denial error typing.

## Architectural boundary

The process adapter performs controlled process execution only. Filesystem effects remain the responsibility of the filesystem adapter. HTTP access belongs to the separate HTTP adapter.

The adapter must deny any executable that is not present in the explicit allowlist.
