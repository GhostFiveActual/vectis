<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# RFC 0025: Module Aliases and Qualified Calls

## Status

Accepted and implemented.

## Problem

RFC 0024 gives every loaded pure function a deterministic project-relative identity, but source code still invokes user functions with bare names. When two accessible modules expose the same public function name, a bare call must fail as ambiguous. Selective imports can disambiguate that case, but they also move the imported function into the caller's bare namespace.

Projects need an explicit source form that preserves module identity at the call site. The form must compose with selective imports, private functions, type contracts, compiler expansion, editor navigation, overlays, and the existing import behavior.

## Source syntax

An import may declare one contextual alias after the optional selector list:

```vectis
import "lib/release.vectis" as release;
import "lib/security.vectis" {audit, score} as security;
```

A pure function from an aliased module is invoked with one qualified call:

```vectis
let allowed release.ready(score);
let checked security.audit(record);
```

`as` is contextual import syntax. It is not a globally reserved identifier, so source that declares a function named `as` remains valid outside the import alias position.

## Semantic rules

1. An alias belongs only to the module containing the import declaration.
2. Alias names must be unique among aliased imports in that module.
3. An aliased import contributes no function names to bare-call resolution.
4. A qualified call resolves only against direct public function declarations in the aliased target module.
5. Transitive public functions are not members of an alias namespace.
6. A selective aliased import exposes only the selected direct public functions through that alias.
7. Private functions cannot be selected or invoked through an alias.
8. A qualified call with an unknown alias fails during module resolution.
9. A qualified call naming a missing, private, or unselected function fails before graph generation.
10. Projects that do not use aliases keep the RFC 0023 and RFC 0024 bare-import and selective-import behavior unchanged.
11. A local function and an aliased function may share the same source name because the qualified spelling identifies the imported target explicitly.

## AST and identity

`ImportStatement` carries an optional `alias` string. `CallExpression` carries an optional `qualifier` string. Bare calls have no qualifier.

The qualifier is source syntax rather than semantic identity. Module resolution binds every qualified user call to the `ModuleFunctionId` established by RFC 0024. Semantic analysis and compiler expansion continue to consume that sidecar identity.

A qualified call compiled without module-aware resolution fails closed rather than falling back to a bare user function or built-in function with the same member name.

## Determinism

Alias lookup is local to one importer and depends only on parsed import declarations and the resolved module graph. Qualified member lookup uses one direct target module and one source function name. No search order, filesystem order, or ambient namespace participates in the result.

Duplicate aliases, unknown aliases, inaccessible members, and missing members produce deterministic diagnostics.

## Authority and security

Module aliases add no runtime authority. Imported modules remain restricted to imports and pure function declarations. Existing project-root path containment, extension checks, cycle rejection, private visibility, action capability boundaries, and deterministic compiler expansion remain in force.

Module browser output exposes alias text and project-relative targets only. Absolute local paths are not introduced by this RFC.

## Compiler behavior

Qualified calls are resolved before semantic graph construction. After binding, type validation, recursion detection, result-contract inference, parameter substitution, and function expansion use the bound `ModuleFunctionId` exactly as they do for RFC 0024 calls.

The execution graph does not gain a module-call node type. Pure functions remain compile-time expansion units.

## Editor behavior

Definition, references, rename, and signature help operate on the function member token of a qualified call and follow its `ModuleFunctionId`. Renaming a function changes the declaration and bound call or selector occurrences without changing the module alias.

Semantic tokens classify contextual `as` as a keyword, the declared alias as a variable declaration, and the member in `alias.function(...)` as a function token. The semantic-token legend remains unchanged.

Alias rename and module-path rename are outside this RFC.

## Module browsing

Each import record includes its alias or `null` in addition to its source, resolved target, selector names, and status. The module-browser schema identifier remains stable because this is an additive field.

## Compatibility

Source that does not use aliases keeps its prior parse, resolution, semantic, compiler, runtime, and editor behavior. `as` remains available as an ordinary identifier outside the contextual import position.

Published release artifacts and the package version are unchanged by this language increment.

## Alternatives considered

1. Requiring selective imports for every collision was rejected because it cannot preserve an explicit module namespace at the call site.
2. Treating `alias.function` as ordinary object member access was rejected because module namespaces are compile-time symbols rather than runtime objects.
3. Allowing aliases to expose transitive imports was rejected because it would make a namespace depend on dependency internals rather than the target module's direct public declarations.
4. Reserving `as` globally was rejected because contextual parsing preserves compatibility without reducing determinism.

## Validation strategy

Coverage includes parser and formatter round trips, contextual `as` compatibility, duplicate aliases, namespace-only behavior, qualified collision disambiguation, selective alias restrictions, private visibility, unknown aliases, direct-only namespace boundaries, local and qualified same-name calls, type validation, standalone fail-closed compilation, compiler execution, LSP navigation, references, rename, signature help, semantic tokens, module browsing, existing module regressions, and the complete test suite.
