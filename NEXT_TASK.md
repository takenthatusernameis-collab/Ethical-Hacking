# Next Task

No code change is required this session: the ethscan toolkit is complete and fully verified
(5461 passed, 50 skipped; ruff clean; mypy clean; the `ethscan` console script installs and
honors the exit-2 usage-error contract for `radix`/`stale` with no input).

The one remaining item is the cross-platform CI workflow, which is blocked on infrastructure,
not a code defect:

- Obtain a PAT/token with `workflows` write permission for this repository.
- Create `.github/workflows/test.yml` running pytest, `ruff check .`, and `mypy ethscan/`
  on ubuntu-latest, macos-latest, and windows-latest.
- Trigger it via `workflow_dispatch` and confirm the `test` job passes on all three platforms.
- If a token cannot be obtained, leave this as a documented infrastructure blocker. `act` is
  not available in this environment, so the matrix cannot be validated locally here.

(End of file)
