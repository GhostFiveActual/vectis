<!-- ghost-five-brand:start -->
<div align="center">

# VECTIS

### GHOST FIVE // VECTIS

**A language for turning what you intend to happen into a system that can prove how it will happen.**

<kbd>0.8.0</kbd> &nbsp; <kbd>PYTHON 3.11 TO 3.14</kbd> &nbsp; <kbd>MISSION CONTROL</kbd>

</div>
<!-- ghost-five-brand:end -->

VECTIS is a deterministic automation language and execution toolchain for work that needs to be understood before it runs. A mission is parsed, validated, compiled into an inspectable execution graph, and executed through explicit runtime and authority boundaries.

The result is automation with a visible path from intent to outcome. Source values, derived values, named stages, assertions, conditions, branches, capability requirements, runtime state, and published results remain available for inspection.

## Run the full showcase

The primary example is a complete production release assurance mission with test, quality, security, operations, recovery, change, migration, and release gates.

```bash
vectis check --details examples/showcase/full-release-assurance.vectis
vectis mission examples/showcase/full-release-assurance.vectis
```

For the full compiler view:

```bash
vectis inspect examples/showcase/full-release-assurance.vectis
```

For the execution topology:

```bash
vectis graph examples/showcase/full-release-assurance.vectis --format mermaid
```

The showcase uses named stages and a large mission so Mission Control exposes a substantial trace of source nodes, computed values, assertions, branch decisions, skipped paths, and published gate results.

## Mission Control

`vectis mission` is the human execution surface. It uses the same compiler and runtime as `vectis run`, but presents the result as an operational trace instead of raw JSON.

```bash
vectis mission examples/showcase/full-release-assurance.vectis
```

The output includes:

1. Mission and source identity.
2. Execution status.
3. Graph size.
4. Every runtime node state.
5. Resolved node values.
6. Skipped, blocked, failed, and successful paths.
7. Published results.
8. A stable plan fingerprint tied to the canonical compiled graph.

`vectis run` remains the structured interface for scripts and integrations.

## Language example

```vectis
mission "Release authorization" {
    source ready true;
    source quality 96;
    source risk 18;

    let authorized ready && quality >= 90 && risk <= 25;
    let status if_else(authorized, "AUTHORIZED", "REVIEW");

    assert quality >= 0 && quality <= 100;
    assert risk >= 0 && risk <= 100;

    when authorized {
        publish concat("RELEASE // ", status);
    } otherwise {
        publish "RELEASE // REVIEW";
    }
}
```

## Reusable pure logic

Top-level pure functions let a mission reuse deterministic rules without introducing hidden state or another execution engine.

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

mission "Release authorization" {
    source quality 96;
    source risk 15;
    let summary release_summary(quality, risk);

    assert get(summary, "approved"), "Release gate failed";
    publish summary;
}
```

Functions use explicit parameters, cannot capture mission state, cannot acquire capabilities, and cannot recurse. The compiler expands calls into ordinary expressions before graph generation, so fingerprints, dependencies, reports, and runtime execution continue through the same deterministic model.

## Multi-file modules

Reusable pure functions can live in separate VECTIS files.

```vectis
import "../lib/readiness.vectis";

mission "Release" {
    source score 96;
    publish release_ready(score);
}
```

An imported module contains only other imports and pure function declarations:

```vectis
function release_ready(score) {
    return score >= 90;
}
```

Imports resolve relative to the importing file and remain bounded by the nearest VECTIS project root identified by `vectis.toml`. Cycles, missing modules, paths outside the project root, and executable statements inside imported modules fail before graph generation.

Inspect module resolution directly:

```bash
vectis modules missions/main.vectis
```

Module loading is a compile-time source operation. It does not grant runtime filesystem authority.

## Structured mission state

VECTIS supports deterministic lists and objects through the same expression, semantic, graph, and runtime pipeline used by scalar values.

```vectis
mission "Structured release state" {
    source build {
        passed: true,
        coverage: 94,
        checks: [true, true, true]
    };

    let approved build.passed
        && build.coverage >= 90
        && all(build.checks);

    assert approved, "Build readiness requirements were not met";

    publish {
        status: if_else(approved, "AUTHORIZED", "REVIEW"),
        coverage: build.coverage,
        first_check: build.checks[0],
        check_count: size(build.checks)
    };
}
```

Structured values remain pure data. List and object literals, chained member access, and deterministic index access are part of the expression language and do not imply filesystem, process, HTTP, or other external authority. The earlier constructor and lookup built-ins remain available for compatibility.

## Explicit actions

VECTIS can represent external work as first-class execution graph nodes without turning pure expressions into side effects.

```vectis
mission "Fetch release metadata" {
    source endpoint "https://example.invalid/release";

    action response "http.request" using "http" {
        method: "GET",
        url: endpoint
    };

    assert response.status == 200,
        "Release metadata request must succeed";

    publish response.body;
}
```

An action names both its operation and the capability it expects to consume. Source code cannot register an operation or grant itself authority. The host must provide a matching capability grant and an `ActionRegistry` entry bound to the same capability.

The standard registry can bind the bounded filesystem, process, and HTTP adapters:

```python
from vectis.actions import ActionRegistry
from vectis.adapters.filesystem import FileSystemAdapter
from vectis.capabilities import Capability, CapabilityRegistry
from vectis.compiler import compile_ast_to_execution_graph
from vectis.parser import parse
from vectis.runtime import Runtime

