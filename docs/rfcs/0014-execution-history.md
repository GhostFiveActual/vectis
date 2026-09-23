<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# RFC 0014: Execution History

## Summary

VECTIS can project explicitly persisted execution receipts into a deterministic, value-free execution history for command-line and editor inspection.

## Problem

Execution receipts prove one run at a time, but operators need to review prior outcomes without manually opening every receipt. A history surface must preserve the receipt security model instead of becoming a second store for runtime values, failure details, local paths, or authority secrets.

## History contract

`vectis.history` reads JSON files from one explicit directory and accepts only `vectis.execution-receipt/v1` records that retain `runtime_values_recorded = false`.

History is non-recursive. Receipt symlinks are rejected. Malformed JSON, unsupported schemas, unsafe provenance claims, and structurally invalid receipts are reported as rejected receipt filenames without returning their contents.

Valid entries are sorted by canonical `recorded_at` text and receipt filename, newest first. Callers may bound the result count from 1 through 1000.

## Projected fields

History returns only an allowlisted projection:

1. Receipt filename and recorded timestamp.
2. Safe source label.
3. Plan fingerprint and numeric structural summary.
4. Execution status, success flag, and dry-run flag.
5. Counts of node states.
6. Failure categories without failure details or node values.
7. Granted capability names.
8. Action profile fingerprint when a safe attestation is present.

Raw receipt JSON is never returned by the history API.

## CLI

`vectis history DIRECTORY` reads an explicitly selected receipt directory and emits the deterministic history document as JSON.

`--limit N` bounds returned valid entries and defaults to 50. The command performs no mission execution and creates no files.

## Editor integration

The language server advertises `vectis.history.inspect` through `workspace/executeCommand`.

The command requires a file-backed document URI and a relative history directory. The directory is resolved inside that document's VECTIS project root. Absolute paths and paths that escape the project root are rejected.

The editor command is read-only and uses the same allowlisted history projection as the CLI.

## Determinism

The projection depends only on explicit receipt files, canonical receipt fields, filename ordering, and the requested limit. Directory traversal is non-recursive and stable.

History does not reinterpret execution semantics or derive hidden runtime state.

## Authority and security

Normal `vectis run`, `vectis mission`, and editor operations do not begin recording history automatically. A receipt must already exist because the user explicitly requested receipt persistence.

History performs no execution, action registration, capability grant, network operation, or source mutation. Runtime values, failure details, environment values, absolute receipt paths, and arbitrary JSON fields are excluded from the projected response.

## Compatibility

Receipt schema `vectis.execution-receipt/v1` remains unchanged. Runtime scheduling, source syntax, compiler IR, action profiles, capability semantics, package version, and published releases do not change.

Existing receipt files remain valid inputs when they satisfy the receipt contract.

## Test strategy

Tests cover deterministic ordering, result limits, value exclusion, invalid receipt rejection, unsafe provenance rejection, CLI projection, project-bounded editor access, command advertisement, and the complete repository suite.
