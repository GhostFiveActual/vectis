<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# VECTIS AST Invariants

## Purpose

The VECTIS abstract syntax tree is the typed boundary between parsing and
semantic analysis.

The AST records what the source says. It does not perform name resolution,
type inference, capability authorization, dependency ordering, execution-graph
construction, or runtime execution.

## Canonical source locations

Every AST node owns exactly one canonical `vectis.source_span.SourceSpan`.

The AST must never redefine `SourcePosition` or `SourceSpan`.

This preserves a single source-location model across lexer, parser,
diagnostics, semantic analysis, and later compiler stages.

## Immutability

AST nodes are frozen dataclasses.

Child collections are tuples rather than mutable lists.

A parser constructs a tree; later compiler phases inspect that tree rather
than mutating its syntax.

Derived semantic information belongs in later semantic or intermediate
representations rather than being attached by mutation to AST nodes.

## Node categories

`Node` is the root AST type.

`Expression` represents value-producing syntax.

`Statement` represents declarative or executable syntax.

`Program` is the root source unit.

`Block` contains an ordered tuple of statements.

The initial expression model contains:

* string literals
* numeric literals
* boolean literals
* symbolic references
* unary expressions
* binary expressions

The initial statement model contains:

* mission declarations
* source declarations
* analysis declarations
* requirements
* requests
* publication
* citations
* confidence declarations
* conditional branches

These categories reflect the current semantic model. They do not define
operator precedence or concrete parsing rules.

## Structural typing

Fields that represent expressions accept only `Expression` nodes.

Fields that represent statements accept only `Statement` nodes.

Blocks and programs contain only statements.

Names must be non-empty strings.

The AST performs structural construction validation only. Symbol resolution,
duplicate-name detection, type compatibility, capability validation, and
execution dependency validation belong to semantic analysis.

## Conditional representation

A `when` construct is represented by one `WhenStatement`.

Its primary branch is `body`.

An optional `otherwise` branch is represented as another `Block`.

`otherwise` is therefore not an independent executable statement in the AST;
it is structurally attached to the conditional it completes.

## Source-span policy

Every node retains its own source span, including nested expressions.

Container spans should cover the concrete source represented by the container.
Exact parser span construction will be defined by the parser contract.

The AST does not manufacture or normalize source locations.

## Grammar boundary

This AST deliberately does not claim to be the normative concrete grammar.

The repository currently has a lexical specification, semantic model, and
syntax draft. Before parser implementation, VECTIS must establish a normative
grammar that maps concrete productions to these AST structures.

That grammar may refine AST fields where concrete syntax requires it, but it
must preserve the invariants in this document unless the language-design
contract is intentionally revised.
