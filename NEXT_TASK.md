# NEXT_TASK.md

## Status (2026-10-19T17:05:00Z)
- Prior agent task (invalid `--ports` -> click usage error): **complete**. The
  production code was already in `c7cbe2a`; this session added the missing
  tests, consolidated the eight duplicated `try/except` blocks in
  `ethscan/cli.py` into one `_resolve_ports` helper, removed the `click`
  dependency from `ethscan/report.py`, and added a dedicated `PortSpecError`
  to `ethscan/scanner.py`.
- Verified: 240/240 CLI invocations byte-identical before and after the
  refactor; unit-level keyword harness 0 mismatches; full suite 3995
  passed/1 skipped; ruff output byte-identical to the baseline (48 errors).

## Next task (bounded, high-value)
Invalid CIDR input still crashes with a raw Python traceback instead of a
clean CLI error. Convert it into a proper click usage error for the `cidr`
and `radix` commands.

Evidence (reproduced on `main` at this commit):
```
$ python -m ethscan cidr --cidr bogus
ValueError: 'bogus/128' does not appear to be an IPv4 or IPv6 network   # traceback, exit 1
$ python -m ethscan cidr --cidr 192.168.1.0/24 --diff bogus
ValueError: 'bogus/128' does not appear to be an IPv4 or IPv6 network   # traceback, exit 1
$ python -m ethscan radix --cidrs bogus
ValueError: 'bogus/128' does not appear to be an IPv4 or IPv6 network   # traceback, exit 1
$ python -m ethscan radix --cidrs 192.168.1.0/24 --diff bogus
ValueError: 'bogus/128' does not appear to be an IPv4 or IPv6 network   # traceback, exit 1
```
All four exit 1 and dump a traceback; a click `BadParameter` should give exit
code 2 and a one-line message such as
`Error: Invalid value for '--cidr': 'bogus/128' does not appear to be an IPv4 or IPv6 network`.

Implementation notes:
- Follow the pattern established this session: a dedicated error type that
  subclasses `ValueError` (so library callers keep working), raised by the
  parsing helper, translated to `click.BadParameter` **only** in
  `ethscan/cli.py`.
  - `ethscan/cidr.py:16` `_normalize_cidr` raises `ValueError("Empty CIDR
    value")` and lets `ipaddress.ip_network` raise `ValueError`.
  - `ethscan/radix.py:15` `_normalize_cidr` is a near-identical duplicate of
    the `cidr.py` one; `ethscan/radix.py:34` `_parse_networks` and
    `ethscan/radix.py:39` raise `ValueError` for a bad entry.
  - `ethscan/cidr.py:147` (`run_cidr`) and `ethscan/cidr.py:165` (the
    `--diff` branch) are the `cidr` call sites; `ethscan/radix.py:312`
    (`run_radix`) and `ethscan/radix.py:352` (the `--diff` branch) are the
    `radix` ones.
  - `ethscan/cidr.py` and `ethscan/radix.py` are stdlib-only leaf modules with
    no `ethscan` imports, so consolidating the two copies of `_normalize_cidr`
    (one importing the other, or a small shared helper) introduces no import
    cycle.
- Do **not** change the `ethscan validate` command: it intentionally reports
  invalid CIDR specs inside its JSON/CSV output (exit code 0), not as a usage
  error. `ethscan/validate.py` has its own `_validate_cidr` and must keep
  that contract.
- Do **not** change `--contains`: `cidr --contains bogus` and
  `radix --contains bogus` legitimately answer "not a member" (exit code 0)
  and are not errors.
- The `ethscan/validate.py` module docstring claims it "reuses
  `parse_port_range` from `ethscan.scanner`", but it actually re-implements
  the parsing inline with slightly different messages (e.g. "Port out of range
  (0-65535)" vs the scanner's "Port out of range (0-65535) in range '...'",
  and empty tokens are skipped instead of being an error). Either fix the
  docstring or make the claim true — decide explicitly and note the choice.

Verification: `python -m pytest tests/test_cli.py tests/test_cidr.py tests/test_radix.py -q`
plus new tests asserting exit code 2, an
`Error: Invalid value for '--cidr'/'--cidrs'/'--diff'` message, and the absence
of a traceback for each of the four failing invocations; `ruff check ethscan tests`
must stay at 48 pre-existing errors with no new ones.
