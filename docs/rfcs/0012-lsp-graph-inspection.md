<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# RFC 0012: LSP Execution Graph Inspection

## Summary

This RFC exposes deterministic execution graph inspection through the Language Server Protocol. Editor clients invoke `workspace/executeCommand` with `vectis.graph.inspect` and receive a read-only structural view of the plan compiled from the current source workspace.

The inspection surface reuses the canonical parser, module overlay resolver, semantic analyzer, compiler, execution graph, graph summary, stage manifest, and capability manifest. It does not define a parallel planning model.

## Problem

VECTIS editors can report diagnostics, navigate symbols, format source, show signatures, and classify semantic tokens. They cannot inspect the compiled dependency graph without leaving the editor or building a separate integration around command-line output.

Mission Control needs a stable way to understand graph shape, stage organization, authority requirements, typed edges, dependencies, and successors while source is still being edited.

## Protocol contract

The language server advertises an `executeCommandProvider` containing `vectis.graph.inspect`.

A client sends `workspace/executeCommand` with one argument object containing a `uri` string. The server resolves that document through the same open-buffer overlay workspace used by diagnostics and navigation.

A successful response has `ok` set to `true` and an `inspection` object. A source or compilation failure has `ok` set to `false` and carries normal VECTIS diagnostics translated into the existing LSP diagnostic shape.

Unsupported commands and malformed command arguments are rejected as invalid request parameters.

## Inspection payload

The inspection object contains:

1. A payload version and canonical plan fingerprint.
2. Existing structural summary metrics and deterministic topological order.
3. Existing stage and capability manifests.
4. One structural record per graph node in deterministic topological order.
5. Each node record contains its identifier, kind, label, stage, metadata, dependency identifiers, successor identifiers, and typed incoming and outgoing edges.

Graph node values and runtime state are intentionally omitted. The command describes plan structure rather than execution results.

## Overlay and compilation behavior

For file-backed documents, open editor buffers replace saved file content before module resolution. When the selected document participates in an open importing workspace, inspection uses the widest reachable open workspace, matching navigation behavior.

For non-file documents already open in the language server, the current document text is parsed and compiled directly.

The command never substitutes stale saved source for an open editor buffer.

## Determinism

For identical source text, overlays, installed VECTIS version, and project files, the inspection payload is deterministic. Node order follows the canonical graph topological order. Stage, capability, fingerprint, dependency, successor, and edge information comes from existing graph contracts.

## Authority and security

Graph inspection is read-only. It performs no runtime execution, action dispatch, process launch, network request, capability grant, environment lookup, source mutation, or file write.

The payload may include structural metadata already present in the compiled plan. Runtime node values are excluded.

## Compatibility

This is an additive editor capability. The grammar, typed AST, semantic rules, execution graph format, compiler lowering, runtime scheduling, authority model, module rules, CLI behavior, and package version remain unchanged.

## Test strategy

1. Verify deterministic inspection for identical graphs.
2. Verify node values and runtime state are absent.
3. Verify dependency, successor, and typed branch-edge structure.
4. Verify stage and capability manifests.
5. Verify `initialize` advertises the command.
6. Verify the server compiles unsaved document content instead of stale disk content.
7. Verify invalid source returns structured diagnostics without execution.
8. Verify malformed and unsupported commands fail closed.
9. Run the complete unit, repository-policy, public-history, and live LSP smoke gates before publication.
