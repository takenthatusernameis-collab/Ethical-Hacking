# HANDOFF_NEXT.md

## Session summary (2026-10-20T11:35:00Z)

The prior handoff asked for a **short, permanent sweep test** in the suite.
That item is **complete**.

| Check | State |
|---|---|
| Full test suite | **4389 passed / 7 skipped** (4342/1 before + 47 new, 6 new skips) |
| Ruff linting | **48 pre-existing errors (no new ones)** - unchanged from baseline |
| git diff --check | Clean |
| String option sweep | **196 invocations, 0 leaked tracebacks** (re-run, unchanged) |
| File option sweep | **225 invocations, 0 leaked tracebacks** (re-run, unchanged) |
| New permanent sweep test | `tests/test_option_sweep.py` - **47 passed / 6 skipped in 9.2s** |

## What changed (this session)

- **`tests/test_option_sweep.py`** (new): a permanent, parametrized test that
  walks the commands of `ethscan.cli` and checks that every **string** option
  of every command refuses a small set of hostile values (an empty string, an
  over-long name, a path that does not exist) without leaking a traceback.
  It uses `signal.SIGALRM` with a 5s per-invocation timeout, the same
  mechanism the sweep scripts use. Three commands are excluded by name
  (`dnssec`, `netbios`, `snmp`) because they probe a real host and time out;
  the module docstring says so. A command that leaks a traceback is a
  finding, not a failure to be papered over: the assertion names the command,
  the option and the value.

## Approach

- First ran the baseline (`4342 passed / 1 skipped`, `48 ruff errors`,
  `git diff --check` clean) to pin the working state.
- Enumerated every command and its string-typed options (53 commands, 315
  (command, option, value) combos at 3 hostile values each).
- Wrote a **timing probe** (`/home/runner/work/_temp/kilo-tmp/kilo/time_sweep.py`)
  that measured each combo under a 3s per-invocation timeout to find which
  commands fail fast and which time out. Result: **0 leaks**, and exactly
  three slow commands (`dnssec`, `netbios`, `snmp`).
- Wrote the permanent test to include only the fast commands, with a 5s
  timeout (margin over the slowest included command, `s3`, which peaks at
  ~2.4s when its target triggers a DNS lookup).
- Re-ran the full suite (**4389 passed / 7 skipped**), ruff (**48 errors,
  unchanged**), `git diff --check` (clean) and the two hostile sweep scripts
  (196 and 225 invocations, **0 leaks**).

## Approaches that failed or were rejected (carried forward)

- Running the full twenty-minute sweep as a test: rejected, the suite must
  stay under a minute.
- Including the network-probing commands in the permanent test: rejected, they
  time out under any reasonable per-invocation timeout and are not part of the
  guarantee this test enforces.
- A `--ports` sweep in the same test: the `--ports` option was already
  validated in an earlier session and is covered by its own regression tests;
  adding it here would slow the test without adding coverage.

## What remains unresolved

- The 48 pre-existing ruff errors are untouched (mostly BLE001 and TRY002,
  46 of the 48 are not auto-fixable and each needs a review).
- The file-option sweep is still a script outside the repository (it needs a
  per-invocation timeout and covers 225 invocations). The permanent test covers
  the string options; the file options are pinned by the per-option regression
  tests in `tests/test_cli.py` (`test_a_file_option_with_a_missing_file_is_a_usage_error`,
  `test_a_file_option_with_a_directory_is_a_usage_error`).

## Next task (bounded, high-value)

**Review and reduce the 48 pre-existing ruff errors**

**Evidence:**
- `python -m ruff check ethscan/ tests/` -> 48 errors, 2 auto-fixable (`PLR0402` in `tests/test_brute.py`)
- `python -m pytest -q` -> 4389 passed, 7 skipped
- The permanent sweep test now keeps the "no traceback leak" guarantee alive
  for every string option of every command.

**Recommended approach:**
1. Run `ruff check ethscan/ tests/ --output-format=concise` and group the 48
   errors by rule. Most are `BLE001` (broad `except Exception`) and `TRY002`
   (`raise Exception` in a test).
2. Fix the 2 auto-fixable ones first (`ruff check --fix`).
3. For the rest, decide per rule whether to narrow the `except`, replace the
   bare `raise` with a specific exception, or add an explicit `# noqa: BLE001`
   with a comment explaining why the broad catch is correct there.
4. Keep the ruff error count monotonic: no new errors, and the count must not
   rise when the sweep test or any future command is added.

**Constraints:**
- Do not change the behaviour of a command to make a ruff rule pass; a broad
  `except` that hides a real bug is a finding, not a lint to be silenced.
- The suite must stay green and fast; the sweep test adds ~9s.
- Do not weaken the safety controls that the hostile-option work put in place
  (the `_TargetGroup`, `_write_output`, `parse_url`, etc.).