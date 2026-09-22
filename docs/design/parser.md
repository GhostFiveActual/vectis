<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# VECTIS Parser Design

## Contract

`parse(source, file=...) -> Program` is the canonical VECTIS source-to-AST
entry point. It invokes the reference lexer and produces the canonical AST from
`vectis.ast`.

The normative syntax contract is `docs/spec/grammar.md`. The parser does not
perform semantic analysis, capability validation, name resolution, execution
planning, or runtime work.

## Grammar implementation

The parser uses deterministic recursive descent. Statement productions map
directly to canonical AST statement classes. `otherwise` is not a standalone
statement; it is accepted only as the optional continuation of a `when`
statement and becomes `WhenStatement.otherwise`.

Expression precedence from lowest to highest is `||`, `&&`, `== !=`, `>= <=`,
`+ -`, `* /`, unary `! + -`, then primary expressions. Binary operators are
left associative. Unary operators are right associative. Parentheses override
precedence without introducing a separate AST node.

The lexer absorbs `+` or `-` into a numeric token when the sign is immediately
followed by a digit. Therefore `-42` is a `NumberLiteral`, while `-value` is a
`UnaryExpression`.

The case-sensitive identifier spellings `true` and `false` are contextual
boolean literals. Other identifier spellings are `Reference` nodes.

## Canonical AST mapping

The parser constructs only the canonical AST types.
It does not redefine compiler primitives.

`mission` maps to `Mission`, `source` to `SourceDeclaration`, `analyze` to
`AnalyzeDeclaration`, `require` to `RequireStatement`, `request` to
`RequestStatement`, `publish` to `PublishStatement`, `citations` to
`CitationsStatement`, `confidence` to `ConfidenceStatement`, and `when` to
`WhenStatement`.

## Source span policy

Every AST node retains a canonical source span. Literal and reference spans
come directly from tokens. Unary expressions span operator through operand.
Binary expressions span left operand through right operand. Blocks include
both braces. Simple statements span keyword through semicolon. Mission spans
keyword through closing brace. When spans extend through `otherwise` when
present. Program spans cover the first through last statement. Empty programs
receive a deterministic zero-width source span at line 1, column 1.

Parenthesized expressions retain their canonical AST type but widen the root
source span to include the parentheses.

## Diagnostic contract

Syntax diagnostics raise `ParserError` and include source file, one-based line,
and one-based column. Missing delimiters, malformed citations, standalone
`otherwise`, incomplete expressions, invalid statement starts, and unexpected
end of input fail deterministically. Lexer failures remain `LexerError`.

## Public API

`parse(source, file=...) -> Program` is the stable parser API for later
compiler stages. `Parser` remains available for deterministic token-stream
testing and compiler integration.
