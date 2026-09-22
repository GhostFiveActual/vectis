<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# RFC 0003: Explicit Actions

Status: Accepted and implemented for VECTIS 0.6.

## Problem

VECTIS can already describe deterministic plans, validate authority requirements, and embed bounded filesystem, process, and HTTP adapters. The language needs a first-class way to invoke external work while keeping effects visible in the execution graph and preventing operation names from silently acquiring authority.

## Syntax

An action binds one result value:

```vectis
action response "http.request" using "http" {
    method: "GET",
    url: endpoint
};
```

The result identifier enters the mission value environment. The operation string identifies the external operation. The capability string states the authority the source expects to consume. The final expression must evaluate to an object containing structured input.

## Semantic model

1. Action input is validated as an ordinary VECTIS expression.
2. The input must be an object or a value whose type cannot be proven before runtime.
3. The action result name follows the same duplicate-declaration rules as source, let, and analyze declarations.
4. The result has unknown static type unless a future typed action schema proves a narrower type.
5. Downstream expressions may depend on the action result.

## Execution graph

Compilation emits one action node with:

1. A stable node identifier equal to the bound result name.
2. Node kind `action`.
3. The operation name.
4. The required capability.
5. The canonical executable input expression.
6. The authored source expression when expansion changes it.
7. Stage metadata.
8. Ordinary dependency edges from every referenced input value.

Action nodes therefore participate in plan fingerprints, graph metrics, branch gating, assertions, timelines, reports, and failure propagation.

## Runtime model

The embedding application supplies an `ActionRegistry`. Each registered operation is permanently associated with one capability and one handler.

Runtime execution requires all of the following:

1. The source names an operation.
2. The source names a capability.
3. The runtime has been granted that capability.
4. The operation is registered.
5. The registered operation is bound to the same capability named by the source.
6. The resolved input is an object.
7. The handler returns a value inside the VECTIS value model.

Any violation fails the action node and blocks dependent work.

## Standard adapter bindings

The action registry can bind the existing bounded adapters:

| Operation | Capability | Behavior |
| --- | --- | --- |
| `filesystem.read_text` | `filesystem` | Read UTF-8 text inside configured roots. |
| `filesystem.write_text` | `filesystem` | Write UTF-8 text inside configured roots. |
| `process.run` | `process` | Run an allowlisted executable with structured arguments and bounded timeout. |
| `http.request` | `http` | Perform a structured bounded HTTP request without implicit redirects or proxy inheritance. |

Constructing and registering an adapter remains an explicit host decision. Source code cannot create adapters, expand their allowlists, inherit environment variables, or register operations.

## Determinism

The execution plan remains deterministic. Action results can depend on external systems and are therefore not claimed to be deterministic unless the registered handler itself is deterministic.

For identical source, VECTIS version, input values, capability grants, registered operation contracts, and handler results, downstream execution remains deterministic.

Dry runs never invoke action handlers.

## Authority

Operation names are not authority tokens. The source must declare the capability, the runtime must grant it, and the action registry must agree that the operation belongs to that capability.

This prevents a source file from relabeling a process or filesystem operation as a weaker capability.

## Failure behavior

Missing capability grants, unavailable operations, capability mismatches, invalid action input, adapter denials, adapter timeouts, transport failures, and invalid result values fail the action node. Dependent nodes become blocked through the existing graph semantics.

## Compatibility

The 0.6 line preserves the action syntax, explicit operation-to-capability binding, fail-closed behavior, result declaration semantics, and action node graph representation.

Future typed action schemas, retries, receipts, or CLI configuration must not introduce ambient authority or silently reinterpret existing action source.

## Alternatives considered

Implicit built-in side-effect functions were rejected because they would blur pure expression evaluation and external authority.

Inferring capability solely from the operation prefix was rejected because authority should be visible in source and independently checked by the runtime registry.

Generic shell actions were rejected because structured allowlisted process execution already provides a safer boundary.

Automatically enabling adapters from installed packages or environment configuration was rejected because it would make authority depend on ambient host state.

## Test strategy

Regression coverage verifies parsing, formatting, semantic input validation, graph dependencies, explicit operation and capability metadata, missing capability denial, missing operation denial, capability mismatch rejection, result propagation, bounded filesystem integration, dry-run behavior, package builds, and the supported Python matrix.
