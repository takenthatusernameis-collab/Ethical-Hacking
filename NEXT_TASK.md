# Next Task for Agent

## Status (current)
- Working tree clean; 7 `.cover` deletions already committed/pushed to origin/main.
- Full suite: 3891 passed, 1 skipped. No regressions.
- ruff: 2010 pre-existing errors. No [tool.ruff] config.
- Coverage: ~99%; remaining gaps dead/optional-dep.

## Next precise task
Select a bounded feature or bug fix with concrete evidence. Coverage-hunting and junk cleanup exhausted. Do not redesign orchestration or weaken safety.

## Evidence / constraints
- Remote HEAD == local HEAD (7e7d38a).
- Do not commit unless explicitly asked.
