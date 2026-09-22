<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# VECTIS Quickstart

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Confirm the installation:

```bash
vectis version
vectis doctor
```

## Run the complete showcase

```bash
vectis check --details examples/showcase/full-release-assurance.vectis
vectis audit examples/showcase/full-release-assurance.vectis
vectis verify examples/showcase/full-release-assurance.vectis --runs 5
vectis mission examples/showcase/full-release-assurance.vectis
vectis timeline examples/showcase/full-release-assurance.vectis
```

The showcase exercises a large mission with multiple independent gates, derived values, assertions, conditional branches, skipped paths, and published results.

Inspect the compiler output:

```bash
vectis inspect examples/showcase/full-release-assurance.vectis
```

Export the topology:

```bash
vectis graph examples/showcase/full-release-assurance.vectis --format mermaid
```

## Create a project

```bash
vectis init ./vectis-project
cd ./vectis-project
vectis test .
vectis mission missions/main.vectis
```

## Reuse deterministic logic

Top-level pure functions keep mission rules reusable without introducing hidden state.

```vectis
function release_ready(score, risk) {
    return score >= 90 && risk <= 25;
}

mission "Quick release gate" {
    source quality 96;
    source risk 15;
    let approved release_ready(quality, risk);
    assert approved, "Release gate failed";
    publish approved;
}
```

Save the source and inspect both its authored and compiled forms:

```bash
vectis check mission.vectis
vectis inspect mission.vectis
vectis mission mission.vectis
```

## Split logic into modules

A project created by `vectis init` includes a reusable `lib/` module. Imports resolve relative to the importing file.

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

Inspect and execute the resolved project:

```bash
vectis modules missions/main.vectis
vectis check missions/main.vectis
vectis mission missions/main.vectis
```

Imported modules contain pure function declarations and imports only. They cannot hide executable mission statements or capability operations.

## Use structured mission state

Structured lists and objects can be written directly and inspected through member or index access.

```vectis
mission "Structured gate" {
    source build {
        ready: true,
        score: 96,
        checks: [true, true, true]
    };

    let approved build.ready
        && build.score >= 90
        && all(build.checks);

    assert approved, "Structured gate failed";

    publish {
        status: if_else(approved, "AUTHORIZED", "REVIEW"),
        score: build.score,
        first_check: build.checks[0]
    };
}
```

The earlier `list(...)`, `object(...)`, and `get(...)` forms remain supported.

## Run bounded actions from the CLI

Start from the inert profile written by `vectis init`, copy it to a local authority file, and review the resulting contract.

```bash
cp actions.example.toml actions.toml
vectis actions --config actions.toml
```

A filesystem action mission can then run through that selected profile:

```vectis
mission "Read project file" {
    action content "filesystem.read_text" using "filesystem" {
        path: "README.md"
    };

    publish content;
}
```

```bash
vectis audit --json read.vectis
vectis run --actions-config actions.toml read.vectis
```

The CLI never discovers `actions.toml` on its own. Process profiles require absolute executable paths, and HTTP profiles require explicit hostnames.

## Work with expressions

```bash
vectis eval 'clamp(108, 0, 100)'
vectis eval 'if_else(94 >= 80, "AUTHORIZED", "REVIEW")'
vectis repl
```

## Launch Mission Control Studio

```bash
vectis studio
```

## Launch the embedded application demo

```bash
vectis demo
```
