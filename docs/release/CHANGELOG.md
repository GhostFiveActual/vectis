<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# VECTIS Release Record

## 0.8.0

### Editor integration and clean canonical baseline

| Area | Release state |
| --- | --- |
| Language server | `vectis lsp` provides a dependency-free Language Server Protocol endpoint over standard input/output. |
| Diagnostics | Editors receive syntax and semantic diagnostics from the same VECTIS compiler used by the CLI. |
| Formatting | Whole-document formatting uses the canonical VECTIS formatter rather than a separate editor implementation. |
| Completion | Completion items are generated from language keywords, deterministic built-ins, and the standard action registry. |
| Hover | Keyword, built-in, and standard-action hover information comes from shared language and registry metadata. |
| Symbols | Document symbols are derived from the typed AST and expose functions, missions, stages, declarations, and actions. |
| Modules | Saved imported files are validated through the project-bounded module loader; unsaved imported buffers remain explicitly syntax-only until overlay resolution is available. |
| Packaging | The supported Python matrix remains 3.11 through 3.14 and release verification includes isolated-wheel CLI and LSP protocol smoke tests. |
| Repository | The canonical public repository begins this release line from a parentless root commit containing the audited VECTIS tree only. |
| Compatibility | The language and runtime contracts from 0.7 remain compatible; 0.8 adds editor-facing tooling without broadening runtime authority. |
## 0.7.0

### Operator action profiles

| Area | Release state |
| --- | --- |
| CLI execution | `run`, `mission`, `timeline`, and `report` accept an explicitly selected `--actions-config FILE`. |
| Inspection | `vectis actions` describes standard contracts and `vectis actions --config FILE` validates a profile without displaying process environment values. |
| Filesystem | Profile roots resolve relative to the profile and remain confined by the filesystem adapter. |
| Process | Executables are explicit absolute allowlist entries, timeouts remain bounded, and parent environment inheritance remains disabled. |
| HTTP | CLI profiles require exact hostname allowlists in addition to scheme, credential, redirect, proxy, and timeout controls. |
| Audit | Action capabilities contribute to the required authority footprint and action nodes expose operation-to-capability mappings. |
| Scaffolding | `vectis init` writes an inert `actions.example.toml` that is never loaded automatically. |
| RFC | RFC 0004 records the profile format, authority model, inspection surface, compatibility contract, and alternatives. |
| Compatibility | Existing source behavior is preserved while CLI authority remains explicit and opt-in. |

## 0.6.0

### Explicit bounded actions

| Area | Release state |
| --- | --- |
| Action syntax | `action result "operation" using "capability" { ... };` binds an external result while keeping operation and authority visible in source. |
| Graph | Actions compile into dedicated nodes with deterministic input expressions, explicit operation and capability metadata, stage context, and dependency edges. |
| Runtime | Missing grants, missing operations, capability mismatches, invalid inputs, adapter failures, and invalid result values fail closed. |
| Registry | `ActionRegistry` binds every operation to exactly one capability and exposes a deterministic manifest. |
| Standard bindings | Bounded filesystem reads/writes, allowlisted process execution, and structured HTTP requests can be registered through existing adapters. |
| Results | Action results remain inside the VECTIS value model and can feed assertions, branches, publications, reports, and later actions. |
| Dry run | Dry-run execution never invokes action handlers. |
| RFC | RFC 0003 records syntax, graph behavior, determinism limits, authority rules, compatibility, and alternatives. |
| Compatibility | Existing 0.2 through 0.5 source remains valid under the 0.6 contract except where the reserved `action` and `using` keywords apply. |

## 0.5.0

### Deterministic multi-file projects

| Area | Release state |
| --- | --- |
| Imports | `import "path.vectis";` loads reusable pure declarations from another source file. |
| Project boundary | Resolution remains inside the nearest project root identified by `vectis.toml`, or the entry file directory when no manifest exists. |
| Module contents | Imported files may contain imports and pure function declarations only, preventing hidden executable mission behavior. |
| Dependency graph | Transitive imports resolve deterministically, duplicate paths load once, and cycles fail before graph generation. |
| Inspection | `vectis modules FILE` exposes the resolved module set and project root. |
| Project tooling | `vectis init` creates a reusable library module and `vectis test` validates module-aware projects. |
| CLI | Validation, execution, inspection, timeline, reporting, verification, graph export, and plan tools resolve imports consistently. |
| Authority | Module loading is compile-time source resolution and does not grant runtime filesystem authority. |

## 0.4.0

### First-class structured syntax

| Area | Release state |
| --- | --- |
| List literals | `[value, value]` creates deterministic structured list values directly in the language. |
| Object literals | `{key: value}` creates deterministic ordered object values with identifier or quoted keys. |
| Member access | `object.member` reads an existing object member with explicit failure for invalid access. |
| Index access | `list[index]` and `object["key"]` provide deterministic indexed lookup. |
| Pure functions | Function bodies and return values can use the structured syntax without changing the compile-time expansion model. |
| Compatibility | Existing `list(...)`, `object(...)`, `get(...)`, and related structured built-ins remain valid. |
| Determinism | Structured syntax lowers through the same AST, semantic, graph, runtime, fingerprint, and reporting pipeline. |
| Authority | Structured expressions remain pure data and do not broaden capability or adapter authority. |

## 0.3.0

### Reusable deterministic computation

