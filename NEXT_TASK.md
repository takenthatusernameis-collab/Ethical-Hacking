# Next task

None pending. Repository fully green and saturated (49964 passed, 147 skipped, 0 failed;
mypy clean over 278 files; ruff clean; README 0 drift; coverage 100%). Do NOT fabricate
work, repeat verification-only sessions as progress, or make empty/control-marker commits.

This session made no code change: the prior handoff ("None pending; do not fabricate")
was treated as the assignment. I independently re-verified the baseline and every
documented README console example from a real shell (all matched byte-for-byte), and
confirmed the documented contracts are already locked by deterministic tests
(`test_cli.py` auto-discovered target-usage sweep, `test_readme_sync.py`,
`test_readme_examples.py`, `test_cache_content_sweep.py`). No reproducible gap exists.

`cidr`/`validate` IPv6 `/127`, `oracle`/`postgresql` empty-target handling, and the
`ethscan/cli.py` unreachable guard remain intentional documented divergences — do not
modify. Do not modify `.github/workflows/**`.

If future work is genuinely needed, FIRST reproduce a concrete gap (focused failing
check, fresh-install failure, or behavioral evidence vs documented contract), then apply
the smallest safe fix, rerun the focused check, then the full gate:
`python -m coverage run --branch --source=ethscan -m pytest -q`;
`python -m mypy ethscan/ tests/`;
`python -m ruff check ethscan/ tests/ check_readme.py`; `python3 check_readme.py`.

Env note: `coverage` is not on PATH; use `python -m coverage ...`. `python` works here.