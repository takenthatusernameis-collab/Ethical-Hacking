# Next Task

## Task
Normalize empty/invalid target handling for `mongodb` (one module) to match the established CLI usage-error pattern.

## Scope
- Reproduce: `python -m ethscan mongodb --target ""`, `"   "`, `"https://"` currently exit 0 and emit JSON with `host: null` and `error: "Could not parse host from target ..."` rather than `click.UsageError` (exit 2).
- Inspect `ethscan/mongodb.py` `_normalize_target`/`run_mongodb` and CLI wiring. If empty-host is detected but swallowed into result data, change to raise `TargetSpecError` so CLI reports `Error: Invalid value for '--target': ...` with exit 2 (consistent with ping/osdetect/vuln/ssh/brute/cve/tls/ssl/s3/fuzz/web/cert/mysql).
- Add/adjust unit tests (empty/whitespace/URL-without-host rejection) and CLI invalid-target test(s) for `mongodb`. Update only tests that asserted the old buggy in-band behavior, with evidence.
- Keep valid-target behavior unchanged.

## Verification
1. Before/after repro for `mongodb --target ""|"   "|"https://"`.
2. `python -m mypy ethscan/ tests/`
3. `python -m ruff check ethscan/ tests/`
4. Targeted pytest for mongodb + CLI mongodb cases, then full `python -m pytest -q`.

## Constraints
- Smallest reversible change; do not batch mssql/oracle/postgresql in same session unless mongodb fix is trivial and fully verified.
- Do not weaken validation/safety; preserve existing output schema for valid targets.
- Record exact counts and any tests changed due to prior buggy expectations in handoff.
