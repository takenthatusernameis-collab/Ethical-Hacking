# Next Task
Continue evidence-driven permanent-test coverage only for demonstrated gaps that lack a permanent check.

Done in recent sessions (verified, present in working tree/history): formatter hostile-shape sweep for every module with `format_*_report_markdown`/`format_*_report_csv`; protocol hostile-answer sweep (`tests/test_protocol_hostile_sweep.py`); cache content sweep (`tests/test_cache_content_sweep.py`); CLI unreachable sweeps; offline command sweeps; file-option / file-content / option / config-value sweeps; CLI sweep coverage (`tests/test_cli_sweep_coverage.py`); int-option range sweep (`tests/test_cli.py` `INT_OPTION_RANGES` + `test_every_int_option_of_the_cli_is_range_checked`).

This session closed the last permanent-test gap found: the 17 `--workers` options of the CLI are `click.IntRange(1, None)` but were not named in `INT_OPTION_RANGES`, so the int-option range sweep did not cover them. Added the 17 entries and `test_an_out_of_range_workers_option_does_not_start_a_probe`. No source change was needed — the options already refuse out-of-range values (verified: `--workers 0` exits 2 with a clean single-line usage error on all 17 commands and never starts a probe).

Constraints:
- Preserve baseline; smallest reversible change.
- Add guards/tests only for demonstrated real gaps (no transport/body/JSON parsing duplication).
- Verify: targeted pytest for new/affected tests, then full `python3 -m pytest -q`, `python3 -m ruff check .`, `python3 -m mypy ethscan`.
- Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`; do not commit unless explicitly asked.

Known pre-existing failures (do not confuse with regressions; unrelated to this sweep): none remaining.

(End of file - total 16 lines)