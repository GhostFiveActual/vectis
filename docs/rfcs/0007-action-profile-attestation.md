<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# RFC 0007: Action Profile Shape Attestation

## Status

Accepted for implementation.

## Problem

Execution receipts can prove which deterministic plan ran and which capability and operation names were available. They do not identify the effective shape of an explicitly selected action profile.

Persisting the full profile in a receipt would expose local paths, host policy, timeout policy, process environment values, or other deployment details. Hashing secret values directly would also create avoidable disclosure risk when low entropy values can be guessed.

VECTIS therefore needs a narrower attestation contract.

## Attestation scope

The attestation fingerprint covers the effective non-secret authority shape of one resolved action profile.

The canonical descriptor contains:

1. Capability names.
2. Registered operation and capability pairs.
3. Filesystem root boundaries.
4. Process executable aliases.
5. Process environment key names.
6. Process timeout bounds.
7. HTTP hostname boundaries.
8. HTTP timeout bounds.

The descriptor excludes process environment values and process executable target paths.

The source path is also excluded from the fingerprint.

## Canonical fingerprint

The descriptor is serialized as canonical UTF-8 JSON with sorted keys and compact separators.

The fingerprint is SHA-256 over those bytes and is represented as 64 lowercase hexadecimal characters.

Equivalent resolved authority shapes therefore produce the same fingerprint.

A change to an attested authority boundary changes the fingerprint.

## Secret-value boundary

The attestation explicitly records `secret_values_attested: false`.

Two profiles that differ only in process environment values may therefore have the same authority-shape fingerprint.

This is intentional. The fingerprint must not be interpreted as proof of secret values or as a signature from an external trust anchor.

## Receipt integration

When execution uses an explicit action profile, the receipt provenance section records:

1. Attestation schema.
2. SHA-256 algorithm identifier.
3. Authority-shape scope.
4. Profile fingerprint.
5. Profile source basename.
6. `secret_values_attested: false`.

The receipt does not persist the canonical descriptor.

This allows a deployment to compare a receipt against an independently inspected profile without exposing the profile boundaries in the receipt itself.

## CLI inspection

`vectis actions --config FILE` exposes the attestation metadata beside the existing profile inspection data.

This gives operators a direct way to obtain the fingerprint for comparison with execution receipts.

## Determinism

Fingerprint construction performs no I/O after the profile has been resolved.

Canonical ordering removes differences caused only by dictionary or set ordering.

The fingerprint describes effective authority shape, not source-file byte identity.

## Compatibility

The language grammar, execution graph, runtime scheduling, action profile TOML syntax, and package version remain unchanged.

Receipts without an action profile remain valid and do not contain profile attestation metadata.

## Security interpretation

The SHA-256 fingerprint provides content identity for the non-secret authority shape.

It does not authenticate who created the profile.

A deployment that requires signer identity or tamper evidence anchored outside the local system can layer a signed attestation over this fingerprint.

## Test strategy

1. Prove repeated profile resolution yields the same fingerprint.
2. Prove secret environment value changes do not change the fingerprint.
3. Prove attested authority boundary changes do change the fingerprint.
4. Prove receipt metadata contains only the safe attestation surface.
5. Prove CLI profile inspection exposes the same fingerprint.
6. Run the complete repository quality gate across every supported Python version.
