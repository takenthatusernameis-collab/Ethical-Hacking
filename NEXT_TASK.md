# Next Task

## Status: one bounded follow-up available; repo otherwise green with fresh evidence.

This session fixed a real silent-wrong-result bug (UDP scan of IPv6 targets reported live services as closed) and verified the full gate green. Working tree has the completed, uncommitted fix at HEAD `683d33e`.

## Verification (fresh evidence, this session)
- `python -m pytest -q` -> **46770 passed, 147 skipped, 0 failed** (baseline 46767; +3 new tests).
- `python -m mypy ethscan/ tests/` -> Success, no issues in 268 source files.
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed.
- `python3 check_readme.py` -> 54 commands, 0 drift both directions.
- Full-suite branch coverage -> `ethscan/scanner.py` 100%; TOTAL 100% (16119 stmts, 6080 branches, 0 miss).
- `git diff --check` -> clean; `git status` -> only `ethscan/scanner.py` + `tests/test_scanner.py` modified.

## Next task (precise, evidence-based)
Add an end-to-end CLI regression test that `ethscan scan --target ::1 --protocol udp` reports a live IPv6 UDP service as open.
- Why: this session's reproduction showed CLI `open_ports: []` before the fix and `open_ports: [<port>]` after; `tests/test_scanner.py` covers `scan_udp_port` directly (unit + loopback), but `tests/test_cli.py`'s UDP tests monkeypatch `scan_udp_ports` and never exercise a real IPv6 transport. A CLI-level test locks the fix at the user-facing layer.
- How: mirror `tests/test_scanner.py::test_scan_udp_port_ipv6_loopback_open_is_detected` through the CLI (bind a `::1` UDP echo server on an ephemeral port, run the `scan` command via `CliRunner` or `subprocess` with `--protocol udp --ports <port>`, assert exit 0 and the port listed in `open_ports`/`details` with `"open": true`). Skip when `not socket.has_ipv6` or when bind raises `OSError`.
- Constraints: keep it deterministic and skip-guarded; no new dependencies; re-run the full gate (pytest/mypy/ruff/check_readme/coverage) afterwards and record results.

## Do not re-implement / do not "fix" (already done / intended)
- `ethscan/cli.py:4318` unreachable defensive guard — documented known limitation; leave it (removing would weaken validation; `# pragma: no cover` would game the metric).
- `oracle`/`postgresql` empty-target handling — intentionally in-band (exit 0) per documented contract; out of scope.
- The remaining `AF_INET` occurrences in `resolve.py`/`dns.py`/`stale.py`/`subtake.py` are `getaddrinfo` name-resolution hints (intentionally IPv4), not sockets; not a bug.
- Do not count control-marker-only (handoff-doc) commits as project progress.

## Next session guidance
1. Run fast gates first: `ruff`, `mypy ethscan/ tests/`, `check_readme.py`. If green, run `python -m pytest -q` once, then coverage; if green, proceed with the CLI regression test above.
2. Only select new work if a genuine gap is REPRODUCED first (reproduce before changing). Do not fabricate work.