# Next Task for Agent

## Status
- Working tree: modified (ethscan/cli.py). Not committed (per "do not commit unless explicitly asked"). HEAD f94613c.
- Tests: 3902 passed, 1 skipped. No regressions.
- Compilation/imports: clean.
- Packaging: `ethscan/py.typed` included in package data (PEP 561).

## Completed this session
- Removed a genuine dead-code defect: the module-level `hash` function in `ethscan/cli.py` (former lines 448–637) was an unreferenced duplicate of the `hash` command. The real `hash` command is `hash_cmd` (registered via `@cli.command(name="hash")`). Exhaustive search confirmed no code path, test, or import called the orphan — it only shadowed the builtin `hash` at module scope.
- Verified removal: 53 registered commands (was 54 counting the phantom), `hash` CLI still functional, full suite green.

## Next precise task
None apparent. If resuming, re-verify: `python -m pytest -q` and `python -m ethscan hash --password test --algorithm sha256`. Do not apply stash; do not hunt lint/type/coverage.

(End of file - total 15 lines)