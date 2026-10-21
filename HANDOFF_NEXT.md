# HANDOFF: state for the next agent

## What changed this session

The task of the previous handoff (extend the permanent CLI-level sweep to
`trace` and `brute`) had already been committed by the session before this
one (commit `119cc6e`, together with the fix of `ethscan/brute.py:110`). The
session after that one (commit `1c5d930`) added a `run_brute` wrapper to
`ethscan/cli.py` **below** the `__main__` guard and broke the
`python -m ethscan.cli` entry point. This session fixed that regression,
closed the gaps the previous sweep left open, and removed two sources of
flakiness from the permanent test suite.

Nothing was committed by this session: the work is in the worktree, the
controller makes the checkpoint commit.

### Source (`ethscan/`)

- `cli.py`: the `run_brute` wrapper was defined **after**
  `if __name__ == "__main__": cli()`. The guard runs the CLI while the module
  body is still executing, so `run_brute` was not bound yet and
  `python -m ethscan.cli brute ...` died with
  `NameError: name 'run_brute' is not defined` (exit 1, no report). The
  wrapper is now defined above the guard, next to the imports.
- `brute.py`: `_attempt_ssh` built the paramiko client **outside** the
  guarded block (the same defect the FTP path had until commit `119cc6e`).
  A failing `paramiko.SSHClient()` escaped the command as a bare
  `RuntimeError`. The client is now built inside the `try:`.
- `ping.py`: two guards were too narrow.
  - `probe_icmp` caught only `socket.gaierror` around `connect_ex`; a
    transport that fails with any other type escaped the command. It now
    catches `(OSError, RuntimeError)`, like the other guards of the module.
  - `_resolve_host` caught only `(socket.gaierror, socket.herror, ValueError)`.
- `cert.py`, `geo.py`, `mac.py`: their `_resolve_host` helpers caught only
  `(socket.gaierror, socket.herror, ValueError)`, so a resolver that fails
  with any other error type escaped the command. They now catch the same set
  as `ethscan/dns.py` and `ethscan/resolve.py`:
  `(socket.timeout, socket.gaierror, socket.herror, OSError, ValueError,
  RuntimeError)`.

### Tests (`tests/`)

- `test_main.py` (4 new checks): the `__main__` guard must be the last
  statement of `ethscan/cli.py`, `ethscan/main.py` and
  `ethscan/__main__.py` (a static invariant that catches the whole class of
  "defined below the guard" defects), and the `brute` command must run when
  `ethscan/cli.py` is executed as `__main__` (the regression itself).
- `test_cli_trace_brute_unreachable_sweep.py` (3 -> 6 checks): rewritten in
  the conventions of `test_cli_http_unreachable_sweep.py` and extended:
  - the FTP client that cannot be **constructed** (locks in the fix of
    commit `119cc6e`, which had no permanent check);
  - the SSH login that fails and the SSH client that cannot be constructed
    (the SSH branch of the command had no check at all; paramiko is not
    installed here, so a stand-in module is used).
- `conftest.py` (new): the `no_external_network` fixture, shared by the two
  option sweeps.
- `test_option_sweep.py`, `test_file_option_sweep.py`: use the fixture. The
  `cert` command fetches certificate transparency data from `crt.sh` and the
  `whois` command talks to a whois server; both made the sweeps depend on
  the latency of the internet and tripped their own five second alarm.
- `test_cert.py`, `test_geo.py`, `test_mac.py`, `test_ping.py` (5 new
  checks): a resolver that fails with an unknown error type is a failed
  lookup, not a raise.

## What was actually verified

- **The regression was reproduced before the fix**:
  `python -m ethscan.cli brute --target 127.0.0.1 --user-file u.txt
  --pass-file p.txt` exited 1 with
  `NameError: name 'run_brute' is not defined`. After the fix the same
  command prints its JSON report and exits 0.

- **The new checks are meaningful.** Every check was proved by reverting the
  guard of its own module and watching the check fail:

  | check                                                | mutation                                                     |
  |------------------------------------------------------|--------------------------------------------------------------|
  | `test_main_guard_is_the_last_statement_of_the_module` | the `run_brute` wrapper moved back below the guard          |
  | `test_cli_module_as_main_runs_the_brute_command`      | the `run_brute` wrapper moved back below the guard          |
  | `test_trace_cli_reports_a_failed_name_lookup`          | `except Exception` -> `except ValueError` (trace)            |
  | `test_trace_cli_reports_a_failed_socket`               | `except Exception` -> `except ValueError` (trace)            |
  | `test_brute_cli_reports_a_failed_login`                | `except Exception` -> `except ValueError` (brute)            |
  | `test_brute_cli_reports_an_unbuildable_client`         | `ftp = FTP()` moved out of the `try:` (brute)                |
  | `test_brute_cli_reports_a_failed_ssh_login`            | `except Exception` -> `except ValueError` (brute)            |
  | `test_brute_cli_reports_an_unbuildable_ssh_client`     | `client = paramiko.SSHClient()` moved out of the `try:`      |
  | `test_ping_connect_failure_of_an_unknown_type_is_reported` | `except (OSError, RuntimeError)` -> `except socket.gaierror` |
  | `test_cert/test_geo/test_mac/test_ping` resolver checks | the `_resolve_host` guard narrowed back                      |

  With the guards restored, all of them pass.

