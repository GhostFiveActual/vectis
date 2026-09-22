<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# VECTIS Normative Grammar : 0.6

Status: normative for the `0.6.x` language line.

## Program

```ebnf
program =
    { import_statement | function_declaration | statement },
    EOF ;
```

Import and function declarations are valid only at program top level. A function body is one returned expression and cannot contain statements or capability operations.

## Imports

```ebnf
import_statement = "import", STRING, ";" ;
```

Import paths resolve relative to the importing source file. Resolution is bounded by the entry project's module root. Imported modules may contain only imports and pure function declarations.

## Statements

```ebnf
statement =
      mission_statement
    | stage_statement
    | source_statement
    | let_statement
    | analyze_statement
    | action_statement
    | require_statement
    | request_statement
    | assert_statement
    | publish_statement
    | citations_statement
    | confidence_statement
    | when_statement
    ;
```

`otherwise` is not an independent statement. It may occur only immediately after a `when` block.

## Blocks

```ebnf
block = "{", { statement }, "}" ;
```

## Pure functions

```ebnf
function_declaration =
    "function", IDENTIFIER,
    "(",
    [ IDENTIFIER, { ",", IDENTIFIER } ],
    ")",
    "{",
    "return", expression, ";",
    "}" ;
```

Function parameters are local values. A function body may reference its parameters, deterministic built-ins, and other user-defined pure functions. Function calls are validated for arity. Recursive call cycles are semantic errors.

## Mission

```ebnf
mission_statement = "mission", STRING, block ;
```

## Stage

```ebnf
stage_statement = "stage", STRING, block ;
```

A stage groups statements for human organization and graph metadata. Declarations remain visible to later stages. Assertion gating remains block-scoped inside the stage.

## Value declarations

```ebnf
source_statement = "source", IDENTIFIER, expression, ";" ;
let_statement    = "let", IDENTIFIER, expression, ";" ;
analyze_statement = "analyze", IDENTIFIER, [ expression ], ";" ;
```

`source` represents initial/input values. `let` represents deterministic computed values. `analyze` remains an explicit analysis node that may be connected to a runtime handler.

## Actions

```ebnf
action_statement =
    "action", IDENTIFIER,
    STRING,
    "using", STRING,
    expression,
    ";" ;
```

The identifier binds the action result as a mission value. The first string names the external operation. The `using` string names the capability that must be granted before the operation can run. The input expression must evaluate to an object.

Action operations are not discovered from the host environment and do not imply authority. The embedding application must explicitly register the operation with the same capability name. Missing capability grants, missing operations, and operation-to-capability mismatches fail closed.

## Capability statements

```ebnf
require_statement = "require", expression, ";" ;
request_statement = "request", expression, ";" ;
```

## Assertion

```ebnf
assert_statement =
    "assert", expression,
    [ ",", STRING ],
    ";" ;
```

The optional string is a deterministic human-readable explanation for assertion failure. It does not affect truth evaluation, scheduling, or authority. The semantic model requires an assertion expression to be boolean or not statically inferable. At runtime a false assertion fails, surfaces the message when present, and gates subsequent statements in the same block.

## Output / metadata statements

```ebnf
publish_statement = "publish", expression, ";" ;
confidence_statement = "confidence", expression, ";" ;

citations_statement =
    "citations", "[",
    [ expression, { ",", expression } ],
    "]", ";" ;
```

## Conditional

```ebnf
when_statement =
    "when", expression, block,
    [ "otherwise", block ] ;
```

## Expressions

Precedence from lowest to highest:

1. `||`
2. `&&`
3. `==`, `!=`
4. `>`, `>=`, `<`, `<=`
5. `+`, `-`
6. `*`, `/`, `%`
7. unary `!`, `+`, `-`
8. postfix member and index access
9. primary expressions

```ebnf
expression = logical_or ;

logical_or =
    logical_and,
    { "||", logical_and } ;

logical_and =
    equality,
    { "&&", equality } ;

equality =
    comparison,
    { ( "==" | "!=" ), comparison } ;

comparison =
    additive,
    { ( ">" | ">=" | "<" | "<=" ), additive } ;

additive =
    multiplicative,
    { ( "+" | "-" ), multiplicative } ;

multiplicative =
    unary,
    { ( "*" | "/" | "%" ), unary } ;

unary =
      ( "!" | "+" | "-" ), unary
    | postfix
    ;

primary =
      structured_literal
    | STRING
    | NUMBER
    | boolean_literal
    | function_call
    | reference
    | "(", expression, ")"
    ;

postfix =
    primary,
    {
        ".", IDENTIFIER
        | "[", expression, "]"
    } ;

structured_literal =
      list_literal
    | object_literal
    ;

list_literal =
    "[",
    [ expression, { ",", expression } ],
    "]" ;

object_literal =
    "{",
    [
        object_member,
        { ",", object_member }
    ],
    "}" ;

object_member =
    ( IDENTIFIER | STRING ),
    ":",
    expression
    ;

function_call =
    IDENTIFIER, "(",
    [ expression, { ",", expression } ],
    ")" ;

reference = IDENTIFIER ;
boolean_literal = "true" | "false" ;
```

## Function names

The parser accepts any identifier-shaped call. Semantic analysis resolves calls against user-defined pure functions and the deterministic built-in registry. Built-in names are reserved and cannot be reused by a user-defined function. The installed built-in registry is discoverable with:

```bash
vectis builtins
```

Unknown functions are semantic errors rather than parser errors.

## Deliberate syntax exclusions

The grammar excludes runtime imports, package-registry imports, loops, function-local statement bodies, and recursive functions. Imported source modules support only imports and top-level pure function declarations. Structured values support list and object literals plus member and index access, while the existing `list(...)`, `object(...)`, `get(...)`, and `has(...)` built-ins remain supported for compatibility.
