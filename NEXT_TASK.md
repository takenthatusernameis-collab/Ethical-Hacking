# NEXT TASK

## Status: COMPLETE

### Previously assigned task: `cve` and `osdetect` bad-document crashes
**Done — already committed in the baseline (`8b4da94`, HEAD).**
- `cve --services-file` with `{"results": [{"port": 22, "banner": 5}]}` -> exit 0, notes name the problem,
  no traceback (`ethscan/cve.py:344-365`).
- `osdetect --banners-file` with `{"results": "abc"}` -> exit 0, note
  `Banners data holds no 'results' list` (`ethscan/cli.py:2310-2341`).
- Covered by 3 checks in `tests/test_cli_aggregator_unreachable_sweep.py`; verified at the command line
  and by the test suite (12 passed in that file).

### The six commands `TASK.md` listed as unresolved: already fixed
The older `TASK.md` said `ping`, `osdetect`, `resolve`, `dns`, `stale` and
`subdomains` still let a transport failure of an unnamed type escape. Direct
inspection of the source shows every site it named is now inside an
`except Exception` block that returns the module's documented error signal, and
each has a module-level regression test plus a hostile-transport sweep check:

- `ping` — `ethscan/ping.py:174-180`, `:187-197`, `:235-245`, `:248-263`, `:264-279`;
  hostile `socket.socket` -> `RESP_NO_RESPONSE` with the error string.
- `osdetect` — `ethscan/osdetect.py:132`; hostile `socket.create_connection` ->
  `NO-RESPONSE` probe.
- `resolve` — `ethscan/resolve.py:67`, `:82`, `:102`, `:117`; hostile
  `socket.getaddrinfo` -> `[]`.
- `dns` — `ethscan/dns.py:65`, `:88`, `:115`; hostile `socket.getaddrinfo` -> `[]`.
- `stale` — `ethscan/stale.py:55`, `:70`, `:87`; hostile `socket.getaddrinfo` ->
  domain reported stale.
- `subdomains` — `ethscan/subdomains.py:106`, `:116`; hostile
  `socket.gethostbyname` -> unresolved.

### This session: verification only, no source changes
`git status` is clean and `git diff --stat` is empty. The work was confirming the
state rather than making it.

### What was actually verified
- `python -m ruff check ethscan/ tests/` -> **All checks passed**.
- `python -m pytest tests/` -> **5158 passed, 48 skipped, 3 warnings** (pre-existing `test_main.py` runpy
  warnings).
- `ethscan/cli.py` declares exactly 53 `@cli.command()` decorators; the permanent
  cross-reference in `tests/test_cli_sweep_coverage.py:43` confirms 53/53 are
  named in a CLI sweep file, and that check passes.

### What remains unresolved

- **None.** The CLI failure-field coverage task is complete: all 53 CLI commands now have a
  permanent CLI-level failure-field check. The 10 commands that do not open a transport of their
  own are covered by `tests/test_cli_offline_sweep.py` and `tests/test_cli_offline_input_sweep.py`;
  the other 43 are covered by the four transport sweep files. A cross-reference of every
  `@cli.command()` against the sweep files confirms 53/53 covered.
- `python ethscan/cli.py` cannot work in this layout (pre-existing); use `python -m ethscan.cli`.

### Constraints

- Smallest reversible change; do not weaken an existing guard; turn the crash into the module's
  documented error signal.
- Keep the permanent sweeps in the repository, and prove every new check by reverting the guard of
  its own module.
- Do not commit unless explicitly asked.

### One precise next task

- **No outstanding task from this handoff.** The CLI failure-field coverage work is done and
  verified (`python -m pytest tests/` -> 5158 passed, 48 skipped; `python -m ruff check ethscan/
  tests/` -> all checks passed). Do not re-add checks that already exist.

(End of file - total 59 lines)