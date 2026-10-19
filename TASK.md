# TASK.md

Date: 2026-10-19T19:40:00Z
Status: an invalid CIDR is now a clean click usage error in the `cidr` and
`radix` commands, the translation lives in exactly one place, the library
modules are free of click, and a radix tree over mixed IPv4/IPv6 networks is
rejected instead of crashing.

## What changed (this session)
- `ethscan/cidr.py`: `_normalize_cidr` was promoted to the public
  `normalize_cidr`, with `_normalize_cidr` kept as an alias so existing
  callers keep working. The dedicated `CidrSpecError(ValueError)` (added in
  the previous session) is raised by it and therefore by `run_cidr`.
- `ethscan/radix.py`:
  - the duplicated `_normalize_cidr` was deleted; the module now uses
    `ethscan.cidr.normalize_cidr` (`_normalize_cidr` stays as an alias).
  - new `RadixSpecError(ValueError)`.
  - `_parse_networks` was promoted to the public `parse_cidrs` (old name kept
    as an alias). It now also rejects a list that mixes IPv4 and IPv6
    networks, because a radix tree is built over a single address family.
- `ethscan/cli.py`:
  - new `_invalid_cidr(exc, param)` and `_check_cidr(value, param)` (one
    value) plus `_check_cidrs(values, param)` (a list, which also rejects
    mixed address families). Both translate the library errors into a click
    usage error; `param` names the option the value came from.
  - the `cidr` command checks `--cidr` and `--diff`.
  - the `radix` command checks `--cidr-file`, `--cidrs` and `--diff`.
- `ethscan/validate.py`: the module docstring no longer claims the module
  reuses `parse_port_range` from `ethscan.scanner` (it does not). The
  docstring now states that the port specifications are parsed inline and why.
  The `validate` command's behaviour is unchanged.
- `README.md`: the Usage section documents the CIDR usage errors, the
  mixed-family rejection, and that `validate` keeps reporting invalid
  specifications inside its own output.
- `tests/test_cli.py` (+13): usage errors for `cidr --cidr`, `cidr --diff`,
  `radix --cidrs`, `radix --diff` and `radix --cidr-file`; the four
  invocations that used to dump a traceback; a single-line error; mixed
  families rejected; a diff in the other family still accepted; `--contains`
  still not an error; `validate` still reports inside its output; no
  calculation starts for a rejected value. The existing
  `test_library_modules_stay_free_of_click` guard now also covers
  `cidr.py` and `radix.py`.
- `tests/test_cidr.py` (+7) and `tests/test_radix.py` (+8): the new error
  types are `ValueError` subclasses, the parsers raise them, the private
  aliases point at the public functions, and a diff in the other address
  family is accepted.

## Verification
- Behavioural equivalence: a 243-invocation harness (valid and invalid CIDRs
  for `cidr` and `radix`, all three output formats, `--contains` values,
  `--cidr-file` inputs, mixed families, and the `validate` command) was
  captured before and after the change by stashing the work tree. **178 of
  243 invocations are byte-identical**; 62 are exactly the intended
  conversions (a raw traceback with exit code 1 became a one-line usage
  error with exit code 2); the remaining 3 differ only in the temporary
  file path recorded in argv (stdout and stderr are byte-identical). No
  stdout changed in any invocation. The `validate` command is byte-identical
  in all 8 of its invocations.
- Full suite: **4024 passed, 1 skipped** (baseline 3995 + 29 new). No
  regressions.
- Lint: `python -m ruff check ethscan tests --output-format concise` reports
  the same 48 pre-existing errors as the baseline (no new ones), verified by
  diffing the rule set against a `git stash`ed tree.
- Manual: all four previously-crashing invocations now print
  `Error: Invalid value for '--cidr'/'--cidrs'/'--diff': ...` and exit 2.

## Unresolved / deliberate non-changes
- The `validate` command still reports invalid specifications inside its
  JSON/CSV output with exit code 0. That is its documented contract.
- `radix` still cannot build a tree over mixed address families; it now
  rejects the input with a usage error instead of a `TypeError` traceback.
  Supporting both families in one tree would need a per-family tree and is
  out of scope.
- `ethscan/validate.py` still parses port specifications inline rather than
  reusing `parse_port_range`. Making the claim true would change the
  per-token error messages and the handling of empty tokens, and therefore
  the `validate` output contract, so the docstring was corrected instead.
- The 48 pre-existing ruff errors are unrelated to this work and were
  deliberately left alone.

## Next
See `HANDOFF_NEXT.md` / `NEXT_TASK.md` for the remaining follow-up task.
