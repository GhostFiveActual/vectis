<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# VECTIS Lexical Specification : 0.1

Status: normative.

## Whitespace

Spaces, tabs, carriage returns, and newlines separate tokens and are otherwise ignored.

## Comments

Line comments begin with `//` and continue to the end of the line.

## Keywords

```text
mission
source
let
analyze
when
otherwise
publish
request
require
assert
citations
confidence
```

`true` and `false` are contextual boolean literals and remain identifier tokens so they can be handled by the expression parser.

## Identifiers

Identifiers begin with an ASCII letter or `_` and continue with ASCII letters, digits, or `_`.

Examples:

```text
ready
quality_score
_private_value
starts_with
```

Built-in function names are ordinary identifiers followed by `(`.

## Strings

Strings are delimited by double quotes:

```vectis
"Ghost Five // VECTIS"
```

The current lexer preserves characters literally until the closing double quote. Backslash escape processing is not currently defined.

## Numbers

Integers and decimal numbers are supported. A leading `+` or `-` immediately followed by a digit is tokenized as part of the numeric literal.

```text
42
-12
+8
0.95
```

## Punctuation

```text
{ } ( ) [ ] ; ,
```

Square brackets are currently used by the `citations` statement; general list expressions are outside the 0.1 grammar.

## Operators

Multi-character operators:

```text
>=  <=  ==  !=  &&  ||
```

Single-character operators:

```text
+  -  *  /  %  !  <  >
```

Bare `=`, `&`, and `|` are rejected because assignment and bitwise operators are not defined.

## Source locations

Every token carries a one-based file/line/column `SourceSpan`. Diagnostics retain these positions through lexer and parser errors.
