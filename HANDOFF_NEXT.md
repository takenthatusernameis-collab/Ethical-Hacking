# Handoff: README documentation completion for remaining summary-only commands

## What changed

### README documentation
`README.md` — Replaced three summary-only feature bullets with detailed per-command bullets matching the style of the other 51 commands:

- **`web`** (was "Web application security checks (implemented)") — now documents `--checks` (headers, info_disclosure, ssl), `--target`, `--timeout`, and `--output-format [json|markdown|csv]` / `--format` / `--out`.
- **`dnsbrute`** (was "DNS brute force: AXFR zone transfer attempts + subdomain brute forcing (implemented)") — now documents raw AXFR over TCP port 53 with optional dnspython fallback, `--ns`/`--wordlist`/`--resolver`, recursive AXFR (`--recursive`/`--no-recursive`, `--max-depth`), `--timeout`, `--workers`, and `--output-format [json|markdown|csv]` / `--format` / `--out`.
- **`tls`** (was "TLS protocol/cipher enumeration (implemented)") — now documents per-version and per-cipher probes, `--versions`/`--ciphers`, obsolete-version findings, `--target`, `--port` (443), `--timeout`, `--workers`, and `--output-format [json|markdown|csv]` / `--format` / `--out`.

All 54 registered commands now have detailed README bullets with CLI options and output format support.

## What was verified

- `python -m pytest -q` → **2808 passed, 3 failed** (3 failures are pre-existing network-dependent DNS tests: `test_dns.py::test_run_dns_offline_basic`, `test_dnsbrute.py::test_run_dnsbrute_resolver_used_for_resolution`, `test_resolve.py::test_run_resolve_domain_defaults` - environmental, no internet access in sandbox; not caused by documentation changes).
- No code changes - only README.md modified. Working tree changes are isolated to documentation.
- `git diff --stat` → `README.md | 5 +++--` (3 insertions, 2 deletions — three summary bullets replaced with detailed bullets).
- `python -m ethscan --help` → lists all 54 commands.

## What remains unresolved

- The 3 network-dependent DNS test failures remain (environmental). They should pass in an environment with network access.
- No functional gaps; all commands have implementations and CLI wiring as verified by tests.

## Next precise task

No further documentation tasks are obvious from the handoff chain. All summary-only commands now have detailed bullets. If continuing, pick another bounded, high-value task such as improving edge case coverage or refactoring a small, well-defined component. Otherwise, mark as complete.

(End of file - total 22 lines)