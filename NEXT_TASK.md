# Next Task

## Status
Session 125 verified the `snmp` findings hardening at HEAD: `_normalize_findings` is applied in both `format_snmp_report_markdown` and `format_snmp_report_csv`, and `tests/test_snmp_formatter_hostile_sweep.py` covers non-iterable/hostile shapes. Full suite green: 6411 passed, 53 skipped, 0 failed; mypy/ruff clean (194 source files).

## One precise next task
None pending. Repository is fully green. If future work is needed, pick a single bounded, high-value, verifiable improvement and reproduce it first — do not speculate or weaken safety controls. `oracle`/`postgresql` empty-target handling remains intentionally out of scope per their documented contract (exit 0, in-band error).

(End of file)
