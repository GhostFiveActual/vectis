<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# VECTIS Command Line Toolchain

## Purpose

The VECTIS command line serves two audiences without forcing either one to compromise. Engineering commands return structured data that scripts and integrations can consume. Mission Control gives a human operator a branded execution view built from the same compiler and runtime result.

## Operator command

```bash
vectis mission mission.vectis
```

Mission Control executes the validated graph and renders node state, resolved values, branch behavior, graph size, plan depth, plan width, published output, and overall mission status as an operational console.

Use `--dry-run` to inspect deterministic scheduling, repeat `--capability NAME` for direct grants, or provide `--actions-config FILE` when external action adapters are required. Action profiles are never discovered automatically.

## Engineering commands

| Command | Contract |
| --- | --- |
| `check` | Parse, analyze, and compile without execution. Use `--details` for structural plan metrics. |
| `tokens` | Emit lexer tokens as JSON. |
| `parse` | Emit the typed syntax tree as JSON. |
| `plan` | Emit the execution graph as JSON. |
| `inspect` | Emit tokens, syntax tree, diagnostics, and graph together. |
| `run` | Execute the validated graph and return structured runtime data. |
| `fmt` | Print, verify, or write canonical formatting. |
| `eval` | Evaluate one pure scalar expression. |
| `graph` | Export JSON, Graphviz DOT, or Mermaid graph text. |
| `explain` | Emit a structural mission summary. |
| `audit` | Inspect plan shape, stages, capability footprint, and deterministic identity without execution. |
| `fingerprint` | Print the stable SHA-256 fingerprint of the compiled execution graph. |
| `verify` | Prove repeated compilation and dry-run scheduling remain identical. |
| `diff` | Compare two compiled plans by fingerprint, structure, and metric deltas without execution. |
| `limits` | Validate explicit node, edge, depth, and width budgets. |
| `report` | Execute a mission and write a standalone HTML execution report. |
| `init` | Create a branded project scaffold. |
| `test` | Compile every VECTIS file under a path. |
| `examples` | List or print canonical examples. |
| `repl` | Run an interactive deterministic expression session. |
| `builtins` | Emit the built in function registry. |
| `actions` | Inspect standard action contracts or validate one explicit action profile. |
| `capabilities` | Emit the standard capability registry. |
| `doctor` | Report local runtime information. |
| `version` | Print the installed version. |
| `studio` | Launch VECTIS Mission Control Studio. |
| `app` | Alias for Studio. |
| `demo` | Launch the Launch Control application. |
| `showcase` | Alias for the Launch Control application. |

## Output discipline

`vectis run` remains the machine friendly execution interface. `vectis mission` is the human presentation layer. Both use the same language, compiler, graph, evaluator, and runtime.

This separation is intentional. A more exciting operator experience must not make automation output harder to consume from another system.

## Exit behavior

| Code | Meaning |
| --- | --- |
| `0` | Requested operation completed successfully. |
| `1` | Validation, compilation, project testing, or runtime execution failed. |
| `2` | User input, path, encoding, or command data was invalid. |