| Area | Release state |
| --- | --- |
| Pure functions | Top-level user-defined functions provide reusable expression logic with explicit parameters and one returned expression. |
| Scope | Function bodies can reference only their parameters, deterministic built-ins, and other user-defined pure functions. |
| Call graph | Forward calls are supported while direct and indirect recursion are rejected before graph generation. |
| Compilation | Function calls expand into ordinary VECTIS expressions before dependency discovery and runtime execution. |
| Inspection | Graph metadata retains the authored source expression when function expansion changes the executable expression. |
| Types | Statically inferable function results participate in ordinary boolean, numeric, string, list, and object semantic checks. |
| RFC | RFC 0001 records the function contract, determinism model, authority boundary, alternatives, and compatibility requirements. |
| Authority | Function declarations create no runtime action nodes and cannot capture or acquire external authority. |
| Packaging | CI and release verification execute user-defined functions from an isolated installed wheel on the supported Python matrix. |

## 0.2.0

### Structured state and durable project contracts

| Area | Release state |
| --- | --- |
| Structured values | Deterministic list and object values flow through expressions, semantic typing, compiled graphs, runtime values, publications, CLI JSON, and reports. |
| Collection operations | Pure functions provide construction, lookup, membership checks, key and value projection, sizing, and boolean collection gates. |
| Assertions | Assertions may carry deterministic human-readable failure explanations without changing truth evaluation or authority. |
| Public history | The public project begins from a sanitized parentless VECTIS root, and CI audits the tree plus reachable refs and history for retired private labels. |
| Compatibility | A documented versioning, deprecation, serialization, and migration contract governs public behavior. |
| Design process | Durable language and architecture changes use a documented RFC process and design-proposal workflow. |
| Authority | Structured data remains pure computation and does not broaden filesystem, process, HTTP, or adapter authority. |
| Platform | CI validates Python 3.11, 3.12, 3.13, and 3.14, including package build and isolated wheel execution. |

## 0.1.4

### Determinism proof and plan comparison

| Area | Release state |
| --- | --- |
| Plan comparison | `vectis diff` compares compiled plan fingerprints, structural summaries, and metric deltas without execution. |
| Determinism verification | `vectis verify` remains side-effect-free and proves repeated compiler and dry-run scheduler stability. |
| Deep-plan regression | Automated coverage compiles, fingerprints, and executes a 600-step dependency chain. |
| Launch Control timeline | The demonstration application renders deterministic graph levels and node state as execution waves. |
| Compatibility | Existing 0.1 syntax, stage behavior, capability boundaries, structured runtime output, audit, timeline, reporting, and package interfaces remain compatible. |

## 0.1.3

### Plan scale and operator experience

| Area | Release state |
| --- | --- |
| Execution timeline | `vectis timeline` groups runtime state and resolved values by deterministic graph level. |
| Complexity budgets | `vectis limits` enforces node, edge, depth, width, fan-in, and fan-out ceilings. |
| Launch Control | The demonstration application produces a standalone HTML proof report from the exact compiled plan and runtime result. |
| Human verification | Mission Control, timeline output, plan audit, fingerprints, determinism verification, and reports describe the same execution model at different levels of detail. |
| Compatibility | Existing 0.1 language syntax, graph serialization, capability boundaries, and structured execution output remain compatible. |

## 0.1.2

### Determinism and plan control

| Area | Release state |
| --- | --- |
| Determinism verification | `vectis verify` repeats parsing, compilation, graph fingerprinting, and dry-run scheduling and fails on any divergence. |
| Width budgets | `vectis limits` can reject plans whose maximum topological width exceeds an explicit budget. |
| Public contract | README, quickstart, user guide, CLI design, and regression coverage describe the same verification and complexity controls. |
| Compatibility | The 0.1 language syntax, graph serialization, runtime authority model, and existing CLI behavior remain compatible. |

## 0.1.1

### Release surface

| Area | Release state |
| --- | --- |
| Plan audit | Human and JSON inspection of graph shape, stage distribution, capability footprint, determinism, and plan fingerprint before execution. |
| Large-plan analysis | Linear adjacency construction for graph metrics plus deep-chain and wide-plan regression coverage. |
| Launch Control | Stage count and compiled plan fingerprint displayed beside execution telemetry. |
| Public policy | Product-tree checks without embedding private organizational names in policy source. |
| Compatibility | The 0.1 language, execution graph serialization, capability boundaries, and public command contracts remain compatible. |

## 0.1.0

### Product surface

| Area | Release state |
| --- | --- |
| Language | Scalar declarations, computed values, assertions, deterministic functions, arithmetic, comparison, boolean logic, conditional branches, publications, confidence, citations, and capability statements. |
| Compiler | Lexer, parser, typed syntax tree, semantic analysis, execution graph generation, structured diagnostics, and deterministic formatting. |
| Runtime | Deterministic indexed scheduling, dependency value resolution, branch selection, assertion gating, runtime state tracking, published values, capability checks, and large-plan execution coverage. |
| CLI | Validation, inspection, execution, Mission Control, formatting, expression evaluation, graph export, HTML execution reports, project initialization, project testing, REPL, environment diagnostics, and application launchers. |
| Studio | Source editing, validation, topology, runtime state visualization, diagnostics, syntax tree inspection, graph data, and built in reference. |
| Demo | Launch Control application backed by a multi-gate VECTIS mission, compiler, and runtime. |
| Examples | Language fixtures plus a comprehensive production release assurance showcase. |
| Quality | Python 3.11 through 3.14 CI, package build, installed wheel smoke test, repository policy, security checks, comprehensive showcase coverage, and staged execution plans with hundreds of deterministic nodes. |

## 0.0.1

The 0.0.1 tag records the initial compiler, execution graph, runtime, capability model, adapters, structured diagnostics, packaging, and CLI baseline.