actions = ActionRegistry()
actions.register_filesystem(
    FileSystemAdapter("./workspace")
)

capabilities = CapabilityRegistry()
capabilities.declare_capability(
    Capability(
        name="filesystem",
        description="Workspace file access",
    )
)

program = parse(
    """
    mission "Read" {
        action content "filesystem.read_text" using "filesystem" {
            path: "input.txt"
        };
        publish content;
    }
    """
)

result = Runtime(
    compile_ast_to_execution_graph(program),
    capabilities=capabilities,
    actions=actions,
).execute()
```

Built-in action bindings include `filesystem.read_text`, `filesystem.write_text`, `process.run`, and `http.request`. Filesystem roots, executable allowlists, process environments, HTTP behavior, and timeouts remain controlled by the adapter instance supplied by the host.

## CLI action profiles

External actions can run directly from the CLI through an explicitly selected TOML profile.

```toml
[actions.filesystem]
roots = ["./workspace"]

[actions.http]
allowed_hosts = ["api.example.com"]
default_timeout = 10
max_timeout = 30
```

```bash
vectis actions --config actions.toml
vectis audit --json mission.vectis
vectis run --actions-config actions.toml mission.vectis
vectis mission --actions-config actions.toml mission.vectis
```

VECTIS does not search for an authority profile. A profile has no effect until the operator supplies its path. Configured filesystem roots resolve from the profile location, process executables must be absolute allowlist entries, the parent process environment is not inherited, and CLI HTTP configuration requires an explicit hostname allowlist.

`vectis actions` describes the standard operation contracts without granting them. `vectis actions --config FILE` validates a selected profile and displays its capability and operation footprint without displaying process environment values.

## Why VECTIS

| Principle | VECTIS behavior |
| --- | --- |
| Intent is explicit | Missions use a defined language rather than hidden host language behavior. |
| Meaning is validated | Syntax, references, functions, and selected type rules are checked before execution. |
| Plans are inspectable | Valid source becomes a deterministic execution graph. |
| Authority is deliberate | Filesystem, process, and HTTP access remain behind explicit capability boundaries. |
| Results are explainable | Runtime state and resolved values remain available after execution. |
| Human and machine interfaces remain separate | Mission Control serves operators while structured JSON serves tools and integrations. |

## Installation

```bash
git clone https://github.com/GhostFiveActual/vectis.git
cd vectis

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Confirm the installation:

```bash
vectis version
vectis doctor
```

## Command reference

| Command | Purpose |
| --- | --- |
| `vectis mission FILE` | Execute through the human Mission Control view. |
| `vectis run FILE` | Execute and return structured runtime data. |
| `vectis check FILE` | Validate syntax and semantics. |
| `vectis check --details FILE` | Validate and print nodes, edges, depth, levels, width, fan-in, fan-out, sources, and sinks. |
| `vectis tokens FILE` | Print the lexer token stream. |
| `vectis parse FILE` | Print the typed syntax tree. |
| `vectis plan FILE` | Compile and print the execution graph. |
| `vectis inspect FILE` | Print tokens, syntax tree, diagnostics, and graph together. |
| `vectis graph FILE --format json` | Export graph JSON. |
| `vectis graph FILE --format dot` | Export Graphviz DOT. |
| `vectis graph FILE --format mermaid` | Export Mermaid topology. |
| `vectis explain FILE` | Summarize mission structure and complexity. |
| `vectis modules FILE` | Inspect deterministic source-module resolution. |
| `vectis audit FILE` | Inspect stages, capability footprint, structure, and plan identity without execution. |
| `vectis fingerprint FILE` | Print the stable SHA-256 fingerprint of the compiled plan. |
| `vectis verify FILE` | Recompile and dry-run repeatedly to prove deterministic plan identity and scheduling. |
| `vectis diff LEFT RIGHT` | Compare two compiled plans by fingerprint, structure, and metric deltas without execution. |
| `vectis limits FILE --max-nodes N` | Validate node, edge, depth, width, fan-in, and fan-out budgets. |
| `vectis timeline FILE` | Execute and group runtime state by deterministic graph level. |
| `vectis report FILE --output REPORT.html` | Execute a mission and write a standalone branded HTML trace. |
| `vectis fmt FILE` | Print canonical formatting. |
| `vectis fmt --check FILE` | Verify canonical formatting. |
| `vectis fmt --write FILE` | Rewrite source canonically. |
| `vectis eval EXPRESSION` | Evaluate one pure expression. |
| `vectis repl` | Open the deterministic expression REPL. |
| `vectis init PATH` | Create a VECTIS project scaffold. |
| `vectis test PATH` | Compile every VECTIS file below a path. |
| `vectis examples` | List packaged examples. |
| `vectis builtins` | Print the deterministic function registry. |
| `vectis actions` | Inspect standard action contracts or validate an explicit action profile. |
| `vectis capabilities` | Print standard capability names. |
| `vectis doctor` | Report environment information. |
| `vectis lsp` | Run the Language Server Protocol endpoint over standard input/output. |
| `vectis studio` | Launch VECTIS Mission Control Studio. |
| `vectis demo` | Launch the embedded application demonstration. |
| `vectis version` | Print the installed version. |

