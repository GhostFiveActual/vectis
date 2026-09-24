<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# RFC 0023: Selective Function Imports

## Status

Accepted and implemented.

## Problem

Bare imports intentionally expose the reachable public function graph. That preserves simple module composition, but a source file cannot state that it depends on only a specific subset of a direct module surface.

## Syntax

A selective import places one or more public function names after the path:

```vectis
import "lib/gate.vectis" {ready, score};
```

The existing bare form remains valid:

```vectis
import "lib/gate.vectis";
```

Selector order is preserved by parsing and formatting. The selector list must contain at least one unique identifier.

## Resolution contract

1. Every selected name must be declared directly by the imported module.
2. A selected declaration must be public.
3. A module that contains a selective import may call its own functions, names selected from direct imports, and public functions reachable through any bare import in that same source module.
4. A selected public function may continue to call private helpers and imported dependencies according to the rules of its own source module.
5. Bare imports preserve the existing reachable public behavior.
6. Function declarations remain in the flattened compilation program and retain globally unique names. Namespace identity and aliases remain separate work.

Missing, private, duplicate, or unselected names fail before graph generation when static module information is available.

## Editor and inspection surfaces

Overlay-aware workspaces enforce the same selector contract as disk-backed loading. Selective import names participate in function definition, references, and rename. Semantic tokens classify selector names as functions. Module browsing reports an additive `names` field on each import record, using `null` for a bare import and a string list for a selective import.

## Authority and execution

Selective imports affect compile-time name access only. Runtime scheduling, capabilities, action profiles, adapters, receipts, and external authority are unchanged.

## Compatibility

Existing bare imports retain their previous source and runtime behavior. The package version remains `0.8.0` for this implementation line.

## Validation

Validation covers parser and formatter round trips, duplicate selectors, selected execution, rejected missing and private selections, rejected unselected calls, transitive dependency use, bare-import compatibility, overlay resolution, navigation and rename, semantic tokens, module browsing, repository policy, public history, privacy boundaries, and the complete unit suite.