- **The four resolver guards were measured at the command line.** With
  `socket.gethostbyname` and `socket.getaddrinfo` raising a plain
  `OSError("hostile resolver")`:

  | command | before this session | after this session |
  |---------|---------------------|--------------------|
  | `cert`  | exit 1, traceback    | exit 0, report     |
  | `geo`   | exit 1, traceback    | exit 0, report     |
  | `mac`   | exit 1, traceback    | exit 0, report     |
  | `ping`  | exit 1, traceback    | exit 0, report     |
  | `dns`, `resolve`, `stale`, `subdomains`, `subtake`, `s3`, `trace`, `whois`, `web` | exit 0 | exit 0 |

- **The new checks are hermetic.** `test_cli_trace_brute_unreachable_sweep.py`
  and `test_main.py` were run with the network blocked (a plugin that raises
  on every connection and on every name lookup that is not a numeric
  address): **20 passed**. The plugin was used for the proof only and is not
  part of the repository.

- **The option sweeps are hermetic now.** They are run with the
  `no_external_network` fixture: the HTTP transport and the resolution of a
  name that is not a numeric address fail at once, while connections to a
  numeric address stay untouched. Both sweeps were run three times in a row:
  97 passed, 9 skipped, every time.

- `python -m ruff check ethscan/ tests/` -> **All checks passed**.
- `python -m pytest tests/` -> **5097 passed, 48 skipped, 3 warnings** (the
  baseline at the start of the session was 5085 passed, 48 skipped, 2
  warnings; the +12 are the new checks, the third warning is the new runpy
  check in `test_main.py`, of the same kind as the two pre-existing ones).
  The suite was run twice in a row with the same result.
- `git diff --check` -> clean. Nothing is committed.

## What remains unresolved

- **The CLI level still has no failure-field check for the three
  aggregators** `vuln`, `recon` and `report` (40 of the 53 commands have a
  permanent CLI-level check: 28 in `test_cli_unreachable_sweep.py`, 10 in
  `test_cli_http_unreachable_sweep.py`, 2 in
  `test_cli_trace_brute_unreachable_sweep.py`). The modules behind them are
  covered one level down.
- **`socket.setdefaulttimeout()` is a process-wide side effect.** The
  resolution helpers of `ethscan/dns.py`, `ethscan/resolve.py`,
  `ethscan/stale.py`, `ethscan/subtake.py` and `ethscan/s3.py` set the
  default timeout of the process. The CLI sweeps restore it after every
  check; the other test files do not, so a later test inherits a 2s default
  socket timeout.
- **`python ethscan/cli.py` does not work and cannot work in this layout**
  (pre-existing, not a regression): the script's own directory is
  `sys.path[0]`, so `from ethscan import __version__` fails with
  `ModuleNotFoundError`. `python -m ethscan.cli` is the working form of that
  entry point and it works again after the fix of this session.
- **The `vuln`, `recon` and `report` commands were not probed at the command
  line in this session** (only their modules were covered one level down
  before), so a crash path of the aggregators themselves would still be
  invisible to the permanent sweeps.

## Approaches that failed and why

- **The first version of the hermetic fixture raised a plain `OSError` from
  the name resolution.** The string-option sweep then failed for `cert`,
  `geo`, `mac` and `ping`, because a plain `OSError` is not the failure a
  resolver produces: the real failure of a name lookup is a
  `socket.gaierror`. The fixture now raises `socket.gaierror`, which is what
  the modules already handle, and the four resolver guards were fixed
  separately with the guard they were missing.
- **The first version of the fixture recursed into itself.** The guarded
  resolver called `socket.getaddrinfo`, which was the patched function, and
  every command died with `RecursionError`. The originals are now kept at
  module level in `tests/conftest.py`.
- **The first version of the ping guard caught only `OSError`.** The
  project's hostile transport is a `RuntimeError` (see the other regression
  tests), which is not an `OSError`, so the check failed. The guard catches
  `(OSError, RuntimeError)` now, like the other guards of the module.
- **`socket.gaierror` derives from `OSError`.** Narrowing a guard to
  `except socket.gaierror` therefore changes nothing for a `gaierror`; the
  mutation has to drop `OSError` (or raise a different type) to prove
  anything. This trap applies to every guard of this repository.
- **A check that fails while another process mutates the sources is not
  evidence.** The mutation runs and the test runs have to be sequential.

## One precise next task

Extend the permanent CLI-level sweep to the last three commands that open a
transport of their own without a failure-field check at the command line:
the aggregators `vuln`, `recon` and `report`.

The method is the one of `tests/test_cli_unreachable_sweep.py`,
`tests/test_cli_http_unreachable_sweep.py` and
`tests/test_cli_trace_brute_unreachable_sweep.py`: patch the transport the
command really opens, run the command through `CliRunner`, and assert that
it exits 0, leaks no traceback and prints the command's own failure signal.

What is already known about the three commands:

- `vuln` (`--target`, optional `--services-file`, `--tls-file`,
  `--ssl-file`): the services file lists the ports to probe, so a check
  needs a file with one port.
- `recon` (`--target`, optional `--modules`): the modules of the recon run
  can be limited with `--modules`, so a check can pick the ones that open a
  socket and leave the rest out.
- `report` (`--target`, optional `--audit-file`): it scans the ports of the
  target and audits the credentials.

The transports to patch are the ones the modules really open
(`ethscan.vuln`, `ethscan.recon`, `ethscan.report` use sockets of their
own); patching the module attribute is enough, because the command line
never injects a transport.

Constraints:

- Smallest reversible change; do not weaken an existing guard; turn the
  crash into the module's documented error signal.
- Keep the permanent sweeps in the repository, and prove every new check by
  reverting the guard of its own module.
- Do not commit unless explicitly asked.
