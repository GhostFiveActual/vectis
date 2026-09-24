<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# VECTIS User Guide

## Purpose

VECTIS is a deterministic automation language. It converts source into typed syntax, validates the program, compiles an execution graph, and executes that graph through explicit runtime rules.

## Install

Create an isolated environment and install the package in editable mode:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Confirm the installation with `vectis version` and `vectis doctor`.

## Create a project

```bash
vectis init ./project
cd ./project
```

Validate every mission in the project:

```bash
vectis test .
```

## Project templates

List the deterministic built-in project templates:

```bash
vectis templates
```

Preview one template without writing files:

```bash
vectis templates release-gate
```

Materialize a selected template:

```bash
vectis init ./release-project --template release-gate
```

The template catalog is package-local. VECTIS does not download templates, discover a remote registry, execute generated missions, or activate included action-profile examples. Existing destination files fail closed unless `--force` is selected explicitly.

## Stages

Large missions can group related statements under named stages:

```vectis
stage "Security gate" {
    source critical_findings 0;
    let cleared critical_findings == 0;
    publish cleared;
}
```

Stages organize source and attach a stage path to compiled graph nodes. They do not create an implicit action, grant authority, or change cross-stage value dependencies.

## Declarations

A source declaration defines an initial value.

```vectis
source score 94;
source ready true;
source label "VECTIS";
```

A let declaration defines a deterministic computed value.

```vectis
let approved ready && score >= 80;
let title upper(label);
```

An analyze declaration reserves an analysis node that an embedding runtime may connect to a handler.

```vectis
analyze findings;
```

## Expressions

VECTIS supports strings, numbers, booleans, deterministic lists and objects, references, function calls, parentheses, unary operators, and binary operators.

Operator precedence from lowest to highest is:

1. `||`
2. `&&`
3. `==` and `!=`
4. `>`, `>=`, `<`, and `<=`
5. `+` and `-`
6. `*`, `/`, and `%`
7. unary `!`, `+`, and `-`
8. primary values and function calls

## Built in functions

Use:

```bash
vectis builtins
```

to print the current registry.

The function surface includes string normalization, string tests, replacement, bounded repetition, concatenation, length, numeric range checks, numeric clamping, aggregate boolean gates, counting, averaging, percentages, minimum, maximum, rounding, conversion, coalescing, and conditional selection.

Examples:

```vectis
let clean trim(raw_name);
let title upper(clean);
let bounded clamp(score, 0, 100);
let approved between(bounded, 80, 100);
let status if_else(approved, "AUTHORIZED", "REVIEW");
let message replace("MISSION READY", "READY", status);
let gates all_true(test_gate, security_gate, operations_gate);
let score average(quality, coverage, reliability);
```

## User-defined pure functions

Reusable calculations can be declared at program top level.

```vectis
function release_ready(score, risk) {
    return score >= 90 && risk <= 25;
}

function release_summary(score, risk) {
    return object(
        "approved", release_ready(score, risk),
        "score", score,
        "risk", risk
    );
}

mission "Release" {
    source quality 96;
    source risk 15;
    let summary release_summary(quality, risk);

    assert get(summary, "approved"), "Release gate failed";
    publish summary;
}
```

A function body is one returned expression. Parameters are local to the function and form its complete reference environment. Functions may call deterministic built-ins and other user-defined pure functions, including functions declared later in the source.

Pure-function parameters and results may carry contextual type annotations:

```vectis
function release_ready(
    score: number,
    risk: number
): boolean {
    return score >= 90 && risk <= 25;
}

function label(value: any): string {
    return upper(string(value));
}
```

Supported base annotations are `string`, `number`, `boolean`, `list`, `object`, and `any`. A list annotation may include a recursively nested item contract such as `list[number]`, `list[string]`, or `list[list[boolean]]`. Plain `list` remains the broad list contract, while `list[any]` explicitly accepts any item type. Parameters may be annotated individually, the result annotation is optional, and existing untyped declarations remain valid. Known call-site argument types are checked against annotated parameters. Declared list item contracts validate statically visible list elements and propagate through typed list parameters, list literals, declarations, pure-function results, and list indexing. A declared result type is checked against the statically inferred function body when that body type is known. `any` preserves the existing unknown-type behavior without weakening runtime authority boundaries.

```vectis
function first_score(scores: list[number]): number {
    return scores[0];
}

function release_scores(): list[number] {
    return [96, 92, 98];
}
```

Direct and indirect recursion are rejected before graph generation. Function bodies cannot capture mission values or contain capability, publication, analysis, process, filesystem, or network statements.

