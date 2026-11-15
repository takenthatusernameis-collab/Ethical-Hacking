"""Tests to close branch gaps in ethscan/vuln.py."""

from ethscan.vuln import run_vuln


def test_run_vuln_empty_banner_skips_append(monkeypatch):
    """Cover 950->955: empty banner string skips banners.append()."""
    def mock_run_service(host, ports=None, timeout=3.0, max_workers=50):
        return {
            "results": [
                {"port": 22, "banner": "SSH-2.0-OpenSSH_7.2p2"},
                {"port": 80, "banner": ""},  # empty banner string
            ]
        }

    monkeypatch.setattr("ethscan.vuln.run_service", mock_run_service)

    results = run_vuln("example.com")
    # Should have checked both services (services_checked counts entries with valid banners)
    assert results["services_checked"] == 2
    # Empty banner should not be added to banners list
    # The _scan_host function returns banners, but run_vuln doesn't expose it directly
    # Just verify it doesn't crash and processes correctly
    assert results["finding_count"] >= 1  # OpenSSH finding


def test_run_vuln_min_severity_none_false_branch(monkeypatch):
    """Cover 977->984: min_severity=None takes false branch, skips filtering."""
    def mock_run_service(host, ports=None, timeout=3.0, max_workers=50):
        return {
            "results": [
                {"port": 22, "banner": "SSH-2.0-OpenSSH_7.2p2"},
                {"port": 21, "banner": "220 (vsFTPd 2.3.4)"},
            ]
        }

    monkeypatch.setattr("ethscan.vuln.run_service", mock_run_service)

    # Call without min_severity (defaults to None)
    results = run_vuln("example.com")
    assert results["min_severity_filter"] is None
    # Should keep all findings (medium from OpenSSH + critical from vsftpd)
    assert results["finding_count"] >= 2
    assert results["severity_counts"]["medium"] >= 1
    assert results["severity_counts"]["critical"] >= 1


def test_run_vuln_recursive_normalized_host_false_branch(monkeypatch):
    """Cover 1031->1029: normalized_discovered falsy or already scanned continues loop."""
    call_count = {"count": 0}

    def mock_run_service(host, ports=None, timeout=3.0, max_workers=50):
        call_count["count"] += 1
        if host == "example.com":
            # Banner contains a host that normalizes to empty (invalid)
            # and a valid host that will be scanned
            return {
                "results": [
                    {"port": 80, "banner": "Server: nginx via invalid..host", "service": "nginx"},
                    {"port": 80, "banner": "Server: nginx via backend.internal.example.com", "service": "nginx"},
                ]
            }
        elif host == "backend.internal.example.com":
            return {
                "results": [
                    {"port": 22, "banner": "SSH-2.0-OpenSSH_7.2p2", "service": "OpenSSH"},
                ]
            }
        return {"results": []}

    monkeypatch.setattr("ethscan.vuln.run_service", mock_run_service)

    results = run_vuln("example.com", recursive=True, max_depth=1)
    # Should scan example.com and backend.internal.example.com
    # invalid..host should normalize to empty and be skipped (1031 false branch)
    assert "backend.internal.example.com" in results["recursive_hosts_scanned"]
    assert call_count["count"] == 2


def test_run_vuln_recursive_result_false_branch(monkeypatch):
    """Cover 1036->1029: recursive_result falsy (empty dict) skips append."""
    call_count = {"count": 0}

    def mock_run_service(host, ports=None, timeout=3.0, max_workers=50):
        call_count["count"] += 1
        if host == "example.com":
            return {
                "results": [
                    {"port": 80, "banner": "Server: nginx via deeper.internal.example.com", "service": "nginx"},
                ]
            }
        elif host == "deeper.internal.example.com":
            # This host will be scanned at depth 1, but max_depth=1 so depth 2 > max_depth
            # _recursive_scan returns {} (falsy) at line 1009-1010
            return {
                "results": [
                    {"port": 22, "banner": "SSH-2.0-OpenSSH_7.2p2", "service": "OpenSSH"},
                ]
            }
        return {"results": []}

    monkeypatch.setattr("ethscan.vuln.run_service", mock_run_service)

    # max_depth=1 means:
    # - depth 0: example.com (scans, discovers deeper.internal.example.com)
    # - depth 1: deeper.internal.example.com (scans, but depth=1 not < max_depth=1, so no further recursion)
    # - If a host at depth 1 discovered another host, depth 2 > max_depth=1, _recursive_scan returns {}
    results = run_vuln("example.com", recursive=True, max_depth=1)
    # deeper.internal.example.com is scanned at depth 1
    assert "deeper.internal.example.com" in results["recursive_hosts_scanned"]
    # The recursive call for deeper.internal.example.com returns a result (not empty)
    # But if it discovered a host at depth 2, that recursive call would return {}
    assert call_count["count"] == 2


def test_run_vuln_recursive_result_empty_dict_at_max_depth(monkeypatch):
    """Cover 1036->1029: recursive_result is {} when depth > max_depth."""
    call_count = {"count": 0}

    def mock_run_service(host, ports=None, timeout=3.0, max_workers=50):
        call_count["count"] += 1
        if host == "example.com":
            return {
                "results": [
                    {"port": 80, "banner": "Server: nginx via host1.internal.example.com", "service": "nginx"},
                ]
            }
        elif host == "host1.internal.example.com":
            return {
                "results": [
                    {"port": 80, "banner": "Server: apache via host2.internal.example.com", "service": "apache"},
                ]
            }
        elif host == "host2.internal.example.com":
            return {
                "results": [
                    {"port": 22, "banner": "SSH-2.0-OpenSSH_7.2p2", "service": "OpenSSH"},
                ]
            }
        return {"results": []}

    monkeypatch.setattr("ethscan.vuln.run_service", mock_run_service)

    # max_depth=1:
    # - depth 0: example.com -> discovers host1.internal.example.com
    # - depth 1: host1.internal.example.com -> discovers host2.internal.example.com
    # - depth 2: host2.internal.example.com -> depth (2) > max_depth (1), returns {}
    # The recursive_result for host2 would be {}, which is falsy (1036 false branch)
    results = run_vuln("example.com", recursive=True, max_depth=1)
    assert "host1.internal.example.com" in results["recursive_hosts_scanned"]
    # host2.internal.example.com should NOT be scanned because depth would be 2 > max_depth 1
    assert "host2.internal.example.com" not in results["recursive_hosts_scanned"]
    assert call_count["count"] == 2