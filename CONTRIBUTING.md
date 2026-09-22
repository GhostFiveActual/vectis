<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# Contributing to VECTIS

VECTIS favors deterministic behavior, explicit contracts, focused changes, and tests that exercise the real compiler and runtime path.

## Development setup

```bash
git clone https://github.com/GhostFiveActual/vectis.git
cd vectis

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

## Read the contracts

Before changing language or runtime behavior, review the relevant documents:

* `docs/spec/grammar.md`
* `docs/spec/semantic-model.md`
* `docs/architecture/compiler-pipeline.md`
* `docs/architecture/runtime.md`
* `docs/architecture/security.md`
* `docs/standards/README.md`
* `COMPATIBILITY.md`
* `docs/rfcs/README.md`

Do not silently broaden syntax, runtime authority, adapter access, or compatibility guarantees.

## Required verification

```bash
bash tools/quality-gate.sh
```

Runtime and compiler changes require regression coverage through the actual source to runtime path.

Package-affecting changes must also build and install successfully:

```bash
python -m pip install build
python -m build
```

Install the generated wheel into an isolated environment outside the repository and execute the CLI from that environment.

## Pull request contract

A focused pull request explains:

1. The behavior affected.
2. The contract affected.
3. How determinism is preserved.
4. Whether authority changes.
5. The tests that prove the behavior.
6. The documentation that describes the behavior.

Keep unrelated refactors separate.

## Design proposals

Changes that affect durable language, semantic, execution graph, runtime, authority, serialization, or compatibility contracts begin with the design proposal issue template.

Maintainers may require a numbered RFC before implementation. The RFC process is defined in [docs/rfcs/README.md](docs/rfcs/README.md), and compatibility expectations are defined in [COMPATIBILITY.md](COMPATIBILITY.md).

## Contribution licensing

VECTIS is licensed under Apache License 2.0. Unless you explicitly state otherwise, a contribution intentionally submitted for inclusion in VECTIS is provided under Apache License 2.0 in accordance with section 5 of that license.

## Security-sensitive changes

Changes involving capabilities, filesystem boundaries, process execution, environment inheritance, HTTP access, dynamic execution, or privilege boundaries require explicit security review.

See [SECURITY.md](SECURITY.md).

## Community and governance

Participation is governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Repository decision and review responsibilities are described in [GOVERNANCE.md](GOVERNANCE.md).