During compilation, calls expand into ordinary VECTIS expressions. Graph metadata preserves the source expression when expansion occurs, while runtime evaluation uses the expanded deterministic expression.

## Structured values

Lists and objects are first-class deterministic expressions.

```vectis
source build {
    passed: true,
    coverage: 96,
    checks: [true, true, false]
};

let coverage build.coverage;
let first_check build.checks[0];
let named_value build["coverage"];
```

Object keys may be identifiers or quoted strings. Member access uses `value.member`. Index access uses `value[index]`; list indices are integers and object indices are strings. Access failures are explicit runtime errors rather than implicit null values.

The constructor and lookup built-ins from earlier language lines remain supported:

```vectis
let legacy object("ready", true, "score", 96);
let ready get(legacy, "ready");
```

Structured values can be returned from pure functions, published, compared for equality, included in reports, and passed through the same deterministic graph/runtime pipeline as scalar values. They do not grant external authority.

## Modules and imports

Pure functions can be shared across source files.

```vectis
// lib/readiness.vectis
function release_ready(score) {
    return score >= 90;
}
```

```vectis
// missions/main.vectis
import "../lib/readiness.vectis";

mission "Release" {
    source score 96;
    publish release_ready(score);
}
```

Imports resolve relative to the importing file and remain inside the nearest project root containing `vectis.toml`. When no project manifest exists, the entry file directory is the boundary.

Imported modules may contain imports and top-level pure function declarations only. Missing files, absolute paths, root escapes, invalid extensions, cycles, and executable imported statements fail before graph generation.

Use `vectis modules FILE` to inspect the resolved module set for one entry file. Use `vectis modules PATH --browse` to inspect the complete project-bounded source catalog, dependency edges, function signatures, executable-file classification, and safe module diagnostics. Module loading and browsing do not grant runtime filesystem authority.

## Assertions

Assertions enforce mission invariants. An assertion may include a deterministic explanation after the condition.

```vectis
assert score >= 0 && score <= 100;
assert quality >= 90, "Quality score must be at least 90";
```

A false assertion fails its node and blocks later statements in the same block. When an explanation is present, Mission Control and other runtime consumers receive it in the failure record without changing the condition, graph scheduling, or authority model.

## Conditions

```vectis
when approved {
    publish "authorized";
} otherwise {
    publish "review";
}
```

Every node in each branch receives an explicit branch edge from the condition node.

## Actions

Actions represent explicit external effects while keeping the operation, required authority, input, result, and graph dependencies visible.

```vectis
action response "http.request" using "http" {
    method: "GET",
    url: endpoint
};

let healthy response.status == 200;
assert healthy, "Endpoint must return HTTP 200";
publish response.body;
```

The action result name behaves like a mission value after the action succeeds. Input must be an object, and every referenced input becomes an ordinary graph dependency.

Execution requires two independent host decisions. The capability must be granted through `CapabilityRegistry`, and the operation must be registered through `ActionRegistry` with that same capability. VECTIS rejects a source file that tries to pair a registered operation with a different capability.

The standard action registry can bind the bounded filesystem, process, and HTTP adapters. These bindings expose `filesystem.read_text`, `filesystem.write_text`, `process.run`, and `http.request`. The adapter instance still controls roots, executable allowlists, process environment, timeouts, HTTP transport behavior, and related boundaries.

Dry-run execution schedules action nodes but never invokes action handlers.

## CLI action profiles

The CLI can bind standard actions to bounded local adapters through an explicitly selected TOML profile.

```toml
[actions.filesystem]
roots = ["./workspace"]

[actions.process]
default_timeout = 30
max_timeout = 120

[actions.process.executables]
python = "/usr/bin/python3"

[actions.process.environment]
LANG = "C.UTF-8"

[actions.http]
allowed_hosts = ["api.example.com"]
default_timeout = 10
max_timeout = 30
```

Inspect the profile before execution:

```bash
vectis actions --config actions.toml
```

Use it with an execution surface:

```bash
vectis run --actions-config actions.toml mission.vectis
vectis mission --actions-config actions.toml mission.vectis
vectis timeline --actions-config actions.toml mission.vectis
vectis report --actions-config actions.toml mission.vectis
```

No profile is discovered automatically. Relative filesystem roots resolve from the profile directory. Process executable entries must use absolute paths and only profile-declared environment values reach the child process. HTTP profiles require explicit hostnames.

An action profile is an authority grant for one invocation. Keep profiles under the same review discipline as deployment configuration, executable allowlists, and filesystem permissions.

