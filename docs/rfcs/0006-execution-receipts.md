<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# RFC 0006: Execution Receipts and Provenance

## Status

Accepted for implementation.

## Problem

VECTIS can prove the identity and structure of a compiled plan, and it can report runtime state after execution. Those surfaces are useful independently, but automation systems also need a compact record that connects a specific run to the deterministic plan that produced it.

That record must not become an implicit archive of application data, process environments, HTTP payloads, filesystem contents, or other runtime values.

## Receipt model

An execution receipt has four sections.

1. `plan` records the deterministic graph fingerprint, structural summary, and declared authority footprint.
2. `execution` records status, dry run state, execution order, node states, and sanitized failure categories.
3. `provenance` records the VECTIS version, a path safe source label, granted capability names, registered operation names, and an explicit statement that runtime values were omitted.
4. `evidence` records the observation timestamp.

The receipt schema identifier is `vectis.execution-receipt/v1`.

## Determinism boundary

The plan fingerprint remains the deterministic identity of the execution plan.

The evidence timestamp is observation metadata. It is deliberately separated from the plan section and does not alter the graph fingerprint.

Two receipts from the same plan and equivalent runtime outcome may therefore have identical plan and execution sections while carrying different evidence timestamps.

## Data minimization

Receipts do not persist node values.

Receipts do not persist action arguments or action results.

Receipts do not persist process environment values, HTTP bodies, filesystem contents, or action profile secret values.

Runtime failures are reduced to node identity and exception category. Arbitrary exception text is excluded because host exceptions may contain paths, request data, or other sensitive material.

The source field contains only a source basename or `<stdin>`. Local directory paths are not persisted.

## Authority evidence

The plan section records capabilities and actions required by the graph.

The provenance section records granted capability names and registered operation and capability pairs. Adapter configuration remains outside the receipt.

This separates evidence that authority existed from the configuration values that defined its local boundaries.

## CLI behavior

`vectis receipt FILE` executes a mission and emits a receipt as JSON.

`vectis receipt --output RECEIPT.json FILE` persists the receipt to a file.

`vectis run --receipt RECEIPT.json FILE` preserves the existing run JSON output while writing the receipt as a side artifact.

Both commands use the same explicit capability and action profile controls as ordinary execution.

## Failure behavior

Receipt persistence follows ordinary CLI failure rules.

A failed mission can still produce a receipt because failure state is execution evidence.

A receipt file write failure is a CLI error and does not silently discard the requested evidence.

## Compatibility

The language grammar, execution graph format, runtime scheduling, and existing `vectis run` JSON result remain unchanged.

The package version remains 0.8.0 until a release is intentionally prepared.

## Test strategy

1. Prove receipt plan fingerprints match the canonical graph fingerprint.
2. Prove timestamps do not alter plan identity.
3. Prove runtime values and raw failure details are absent.
4. Prove persisted JSON is stable and valid.
5. Prove `vectis receipt` emits the receipt schema.
6. Prove `vectis run --receipt` writes evidence without changing normal run output.
7. Run the complete repository quality gate across every supported Python version.
