# Next Task for Agent

## Status (current)
- Working tree clean (new ethscan/py.typed + pyproject.toml package-data).
- Full suite: 3891 passed, 1 skipped. No regressions.
- Coverage: 99%, 70 missing (provably dead or environment-dependent).
- ruff: pre-existing errors (1734 in ethscan/, 276 in tests/). No targeted linting this session.

## Next precise task
Select a bounded feature or bug fix with concrete evidence (reproducible failure, issue, or user request). Coverage-hunting and bulk cleanup are exhausted. Do not redesign orchestration or weaken safety controls.

## Evidence / constraints
- Remote HEAD == local HEAD (0dd67e6).
- Preserve smallest reversible change; verify with focused tests after change.
- Do not commit unless explicitly asked.

## Recommended next action
Inspect README/issue tracker for concrete, bounded gaps. If none apparent, leave the handoff as-is and do not speculate changes. Prioritize durability over activity.
