# Task
Date: Sat Nov 07 2026

## Current state
- Baseline at session start: green (5910 passed, 50 skipped; ruff/mypy clean; working tree clean).
- `ethscan` importable; pytest 9.2.0, ruff 0.17.4, mypy 2.4.1.

## This session
- **Reproduced gap:** `ethscan completion bash` (default) emitted a JSON report (`{"shell","prog_name","script"}`) instead of the raw completion script, so the documented/expected usage `ethscan completion bash > ~/.ethscan_complete.bash` produced a file that is not a sourceable shell script (`source` fails with `shell::/prog_name::/script:: command not found`). Confirmed at CLI and with `bash -n`/`source` on redirected output; the JSON wrapper itself happened to pass `bash -n` in this environment but is not valid completion script content.
- **Fix (ethscan/cli.py `completion`):** default stdout/`--out` output is now the raw completion script (suitable for redirecting/sourcing). A structured report (JSON/Markdown/CSV) is emitted only when explicitly requested via `--output-format` or the deprecated `--format` alias (detected with Click `ParameterSource`, consistent with existing `--timeout/--workers` handling). `--out` now writes the chosen form (raw by default). Help text updated to document default vs. structured modes.
- **Tests updated/added:** adjusted completion tests in `tests/test_cli.py` and `tests/test_completion.py` to match the corrected contract (default raw; explicit report modes; `--out` raw vs report; custom prog-name raw/report). Fixed `_run_completion_cli` return annotation in `tests/test_completion.py` (`Result`, not `CliRunner`).
- **Docs:** README completion bullet updated to state raw default + redirect example and optional structured output.

## Verified
- Repro before fix: `completion bash > file` → JSON wrapper, not sourceable (`source` errors on `shell:/prog_name:/script:`); after fix: raw script, `bash -n` ok, `source` rc 0; `--prog-name` respected in raw output.
- `python3 -m pytest tests/test_completion.py tests/test_cli.py -q` → 1103 passed (includes 17 completion-related CLI cases).
- `python3 -m pytest tests/test_completion.py -q` → 46 passed.
- `python3 -m ruff check ethscan/cli.py ethscan/completion.py tests/test_completion.py tests/test_cli.py` → clean.
- `python3 -m mypy ethscan/cli.py ethscan/completion.py` → Success.
- Structured modes preserved: `--output-format {json,markdown,csv}` and deprecated `--format` produce reports; `--out` + format writes report; `--out` default writes raw script. Full 5910-test suite not rerun this session (targeted coverage passed).

## Blockers
- None demonstrated.

## Next task
- Run the full test suite (`python -m pytest -q`) to confirm no regressions outside the completion/CLI targeted scope, then address any failure with a minimal, evidence-based fix (reproduce, targeted verify, ruff+mypy). If the full suite is green, select another bounded, high-value robustness/correctness task implementable and verifiable in one session (reproduce any claimed gap before changing code). Do not commit unless asked. Update TASK.md/NEXT_TASK.md/HANDOFF_NEXT.md.