## Editor integration

VECTIS includes a dependency-free Language Server Protocol endpoint:

```bash
vectis lsp
```

Editors and LSP clients can launch that command over standard input/output. The server publishes VECTIS syntax and semantic diagnostics from the same compiler used by the CLI, provides canonical whole-document formatting, and exposes registry-backed completion, hover information, and typed-AST document symbols. It uses full-document synchronization so editor state remains explicit and deterministic.

Saved files with imports are validated through the project-bounded module loader. Unsaved imported documents are syntax-checked without pretending that stale files on disk represent the edited buffer.

See [Editor Integration](docs/editor-integration.md) for protocol behavior and client configuration guidance.

## Mission Control Studio

```bash
vectis studio
```

Studio provides source editing, canonical formatting, validation, execution topology, runtime state visualization, diagnostics, resolved values, syntax tree inspection, graph data, and built in function reference through the same language implementation used by the CLI.

Studio binds to loopback by default. Remote binding requires explicit opt in.

## Application demonstration

```bash
vectis demo
```

Launch Control demonstrates VECTIS embedded inside an application. Flight systems, navigation, communications, range, payload, fuel, weather, quality, and risk inputs become a multi-gate VECTIS mission whose real graph and runtime determine GO or HOLD. Preset scenarios force nominal, weather, systems, and risk paths while preserving the exact generated source, runtime trace, deterministic execution timeline, plan fingerprint, and standalone proof report.

## Architecture

```text
MISSION SOURCE
      │
      ▼
    LEXER
      │
      ▼
    PARSER
      │
      ▼
  TYPED AST
      │
      ▼
SEMANTIC ANALYSIS
      │
      ▼
EXECUTION GRAPH
      │
      ▼
DETERMINISTIC RUNTIME
      │
      ▼
EXPLICIT CAPABILITY ADAPTERS
```

The execution graph separates language meaning from runtime scheduling. External effects remain outside pure expression evaluation and behind explicit adapter boundaries.

## Documentation

Start with:

1. [Quickstart](docs/quickstart.md)
2. [User Guide](docs/user-guide.md)
3. [Language Grammar](docs/spec/grammar.md)
4. [Architecture Overview](docs/architecture/overview.md)
5. [Security Architecture](docs/architecture/security.md)
6. [Project Standards](docs/standards/README.md)
7. [Compatibility](COMPATIBILITY.md)
8. [RFC Process](docs/rfcs/README.md)
9. [Editor Integration](docs/editor-integration.md)
10. [Contributing](CONTRIBUTING.md)

## Quality

```bash
bash tools/quality-gate.sh
```

The gate validates compilation, tests, imports, repository boundaries, whitespace, secret patterns, symbolic links, branding, writing rules, code purpose headers, the comprehensive showcase, and large-plan regression behavior.

## Open source and contributions

VECTIS is licensed under the [Apache License 2.0](LICENSE). The license permits broad use, modification, and redistribution while providing explicit contributor patent terms.

Contributions are welcome through focused pull requests with tests and documentation appropriate to the behavior being changed. Compatibility expectations are defined in [COMPATIBILITY.md](COMPATIBILITY.md), durable design changes use the [RFC process](docs/rfcs/README.md), and contribution requirements are described in [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), and [GOVERNANCE.md](GOVERNANCE.md).

Copyright and attribution information is recorded in [NOTICE](NOTICE).
