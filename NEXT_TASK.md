# Next Task for Next Agent

## Current state
- All 54 commands implemented, registered in CLI, and documented in README with detailed per-command bullets.
- IPv6 target parsing fixed across protocol modules; tests cover IPv6 cases including URL forms.
- All non-DNS protocol tests pass. Full suite: **2808 passed, 3 failed** (pre-existing environmental DNS test failures due to dnspython availability in test environment - not regressions).
- Repository is stable; working tree clean aside from handoff/task documentation from previous sessions.

## Suggested bounded next task (optional)
Pick exactly one small, verifiable improvement. Good candidates:
- Add consistency tests for IPv6 URL normalization on any protocol module missing the combined form (e.g. test that covers both bare `[::1]:port` and `scheme://[::1]:port` together where not present). Keep changes minimal.
- Add minor input validation/edge case coverage in a specific module with low risk.
- Small README/formatting consistency tweak if any minor discrepancy found.

Do not expand scope to infrastructure changes. If no obvious gap exists, record that state is complete and exit with a clear handoff.

## Constraints
- Preserve working baseline. Only make reversible, minimal changes.
- Do not "fix" the 3 pre-existing DNS environmental test failures unless you can do so without changing their intended semantics in a way that breaks other behavior.
- Run focused tests for any modified code; run broader suite only if necessary.
- End with a detailed handoff per the reliability rules.
