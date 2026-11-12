# Next Task

## Status
Session 117 hardened the six findings-joining CSV formatters (`mysql`, `memcached`, `mongodb`, `mssql`, `postgresql`, `redis`) to stringify each element before joining, fixing a `TypeError` on non-string findings (`None`/`int`/nested). Markdown formatters already tolerated the same data. `pytest` 6166 passed (+30), `mypy` clean (189 files), `ruff` clean. New test: `tests/test_findings_csv_hostile_sweep.py`.

## One precise next task
Harden the same six formatters against a non-iterable list field. A dict like `{"findings": 1}` (or `{"dangerous_findings": 1}` for redis) still raises `TypeError: 'int' object is not iterable` in both the Markdown and CSV formatters, because `data.get("findings") or []` yields the truthy scalar and the code iterates it. Reproduce with a temporary fuzzer over the public `format_*` functions, guard the extraction (coerce a non-list/tuple value to `[]`), and extend `tests/test_findings_csv_hostile_sweep.py` with the non-iterable shape. Keep the change minimal and preserve valid-output behavior.

## Notes
- Keep README examples evidence-based; do not invent outputs.
- Do not weaken CLI validation or tests. Preserve oracle/postgresql in-band exit-0 contract vs usage-error exits elsewhere.
- `oracle` and `postgresql` empty-target handling remains intentionally out of scope per their documented contract (exit 0, in-band error).
- Broader formatter hostile-shape gaps exist beyond this task (see TASK.md session 117 "Approaches already tried"); pick them one bounded family at a time.

(End of file)