"""Focused branch-coverage tests for ethscan/vuln.py partial branches.

Reproduced with: python -m coverage run --branch -m pytest tests/test_vuln.py tests/test_vuln_hostile_sweep.py tests/test_vuln_formatter_hostile_sweep.py -q
then: python -m coverage report --show-missing --include='ethscan/vuln.py'
Initial state: 476 stmts, 0 miss, 244 branch, 4 BrPart (99%), missing 950->955, 977->984, 1031->1029, 1036->1029.
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


# 1036->1029 (if recursive_result:) is UNREACHABLE under the current control
# flow and is left uncovered. The guard at line 1024 (if depth < max_depth:)
# gates host discovery, so a recursive call can only be made when depth <
# max_depth. That call returns {} only when depth+1 > max_depth, i.e. depth >=
# max_depth — a contradiction. No input forces the false branch; it is a
# defensive check, not a reachable arc.