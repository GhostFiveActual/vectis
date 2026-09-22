<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# VECTIS Filesystem Adapter

## Purpose

`FileSystemAdapter` provides the explicit `filesystem` capability for controlled text-file access. It performs read and write operations only within one or more explicitly configured root paths.

## Root allowlist

The constructor accepts a single root path or an iterable of roots. Each root is expanded and canonically resolved with `pathlib.Path.resolve(strict=False)`. Duplicate canonical roots are collapsed while preserving declaration order. An empty root allowlist is rejected.

Relative paths are anchored beneath the first configured root. Absolute paths may be used only when their canonical location is within one of the configured roots.

## Path containment and denial

Every requested path is passed through `resolve_path()` before access. Containment uses `Path.relative_to()` rather than string-prefix matching, so a path such as `/allowed-evil/file.txt` is not accepted merely because `/allowed` is an allowed root.

Parent traversal such as `../outside.txt`, direct absolute paths outside the allowlist, and symbolic-link escapes are denied. A denied path raises `FileSystemAccessDenied`, which is a `PermissionError`.

This validation is a capability boundary for VECTIS filesystem access. It is not a general operating-system sandbox and does not claim protection against a concurrent filesystem mutation between validation and the final operation.

## Read operations

`read(path)` resolves and validates the path, then returns text using UTF-8 by default. `read_text(path)` is an equivalent compatibility spelling. A caller may provide another text encoding.

## Write operations

`write(path, content)` resolves and validates the path before writing text with UTF-8 by default. `write_text(path, content)` is an equivalent compatibility spelling. Write content must be `str`; non-text content is rejected. Missing parent directories are not created implicitly.

## Multiple roots

When multiple roots are explicitly granted, an absolute path may resolve beneath any of them. Relative paths continue to use the first root as the deterministic default.

## Tested security properties

The automated adapter tests cover canonical roots, duplicate-root normalization, multiple roots, relative and absolute allowed access, parent traversal denial, string-prefix collision denial, absolute escape denial, symbolic-link escape denial, text read and write operations, invalid path types, non-text write rejection, and the public filesystem capability name.

## Architectural boundary

The filesystem adapter performs filesystem effects only. It does not execute processes, make HTTP requests, interpret VECTIS source, modify compiler semantics, or broaden its own capability grant. Process execution and HTTP access belong to later dedicated adapters.

The adapter must deny any resolved path that falls outside the explicit root allowlist.
