<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# Engineering Standard

## Repository discipline

The repository presents one public product surface. Temporary state, generated caches, private orchestration, credentials, and local environment files do not belong in the tracked product tree.

Source code, tests, documentation, examples, packaging, and automation each have a defined purpose and location.

## Code comments

Every source, test, tool, configuration, and example file identifies VECTIS near the beginning of the file and includes a concise statement of purpose.

Names carry most of the implementation meaning. Comments explain contracts, security boundaries, nonobvious decisions, and failure behavior.

## Implementation rules

1. Prefer deterministic behavior when the problem permits it.
2. Keep external authority explicit.
3. Validate input before side effects.
4. Make security boundaries fail closed.
5. Keep public APIs intentional.
6. Document compatibility behavior.
7. Protect behavior with tests before merge.
8. Keep generated artifacts separate from source of truth.
9. Require architecture review before introducing dynamic execution.
10. Give user facing commands stable exit codes and readable diagnostics.

## Quality gate

Run:

```bash
bash tools/quality-gate.sh
```

The gate is safe to execute repeatedly and fails on policy violations instead of silently correcting them.
