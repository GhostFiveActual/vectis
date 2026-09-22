<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# VECTIS Usability Contract

VECTIS treats the language, CLI, diagnostics, examples, and Studio as one user-facing product surface.

## Syntax consistency

The 0.1 language follows these conventions:

* blocks use `{ ... }`,
* statements end with `;`,
* strings use double quotes,
* function calls use `name(arg, ...)`,
* `when ... { ... } otherwise { ... }` is the conditional form,
* formatting is canonicalized by `vectis fmt`.

There is no automatic semicolon insertion and there are no `if`, `for`, or `while` statements in the current grammar.

## Beginner workflow

The recommended progression is:

```bash
vectis fmt --check mission.vectis
vectis check mission.vectis
vectis inspect mission.vectis
vectis run --dry-run mission.vectis
vectis run mission.vectis
```

Users who prefer a visual workflow can run `vectis studio` and use the same compiler/runtime through the local UI.

## Diagnostic clarity

Diagnostics should:

* carry a stable code,
* identify file/line/column through a source span,
* explain the violated contract without internal implementation jargon,
* be serializable for Studio/editor integrations.

## Studio accessibility

VECTIS Studio provides native buttons/selects/textarea controls, visible focus states, keyboard operation, focusable output regions, an ARIA live status area, and high-contrast dark presentation. Keyboard shortcuts supplement rather than replace native controls.

## Readability

Language and documentation examples should prefer small deterministic missions that expose dependencies clearly. Product documentation must describe implemented behavior and avoid speculative claims about future syntax or security controls.