## Capabilities

The standard capability names are filesystem, process, and http.

```vectis
require "filesystem";
request "http";
```

Granting a capability name does not perform an external action. The embedding application still needs an explicit handler or adapter.

## Diagnostics

VECTIS diagnostics are structured product data. Each diagnostic carries a stable code, severity, message, and source span. Lexer failures use the LEX family, syntax failures use SYN, semantic failures use SEM, and capability failures use CAP.

Use `vectis check` for focused validation, `vectis check --details` for structural plan metrics, or `vectis inspect` when diagnostics should be reviewed beside tokens, syntax, and the compiled graph.

## Formatting

```bash
vectis fmt mission.vectis
vectis fmt --check mission.vectis
vectis fmt --write mission.vectis
```

## Inspection

```bash
vectis tokens mission.vectis
vectis parse mission.vectis
vectis plan mission.vectis
vectis inspect mission.vectis
vectis explain mission.vectis
vectis modules mission.vectis
vectis audit mission.vectis
vectis audit --json mission.vectis
vectis fingerprint mission.vectis
vectis verify mission.vectis --runs 5
vectis limits mission.vectis --max-nodes 500 --max-edges 1000 --max-depth 250 --max-width 200 --max-width 200
vectis report mission.vectis --output execution-report.html
```

Export graph formats:

```bash
vectis graph mission.vectis --format json
vectis graph mission.vectis --format dot
vectis graph mission.vectis --format mermaid
```

## Plan audit

Before execution, inspect graph identity, stage distribution, capability footprint, and structural complexity:

```bash
vectis audit mission.vectis
vectis audit --json mission.vectis
```

The audit is derived entirely from the compiled execution graph. It does not execute handlers or acquire authority.

## Determinism verification

Verify that repeated compilation produces the same graph fingerprint and that repeated dry-run scheduling produces the same execution order, states, and values:

```bash
vectis verify mission.vectis --runs 5
```

The command does not invoke runtime handlers. `vectis diff` compares two compiled plans without execution and reports fingerprints, summaries, and structural deltas.

## Plan identity and complexity budgets

Every compiled execution graph has a stable SHA-256 fingerprint:

```bash
vectis fingerprint mission.vectis
```

A plan can be required to remain inside explicit structural budgets:

```bash
vectis limits mission.vectis --max-nodes 500 --max-edges 1000 --max-depth 250
```

The command fails when the graph exceeds any configured node, edge, depth, or width limit. This provides a deterministic guard against unexpected plan growth before execution.

## Mission Control

For human operation, execute a mission through the branded Mission Control view:

```bash
vectis mission mission.vectis
```

Mission Control presents graph size, node state, resolved values, branch behavior, and published results while using the same compiler and runtime as the structured execution command.

## Execution timeline

Use the deterministic level view when a large plan is easier to understand as execution waves:

```bash
vectis timeline mission.vectis
```

Each level reports node identity, kind, stage, runtime state, and resolved value.

## Execution

```bash
vectis run --dry-run mission.vectis
vectis run mission.vectis
```

Runtime output includes success, execution order, node states, node values, and failures.

## Expression work

Evaluate one pure expression:

```bash
vectis eval 'if_else(93 >= 90, "READY", "REVIEW")'
```

Start an interactive session:

```bash
vectis repl
```

The REPL supports local value assignments for the current session, including values created with deterministic list and object functions.

## Examples

```bash
vectis examples
vectis examples release-gate
vectis examples functions
vectis examples pure-functions
vectis examples readiness
```

## Applications

Launch Mission Control Studio:

```bash
vectis studio
```

Launch the application demonstration:

```bash
vectis demo
```

Studio is for authoring and inspection. Launch Control demonstrates VECTIS embedded inside an application and renders deterministic execution waves from the same runtime timeline data exposed by the CLI.

## Language boundary

VECTIS is an automation language, not a general purpose replacement for Python or another host language. The value model includes scalar and deterministic structured values, reusable computation is expressed through top-level pure functions, and multi-file projects compose pure logic through deterministic imports. Runtime imports, package-registry discovery, function-local statement bodies, recursion, and bounded iteration remain outside the current language contract.


## Complexity budgets

Large plans can be constrained before execution:

```bash
vectis limits mission.vectis \
  --max-nodes 5000 \
  --max-edges 10000 \
  --max-depth 2000 \
  --max-width 1000 \
  --max-fan-in 64 \
  --max-fan-out 64
```

The command fails closed when any configured structural budget is exceeded.
