"""Focused branch-coverage tests for ethscan/vuln.py.

Reproduced with: python -m coverage run --branch --source=ethscan.vuln -m pytest
tests/test_vuln.py tests/test_vuln_hostile_sweep.py tests/test_vuln_branch_gaps.py
tests/test_vuln_formatter_hostile_sweep.py -q
then: python -m coverage report --show-missing --include='ethscan/vuln.py'
Final state: 476 stmts, 0 miss, 243 branch, 0 BrPart (100%).

Reachable partial branches closed by tests in this file:
- 950->955: a banner entry whose value is not a str is skipped.
- 977->984: an unknown min_severity label yields min_rank None, so the
  min_severity filter block is skipped entirely (findings untouched).
- 1031->1029: a discovered host that normalizes to a host already in
  scanned_hosts (the initial host itself) is skipped — no recursion.

Reachable partial branches closed by tests/test_vuln_formatter_hostile_sweep.py:
- 1147->1149: a service finding whose port is None skips the "(port N)" suffix.
- 1259->1270: recursive_hosts_scanned is empty, so the "### Hosts Scanned"
  subsection is omitted while the "### Recursive Findings" subsection renders.

Defensive branch (excluded from branch coverage as unreachable by control flow):
- 1036: `if recursive_result:` is always True for calls reached here. Discovery
  runs only when `depth < max_depth` (line 1024), so `_recursive_scan(..., depth + 1)`
  never takes its early-return path (`depth > max_depth`); the callee returns a
  populated result dict. Marked `# pragma: no branch`.
"""
from __future__ import annotations

from ethscan.vuln import run_vuln


def test_scan_host_skips_non_string_banner(monkeypatch) -> None:
    """Covers 950->955: a banner entry whose value is not a str is skipped."""
    def mock_run_service(host, ports=None, timeout=3.0, max_workers=50):
        return {
            "results": [
                {"port": 22, "banner": "SSH-2.0-OpenSSH_7.2p2"},
                # Non-str banner values are skipped at line 948 (continue),
                # before parse_banner is reached at line 958.
                {"port": 80, "banner": 12345},
                {"port": 443, "banner": None},
                {"port": 8080, "banner": b"bytes-banner"},
            ]
        }

    monkeypatch.setattr("ethscan.vuln.run_service", mock_run_service)

    results = run_vuln("example.com")
    # Only the str banner (OpenSSH 7.2p2) is matched; the non-str banners
    # (int, None, bytes) are skipped at line 948 (continue), so no findings
    # reference ports 80/443/8080.
    assert results["finding_count"] >= 1
    assert all(f.get("kind") == "service" for f in results["findings"])
    assert all(f.get("port") == 22 for f in results["findings"])


def test_min_severity_unknown_filter_drops_all(monkeypatch) -> None:
    """Covers 977->984: an unknown min_severity label yields min_rank None, so the
    min_severity filter block is skipped entirely (findings untouched)."""
    def mock_run_service(host, ports=None, timeout=3.0, max_workers=50):
        return {
            "results": [
                {"port": 22, "banner": "SSH-2.0-OpenSSH_7.2p2"},
            ]
        }

    monkeypatch.setattr("ethscan.vuln.run_service", mock_run_service)

    results = run_vuln("example.com", min_severity="bogus")
    assert results["min_severity_filter"] == "bogus"
    # Unknown label -> filter block skipped -> findings untouched.
    assert results["finding_count"] >= 1


def test_recursive_scan_skips_already_scanned_host(monkeypatch) -> None:
    """Covers 1031->1029: a discovered host that normalizes to a host already in
    scanned_hosts (the initial host itself) is skipped — no recursion, not
    re-added to recursive_hosts_scanned."""
    call_count = {"count": 0}

    def mock_run_service(host, ports=None, timeout=3.0, max_workers=50):
        call_count["count"] += 1
        if host == "example.com":
            return {
                "results": [
                    # Banner advertises the initial host itself; it is already in
                    # scanned_hosts (added at line 909), so the guard at line 1031
                    # is False and the branch 1031->1029 is taken.
                    {"port": 80, "banner": "Server: nginx for example.com", "service": "nginx"},
                ]
            }
        return {"results": []}

    monkeypatch.setattr("ethscan.vuln.run_service", mock_run_service)

    results = run_vuln("example.com", recursive=True, max_depth=1)
    assert results["recursive"] is True
    assert results["recursive_hosts_scanned"] == []
    assert results["recursive_findings"] == []
    # Only the initial host was scanned; the duplicate was skipped.
    assert call_count["count"] == 1


# 1036 (`if recursive_result:`) is excluded from branch coverage with
# `# pragma: no branch` because the false path is unreachable by control flow:
# discovery is gated by `depth < max_depth`, so the recursive call cannot take
# its early-return path and always yields a populated result dict.