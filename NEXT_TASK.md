# Next Task for Agent

## Status (current)
- Working tree clean; no source/test changes this session (documentation-only TASK.md update).
- Full suite: 3892 passed, 1 skipped. No regressions.
- ruff: 2010 pre-existing errors. No [tool.ruff] config.
- Coverage: ~99%; remaining gaps provably dead or optional-dep-dependent (fully characterized in TASK.md).

## Next precise task
Select a bounded feature or bug fix with concrete evidence. Coverage-hunting and junk cleanup are exhausted. Do not redesign orchestration or weaken safety.

## Evidence / constraints
- Remote HEAD == local HEAD (999e68b).
- Do not commit unless explicitly asked.