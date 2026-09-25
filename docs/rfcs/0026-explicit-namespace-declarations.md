<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# RFC 0026: Explicit Namespace Declarations

## Status

Accepted and implemented.

## Problem

RFC 0025 lets each importer choose a local module alias. That solves call-site ambiguity, but the qualifier is owned by the importer rather than the library. A shared library cannot publish one canonical qualified spelling that callers may use consistently across a project.

VECTIS needs an explicit module declaration that can publish a stable logical namespace while preserving project-relative `ModuleFunctionId` identity, existing bare import behavior, selective imports, private visibility, explicit aliases, deterministic compilation, and editor tooling.

## Source syntax

A module may declare one contextual namespace as its first source statement:

```vectis
namespace release;

function ready(value: number): boolean {
    return value >= 90;
}
```

An unaliased importer may use that declared namespace:

```vectis
import "lib/release.vectis";

let allowed release.ready(score);
```

The existing bare import surface remains available, so the same import may also use `ready(score)` according to the RFC 0023 and RFC 0024 rules.

`namespace` is contextual declaration syntax. It is not a globally reserved identifier, so a pure function named `namespace` remains valid outside the declaration position.

## Semantic rules

1. A source module may contain at most one namespace declaration.
2. When present, the namespace declaration must be the first parsed statement in that module. Leading comments and whitespace do not affect this rule because they are not statements.
3. A namespace declaration is compile-time module metadata and does not create a runtime value.
4. An unaliased direct import of a namespaced module exposes the declared namespace as a qualified call surface.
5. The same unaliased import keeps its established bare-call behavior.
6. A selective unaliased import restricts both its bare selected functions and its declared namespace to the selected direct public functions.
7. A declared namespace exposes only direct public function declarations from its module. It does not expose transitive imports.
8. Private functions cannot be invoked through a declared namespace.
9. A declared namespace does not propagate through another module. Only a direct import can expose that namespace to the importer.
10. An explicit RFC 0025 alias suppresses the target module's declared namespace for that import. The explicit alias is the only qualified spelling contributed by that import.
11. Qualified spellings contributed by aliases and declared namespaces must be unique inside one importing module. A collision fails during module resolution.
12. A namespace declaration does not create a self qualifier inside its declaring module. Local functions continue to use local bare resolution.
13. Namespace names cannot use the contextual boolean literal spellings `true` or `false`.
14. A namespace declaration may appear in an entry source as metadata, but it has no local qualification effect unless another module imports that source as a valid library.

## AST and identity

`NamespaceDeclaration` is a top-level statement carrying one namespace name. It has no executable representation.

Qualified calls continue to use `CallExpression.qualifier` from RFC 0025. Module resolution maps a declared namespace qualifier to the directly imported target module and then binds the selected function to the existing project-relative `ModuleFunctionId`.

The namespace text is not part of semantic function identity. For example, a call written as `release.ready()` may still bind to `lib/release.vectis::ready`. Moving or renaming source paths therefore remains an explicit identity-affecting operation, while changing a declared namespace changes source qualification only.

## Determinism

Namespace discovery depends only on the parsed source modules in the bounded project graph. A qualifier resolves through one direct import and one direct target declaration. Filesystem enumeration order, ambient state, and runtime values do not participate.

Duplicate namespace declarations, misplaced declarations, qualifier collisions, unknown qualifiers, inaccessible private members, and unselected members produce deterministic diagnostics before graph generation.

## Authority and security

Namespace declarations add no runtime authority. Imported modules remain restricted to imports, one optional namespace declaration, and pure function declarations. Existing project-root containment, extension checks, cycle rejection, visibility rules, action capabilities, and compiler expansion remain unchanged.

Namespace text is source metadata. Module browser output exposes only the declared namespace and project-relative source information, never absolute project paths.

## Compiler behavior

Top-level namespace declarations are semantic and compiler no-ops after module resolution. They create no execution node, edge, runtime value, or capability.

Qualified calls through declared namespaces use the same function identity sidecar as aliases. Type validation, cycle detection, contract inference, parameter substitution, and compile-time function expansion therefore continue to use `ModuleFunctionId`.

A nested namespace declaration is rejected semantically because namespace metadata is module-scoped rather than block-scoped.

## Editor behavior

Definition, references, rename, and signature help on a namespace-qualified function member follow the bound `ModuleFunctionId`. Function rename changes the declaration and bound member occurrences without changing the namespace declaration.

Semantic tokens classify contextual `namespace` as a keyword and its declared namespace name as a variable declaration. Qualified function members retain the function token classification. The semantic-token legend remains unchanged.

Namespace rename and namespace-definition navigation are outside this RFC.

## Module browsing

Each module record includes a `namespace` field containing the declared namespace or `null`. A namespace declaration does not increase executable statement count and does not prevent an otherwise valid pure-function module from being importable.

Misplaced or duplicate namespace declarations make that module invalid in the browser with project-relative diagnostics.

## Compatibility

Modules without namespace declarations keep their prior parser, resolver, compiler, runtime, and editor behavior. Unaliased imports of a namespaced module keep their established bare-call surface in addition to the declared qualified surface.

Explicit RFC 0025 aliases retain their namespace-only behavior and override the target's declared namespace locally. Published release artifacts and package version remain unchanged by this language increment.

## Alternatives considered

1. Replacing bare imports with declared namespaces was rejected because it would break established source behavior.
2. Making the declared namespace part of `ModuleFunctionId` was rejected because RFC 0024 deliberately defines durable function identity with the project-relative module path and function name.
3. Propagating namespaces transitively was rejected because it would expose dependency internals through unrelated importers.
4. Exposing both an explicit alias and the declared namespace from one import was rejected because one import should contribute one qualified spelling when the caller explicitly chooses an alias.
5. Reserving `namespace` globally was rejected because contextual parsing preserves identifier compatibility.

## Validation strategy

Coverage includes parser and formatter behavior, contextual identifier compatibility, declaration placement and uniqueness, bare-call compatibility, selective imports, private visibility, direct-only namespace surfaces, transitive namespace isolation, alias override behavior, qualifier collisions, project-relative identity, type validation, standalone compilation, compiler execution, LSP navigation, references, rename, signature help, semantic tokens, overlay-aware namespace changes, module browsing, RFC 0022 through RFC 0025 regressions, and the complete test suite.
