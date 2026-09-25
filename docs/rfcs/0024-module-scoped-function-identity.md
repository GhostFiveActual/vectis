<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# RFC 0024: Module-scoped function identity

Status: Implemented

## Problem

VECTIS modules preserve source ownership during loading, visibility checks, selective-import checks, browsing, and editor overlays, but semantic analysis and compilation historically flattened pure functions into one table keyed only by the source function name.

That representation prevents two loaded modules from safely declaring the same function name. It also prevents future module aliases and qualified calls from selecting between colliding declarations without relying on source-name rewriting.

## Contract

Every loaded pure-function declaration receives a deterministic identity composed of its project-relative module path and its source function name.

```text
lib/release.vectis::ready
lib/security.vectis::ready
```

Absolute filesystem paths are not part of this identity.

The source AST remains unchanged. `FunctionDeclaration.name` and `CallExpression.name` continue to represent source syntax. Module resolution carries declaration, call, and selective-import bindings as sidecar metadata through semantic analysis and compilation.

## Resolution

A call inside a module resolves to a declaration in the same module before considering cross-module candidates.

When a module uses selective imports, its cross-module candidates remain limited to selected direct public functions plus the reachable public surface supplied by any bare import in that module.

When a module uses only bare imports, the established reachable public behavior remains compatible. A bare call succeeds only when one public declaration with that source name is resolvable in the loaded program.

If more than one public declaration is a candidate for the same bare call, module resolution fails before execution-graph generation and reports the project-relative candidates.

Private declarations remain callable inside their source module and remain inaccessible from other modules.

## Semantic analysis

Function declaration collection, call validation, type-contract inference, return-contract inference, and recursive-cycle detection use module-scoped identity when module resolution supplies it.

Duplicate names in different modules therefore do not conflict by themselves. Duplicate declarations with the same name inside one module remain invalid.

Diagnostics keep source-level function spelling where that is sufficient. Cycle diagnostics may use project-relative identity when multiple modules participate.

## Compilation

Compile-time pure-function expansion resolves user calls through the module binding metadata. Recursion tracking uses the same identity.

The execution graph, runtime scheduler, capability model, action adapters, and runtime authority contract do not change.

Single-file callers may continue to invoke `compile_program(program)` without module metadata. Module-aware callers pass the resolver scope produced by module or workspace loading.

## Editor behavior

Workspace function occurrences carry module-scoped identity.

Definition, references, and rename operate on that identity rather than matching every occurrence with the same source spelling. Renaming one function does not automatically rename an unrelated same-named declaration in another module.

Signature help resolves the declaration bound to the active call when the call is structurally complete. Existing fallback behavior for incomplete source remains available when one matching declaration is unambiguous.

Module browsing exposes the deterministic project-relative identity for every pure function.

## Determinism and security

Identity depends only on the project-relative module path and function name. Resolver ordering and ambiguity diagnostics are deterministic.

No capability is granted by function identity. No runtime adapter or host authority changes.

Project-relative labels avoid exposing local machine paths through the identity surface.

## Compatibility

Existing single-file programs retain their behavior.

Existing module programs with globally unique function names retain their behavior.

Bare imports, private helpers, selective imports, unsaved overlays, and transitive public access retain their established contracts.

The package version remains `0.8.0`.

## Validation

Validation covers colliding public names, ambiguous bare calls, selective-import disambiguation, local-name precedence, colliding private helpers, bound type contracts, compiler expansion, navigation, references, rename, signature help, module browsing, overlay-aware workspaces, repository policy, public history, privacy boundaries, and the complete unit suite.

## Follow-on

Module aliases and qualified calls can build on this identity without treating source spelling as global symbol identity.
