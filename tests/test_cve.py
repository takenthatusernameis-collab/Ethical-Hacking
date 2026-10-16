"""Tests for the ethscan cve command."""

import json
import urllib.error

from ethscan.cve import (
    _extract_cve_summary,
    _fetch_cve_data,
    _finding_detail,
    _get_cached_or_fetch,
    _is_cache_valid,
    _load_cache,
    _lookup_cve_id,
    _normalize_host,
    _resolve_host,
    _save_cache,
    _severity_rank,
    format_cve_report_csv,
    format_cve_report_json,
    format_cve_report_markdown,
    run_cve,
)


def test_normalize_host_bare() -> None:
    assert _normalize_host("example.com") == "example.com"


def test_normalize_host_url() -> None:
    assert _normalize_host("https://example.com/path") == "example.com"
    assert _normalize_host("http://sub.example.com") == "sub.example.com"


def test_normalize_host_uppercase() -> None:
    assert _normalize_host("EXAMPLE.COM") == "example.com"


def test_resolve_host_offline() -> None:
    assert _resolve_host("nonexistent.invalid.domain.tld") is None


def test_lookup_cve_id_known() -> None:
    assert _lookup_cve_id("OpenSSH", "7.2p2") == "CVE-2016-6210"


def test_lookup_cve_id_unknown() -> None:
    assert _lookup_cve_id("OpenSSH", "9.9.9") is None


def test_lookup_cve_id_no_product() -> None:
    assert _lookup_cve_id("", "1.0") is None


def test_cache_load_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("ethscan.cve.CACHE_FILE", tmp_path / "missing.json")
    assert _load_cache() == {}


def test_cache_save_and_load(tmp_path, monkeypatch) -> None:
    cache_file = tmp_path / "cve_cache.json"
    monkeypatch.setattr("ethscan.cve.CACHE_FILE", cache_file)
    _save_cache({"CVE-2016-6210": {"id": "CVE-2016-6210"}})
    loaded = _load_cache()
    assert "CVE-2016-6210" in loaded


def test_cache_valid_with_timestamp(tmp_path, monkeypatch) -> None:

    monkeypatch.setattr("ethscan.cve.time.time", lambda: 1000.0)
    assert _is_cache_valid({"timestamp": 999.0}) is True
    assert _is_cache_valid({"timestamp": 500.0}) is True
    assert _is_cache_valid({"timestamp": -100000.0}) is False


def test_cache_invalid_without_timestamp() -> None:
    assert _is_cache_valid({"id": "x"}) is False


def test_cache_invalid_non_dict() -> None:
    assert _is_cache_valid("not a dict") is False  # type: ignore[arg-type]


def test_extract_cve_summary_valid() -> None:
    data = {
        "vulnerabilities": [
            {
                "cve": {
                    "id": "CVE-2016-6210",
                    "descriptions": [
                        {"lang": "en", "value": "Test description"},
                    ],
                    "metrics": {
                        "cvssMetricV31": [
                            {"cvssData": {"baseSeverity": "MEDIUM", "baseScore": 5.9}}
                        ]
                    },
                    "published": "2017-02-13T17:59:00.153",
                    "lastModified": "2026-06-17T00:50:38.270",
                    "references": [{"url": "http://example.com"}],
                }
            }
        ]
    }
    summary = _extract_cve_summary(data)
    assert summary["id"] == "CVE-2016-6210"
    assert summary["description"] == "Test description"
    assert summary["severity"] == "MEDIUM"
    assert summary["score"] == 5.9
    assert summary["published"] == "2017-02-13T17:59:00.153"
    assert summary["last_modified"] == "2026-06-17T00:50:38.270"
    assert summary["references"] == ["http://example.com"]


def test_extract_cve_summary_empty() -> None:
    assert _extract_cve_summary({}) == {}
    assert _extract_cve_summary({"vulnerabilities": []}) == {}


def test_extract_cve_summary_fallback_description() -> None:
    data = {
        "vulnerabilities": [
            {"cve": {"id": "CVE-X", "descriptions": [{"value": "fallback"}]}}
        ]
    }
    summary = _extract_cve_summary(data)
    assert summary["description"] == "fallback"


def test_run_cve_offline_target(monkeypatch) -> None:
    def mock_run_service(host, ports=None, timeout=3.0, max_workers=50):
        return {
            "target": host,
            "host": host,
            "timeout": timeout,
            "ports_scanned": 0,
            "services_found": 0,
            "results": [],
        }

    monkeypatch.setattr("ethscan.service.run_service", mock_run_service)
    monkeypatch.setattr("ethscan.cve._fetch_cve_data", lambda *a, **k: None)

    result = run_cve("nonexistent.invalid.domain.tld", timeout=0.5)
    assert result["host"] == "nonexistent.invalid.domain.tld"
    assert result["services_checked"] == 0
    assert result["cve_count"] == 0
    assert any("No CVEs matched" in n for n in result["notes"])


def test_run_cve_with_services_file(tmp_path, monkeypatch) -> None:
    services_file = tmp_path / "services.json"
    services_file.write_text(
        json.dumps(
            {
                "target": "example.com",
                "host": "example.com",
                "timeout": 3.0,
                "ports_scanned": 1,
                "services_found": 1,
                "results": [
                    {"port": 22, "banner": "SSH-2.0-OpenSSH_7.2p2", "service": "OpenSSH"}
                ],
            }
        )
    )
    monkeypatch.setattr("ethscan.cve._fetch_cve_data", lambda *a, **k: None)

    result = run_cve(
        "example.com", services_file=str(services_file), timeout=0.5, use_cache=False
    )
    assert result["services_checked"] == 1
    assert result["cve_count"] >= 1
    assert any(e["source"] == "builtin" for e in result["cve_entries"])


def test_run_cve_with_services_file_offline_fallback(tmp_path, monkeypatch) -> None:
    services_file = tmp_path / "services.json"
    services_file.write_text(
        json.dumps(
            {
                "target": "example.com",
                "host": "example.com",
                "timeout": 3.0,
                "ports_scanned": 1,
                "services_found": 1,
                "results": [
                    {"port": 22, "banner": "SSH-2.0-OpenSSH_7.2p2", "service": "OpenSSH"}
                ],
            }
        )
    )
    monkeypatch.setattr("ethscan.cve._fetch_cve_data", lambda *a, **k: None)

    result = run_cve(
        "example.com",
        services_file=str(services_file),
        timeout=0.5,
        use_cache=False,
        offline_fallback=False,
    )
    assert result["offline_fallback"] is False


def test_run_cve_url_target(tmp_path, monkeypatch) -> None:
    services_file = tmp_path / "services.json"
    services_file.write_text(
        json.dumps(
            {
                "target": "example.com",
                "host": "example.com",
                "timeout": 3.0,
                "ports_scanned": 1,
                "services_found": 1,
                "results": [
                    {"port": 22, "banner": "SSH-2.0-OpenSSH_7.2p2", "service": "OpenSSH"}
                ],
            }
        )
    )
    monkeypatch.setattr("ethscan.cve._fetch_cve_data", lambda *a, **k: None)

    result = run_cve(
        "https://example.com", services_file=str(services_file), timeout=0.5, use_cache=False
    )
    assert result["host"] == "example.com"


def test_run_cve_severity_filter(tmp_path, monkeypatch) -> None:
    services_file = tmp_path / "services.json"
    services_file.write_text(
        json.dumps(
            {
                "target": "example.com",
                "host": "example.com",
                "timeout": 3.0,
                "ports_scanned": 1,
                "services_found": 1,
                "results": [
                    {"port": 22, "banner": "SSH-2.0-OpenSSH_7.2p2", "service": "OpenSSH"}
                ],
            }
        )
    )
    monkeypatch.setattr("ethscan.cve._fetch_cve_data", lambda *a, **k: None)

    result = run_cve(
        "example.com",
        services_file=str(services_file),
        timeout=0.5,
        use_cache=False,
        severity="medium",
    )
    assert result["severity_filter"] == "medium"
    for entry in result["cve_entries"]:
        finding = entry.get("finding") or {}
        cve = entry.get("cve") or {}
        level = finding.get("severity") or cve.get("severity")
        assert level is None or str(level).lower() == "medium"


def test_run_cve_custom_api_url(tmp_path, monkeypatch) -> None:
    services_file = tmp_path / "services.json"
    services_file.write_text(
        json.dumps(
            {
                "target": "example.com",
                "host": "example.com",
                "timeout": 3.0,
                "ports_scanned": 1,
                "services_found": 1,
                "results": [
                    {"port": 22, "banner": "SSH-2.0-OpenSSH_7.2p2", "service": "OpenSSH"}
                ],
            }
        )
    )
    monkeypatch.setattr("ethscan.cve._fetch_cve_data", lambda *a, **k: None)

    result = run_cve(
        "example.com",
        services_file=str(services_file),
        timeout=0.5,
        use_cache=False,
        api_url="https://cve.example.com/",
    )
    assert result["api_url"] == "https://cve.example.com/"


def test_format_cve_report_json_basic() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 0.5,
        "use_cache": True,
        "offline_fallback": True,
        "api_url": None,
        "severity_filter": None,
        "services_checked": 1,
        "cve_entries": [],
        "cve_count": 0,
        "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "notes": [],
    }
    output = format_cve_report_json(data)
    parsed = json.loads(output)
    assert parsed["target"] == "example.com"
    assert "cve_entries" in parsed


def test_format_cve_report_json_empty_entries() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 0.5,
        "use_cache": False,
        "offline_fallback": False,
        "api_url": None,
        "severity_filter": None,
        "services_checked": 0,
        "cve_entries": [],
        "cve_count": 0,
        "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "notes": ["No CVEs matched"],
    }
    output = format_cve_report_json(data)
    parsed = json.loads(output)
    assert parsed["cve_entries"] == []


def test_format_cve_report_markdown_full() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 0.5,
        "use_cache": True,
        "offline_fallback": True,
        "api_url": None,
        "severity_filter": None,
        "services_checked": 1,
        "cve_entries": [
            {
                "source": "builtin",
                "port": 22,
                "product": "OpenSSH",
                "version": "7.2p2",
                "finding": {
                    "id": "CVE-2016-6210",
                    "kind": "service",
                    "title": "OpenSSH user enumeration",
                    "severity": "medium",
                    "description": "Timing attack",
                    "product": "OpenSSH",
                    "version": "7.2p2",
                    "port": 22,
                },
            }
        ],
        "cve_count": 1,
        "severity_counts": {"critical": 0, "high": 0, "medium": 1, "low": 0},
        "notes": [],
    }
    output = format_cve_report_markdown(data)
    assert "# ethscan CVE Report" in output
    assert "## Severity Summary" in output
    assert "## CVE Findings" in output
    assert "CVE-2016-6210" in output
    assert "OpenSSH" in output
    assert "example.com" in output


def test_format_cve_report_markdown_no_entries() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 0.5,
        "use_cache": True,
        "offline_fallback": True,
        "api_url": None,
        "severity_filter": None,
        "services_checked": 0,
        "cve_entries": [],
        "cve_count": 0,
        "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "notes": ["No CVEs matched"],
    }
    output = format_cve_report_markdown(data)
    assert "*No CVEs matched.*" in output
    assert "## Notes" in output


def test_format_cve_report_markdown_pipe_escape() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": "a|b",
        "use_cache": True,
        "offline_fallback": True,
        "api_url": None,
        "severity_filter": None,
        "services_checked": 1,
        "cve_entries": [
            {
                "source": "builtin",
                "port": 22,
                "product": "Open|SSH",
                "version": "7.2p2",
                "finding": {
                    "id": "CVE-2016-6210",
                    "kind": "service",
                    "title": "Test | title",
                    "severity": "medium",
                    "description": "desc | with pipe",
                    "product": "Open|SSH",
                    "version": "7.2p2",
                    "port": 22,
                },
            }
        ],
        "cve_count": 1,
        "severity_counts": {"critical": 0, "high": 0, "medium": 1, "low": 0},
        "notes": [],
    }
    output = format_cve_report_markdown(data)
    assert "\\|" in output
    assert "Open|SSH" not in output.replace("\\|", "")


def test_format_cve_report_markdown_nvd_entry() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 0.5,
        "use_cache": True,
        "offline_fallback": True,
        "api_url": None,
        "severity_filter": None,
        "services_checked": 1,
        "cve_entries": [
            {
                "source": "nvd",
                "port": 22,
                "product": "OpenSSH",
                "version": "7.2p2",
                "cve_id": "CVE-2016-6210",
                "cve": {
                    "id": "CVE-2016-6210",
                    "description": "Test description",
                    "severity": "MEDIUM",
                    "score": 5.9,
                    "published": "2017-02-13",
                    "last_modified": "2026-06-17",
                    "references": ["http://example.com"],
                },
                "cached": False,
                "offline_fallback": False,
            }
        ],
        "cve_count": 1,
        "severity_counts": {"critical": 0, "high": 0, "medium": 1, "low": 0},
        "notes": [],
    }
    output = format_cve_report_markdown(data)
    assert "NVD API" in output
    assert "CVE-2016-6210" in output
    assert "CVSS Score" in output
    assert "http://example.com" in output


def test_run_cve_with_ports_parameter(monkeypatch) -> None:
    called_ports = {}

    def mock_run_service(host, ports=None, timeout=3.0, max_workers=50):
        called_ports["ports"] = ports
        return {
            "target": host,
            "host": host,
            "timeout": timeout,
            "ports_scanned": 0,
            "services_found": 0,
            "results": [],
        }

    monkeypatch.setattr("ethscan.service.run_service", mock_run_service)
    monkeypatch.setattr("ethscan.cve._fetch_cve_data", lambda *a, **k: None)

    result = run_cve(
        "example.com", timeout=0.5, use_cache=False, ports=[22, 80, 443]
    )
    assert result["ports"] == [22, 80, 443]
    assert called_ports["ports"] == [22, 80, 443]


def test_run_cve_without_ports_parameter(monkeypatch) -> None:
    called_ports = {}

    def mock_run_service(host, ports=None, timeout=3.0, max_workers=50):
        called_ports["ports"] = ports
        return {
            "target": host,
            "host": host,
            "timeout": timeout,
            "ports_scanned": 0,
            "services_found": 0,
            "results": [],
        }

    monkeypatch.setattr("ethscan.service.run_service", mock_run_service)
    monkeypatch.setattr("ethscan.cve._fetch_cve_data", lambda *a, **k: None)

    result = run_cve("example.com", timeout=0.5, use_cache=False)
    assert result["ports"] is None
    assert called_ports["ports"] is None


def test_format_cve_report_markdown_with_ports() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 0.5,
        "use_cache": True,
        "offline_fallback": True,
        "api_url": None,
        "severity_filter": None,
        "ports": [22, 80, 443],
        "services_checked": 1,
        "cve_entries": [],
        "cve_count": 0,
        "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "notes": [],
    }
    output = format_cve_report_markdown(data)
    assert "Ports Scanned" in output
    assert "22" in output
    assert "80" in output
    assert "443" in output


def test_format_cve_report_markdown_without_ports() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 0.5,
        "use_cache": True,
        "offline_fallback": True,
        "api_url": None,
        "severity_filter": None,
        "ports": None,
        "services_checked": 1,
        "cve_entries": [],
        "cve_count": 0,
        "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "notes": [],
    }
    output = format_cve_report_markdown(data)
    assert "Ports Scanned" not in output


def test_format_cve_report_json_includes_ports() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 0.5,
        "use_cache": True,
        "offline_fallback": True,
        "api_url": None,
        "severity_filter": None,
        "ports": [22, 80],
        "services_checked": 1,
        "cve_entries": [],
        "cve_count": 0,
        "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "notes": [],
    }
    output = format_cve_report_json(data)
    parsed = json.loads(output)
    assert parsed["ports"] == [22, 80]


def test_run_cve_min_severity_drops_lower(tmp_path, monkeypatch) -> None:
    services_file = tmp_path / "services.json"
    services_file.write_text(
        json.dumps(
            {
                "target": "example.com",
                "host": "example.com",
                "timeout": 3.0,
                "ports_scanned": 1,
                "services_found": 1,
                "results": [
                    {"port": 22, "banner": "SSH-2.0-OpenSSH_7.2p2", "service": "OpenSSH"}
                ],
            }
        )
    )
    monkeypatch.setattr("ethscan.cve._fetch_cve_data", lambda *a, **k: None)

    result = run_cve(
        "example.com",
        services_file=str(services_file),
        timeout=0.5,
        use_cache=False,
        min_severity="high",
    )
    assert result["min_severity_filter"] == "high"
    # OpenSSH 7.2p2 only matches medium findings, so all are dropped
    assert result["cve_count"] == 0


def test_run_cve_min_severity_none_keeps_all(tmp_path, monkeypatch) -> None:
    services_file = tmp_path / "services.json"
    services_file.write_text(
        json.dumps(
            {
                "target": "example.com",
                "host": "example.com",
                "timeout": 3.0,
                "ports_scanned": 1,
                "services_found": 1,
                "results": [
                    {"port": 22, "banner": "SSH-2.0-OpenSSH_7.2p2", "service": "OpenSSH"}
                ],
            }
        )
    )
    monkeypatch.setattr("ethscan.cve._fetch_cve_data", lambda *a, **k: None)

    result = run_cve(
        "example.com",
        services_file=str(services_file),
        timeout=0.5,
        use_cache=False,
    )
    assert result["min_severity_filter"] is None
    assert result["cve_count"] >= 1


def test_run_cve_min_severity_low_keeps_all(tmp_path, monkeypatch) -> None:
    services_file = tmp_path / "services.json"
    services_file.write_text(
        json.dumps(
            {
                "target": "example.com",
                "host": "example.com",
                "timeout": 3.0,
                "ports_scanned": 1,
                "services_found": 1,
                "results": [
                    {"port": 22, "banner": "SSH-2.0-OpenSSH_7.2p2", "service": "OpenSSH"}
                ],
            }
        )
    )
    monkeypatch.setattr("ethscan.cve._fetch_cve_data", lambda *a, **k: None)

    result = run_cve(
        "example.com",
        services_file=str(services_file),
        timeout=0.5,
        use_cache=False,
        min_severity="low",
    )
    assert result["min_severity_filter"] == "low"
    assert result["cve_count"] >= 1


def test_run_cve_min_severity_critical_drops_all(tmp_path, monkeypatch) -> None:
    services_file = tmp_path / "services.json"
    services_file.write_text(
        json.dumps(
            {
                "target": "example.com",
                "host": "example.com",
                "timeout": 3.0,
                "ports_scanned": 1,
                "services_found": 1,
                "results": [
                    {"port": 22, "banner": "SSH-2.0-OpenSSH_7.2p2", "service": "OpenSSH"}
                ],
            }
        )
    )
    monkeypatch.setattr("ethscan.cve._fetch_cve_data", lambda *a, **k: None)

    result = run_cve(
        "example.com",
        services_file=str(services_file),
        timeout=0.5,
        use_cache=False,
        min_severity="critical",
    )
    assert result["min_severity_filter"] == "critical"
    assert result["cve_count"] == 0


def test_format_cve_report_markdown_with_min_severity() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 0.5,
        "use_cache": True,
        "offline_fallback": True,
        "api_url": None,
        "severity_filter": None,
        "min_severity_filter": "high",
        "ports": None,
        "services_checked": 1,
        "cve_entries": [],
        "cve_count": 0,
        "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "notes": [],
    }
    output = format_cve_report_markdown(data)
    assert "Min Severity" in output
    assert "high" in output


def test_format_cve_report_csv_basic() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 0.5,
        "use_cache": True,
        "offline_fallback": True,
        "api_url": None,
        "severity_filter": None,
        "min_severity_filter": None,
        "ports": None,
        "services_checked": 1,
        "cve_entries": [
            {
                "source": "builtin",
                "port": 22,
                "product": "OpenSSH",
                "version": "7.2p2",
                "finding": {
                    "id": "CVE-2016-6210",
                    "kind": "service",
                    "title": "OpenSSH user enumeration",
                    "severity": "medium",
                    "description": "Timing attack",
                    "product": "OpenSSH",
                    "version": "7.2p2",
                    "port": 22,
                },
            },
            {
                "source": "nvd",
                "port": 22,
                "product": "OpenSSH",
                "version": "7.2p2",
                "cve_id": "CVE-2016-6210",
                "cve": {
                    "id": "CVE-2016-6210",
                    "description": "Test description",
                    "severity": "MEDIUM",
                    "score": 5.9,
                    "published": "2017-02-13",
                    "last_modified": "2026-06-17",
                    "references": ["http://example.com"],
                },
                "cached": False,
                "offline_fallback": False,
            },
        ],
        "cve_count": 2,
        "severity_counts": {"critical": 0, "high": 0, "medium": 2, "low": 0},
        "notes": [],
    }
    output = format_cve_report_csv(data)
    lines = output.splitlines()
    assert lines[0] == "source,port,product,version,cve_id,severity,score,title,description,references,cached,offline_fallback"
    # builtin row
    builtin_row = lines[1]
    assert "builtin" in builtin_row
    assert "CVE-2016-6210" in builtin_row
    assert "MEDIUM" in builtin_row
    assert "OpenSSH user enumeration" in builtin_row
    # nvd row
    nvd_row = lines[2]
    assert "nvd" in nvd_row
    assert "5.9" in nvd_row
    assert "http://example.com" in nvd_row
    assert "false" in nvd_row


def test_format_cve_report_csv_no_findings() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 0.5,
        "use_cache": True,
        "offline_fallback": True,
        "api_url": None,
        "severity_filter": None,
        "min_severity_filter": None,
        "ports": None,
        "services_checked": 0,
        "cve_entries": [],
        "cve_count": 0,
        "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "notes": ["No CVEs matched"],
    }
    output = format_cve_report_csv(data)
    lines = output.splitlines()
    assert len(lines) == 1
    assert lines[0] == "source,port,product,version,cve_id,severity,score,title,description,references,cached,offline_fallback"


def test_format_cve_report_csv_missing_optional_fields() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 0.5,
        "use_cache": True,
        "offline_fallback": True,
        "api_url": None,
        "severity_filter": None,
        "min_severity_filter": None,
        "ports": None,
        "services_checked": 1,
        "cve_entries": [
            {
                "source": "builtin",
                "port": None,
                "product": "",
                "version": "",
                "finding": {
                    "id": "CVE-X",
                    "kind": "protocol",
                    "title": "Weak protocol",
                    "severity": "low",
                    "description": "desc",
                },
            }
        ],
        "cve_count": 1,
        "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 1},
        "notes": [],
    }
    output = format_cve_report_csv(data)
    lines = output.splitlines()
    assert len(lines) == 2
    assert "CVE-X" in lines[1]
    assert "LOW" in lines[1]
    assert "builtin" in lines[1]


def test_format_cve_report_csv_escaping() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 0.5,
        "use_cache": True,
        "offline_fallback": True,
        "api_url": None,
        "severity_filter": None,
        "min_severity_filter": None,
        "ports": None,
        "services_checked": 1,
        "cve_entries": [
            {
                "source": "builtin",
                "port": 22,
                "product": "OpenSSH",
                "version": "7.2p2",
                "finding": {
                    "id": "CVE-2016-6210",
                    "kind": "service",
                    "title": "OpenSSH user enumeration, \"quoted\"",
                    "severity": "medium",
                    "description": "Timing attack\nwith newline",
                    "product": "OpenSSH",
                    "version": "7.2p2",
                    "port": 22,
                },
            }
        ],
        "cve_count": 1,
        "severity_counts": {"critical": 0, "high": 0, "medium": 1, "low": 0},
        "notes": [],
    }
    output = format_cve_report_csv(data)
    # The CSV should quote the title and description because they contain special characters.
    # Since csv.writer quotes fields containing special characters (like comma, quote, newline),
    # we expect the title to be quoted because it contains a comma and a quote.
    # The description contains a newline, so it should be quoted as well.
    # We'll check that the output can be parsed correctly by a CSV reader.
    import csv
    import io
    reader = csv.reader(io.StringIO(output))
    rows = list(reader)
    assert len(rows) == 2  # header + one data row
    header = rows[0]
    assert header == ["source", "port", "product", "version", "cve_id", "severity", "score", "title", "description", "references", "cached", "offline_fallback"]
    row = rows[1]
    assert row[0] == "builtin"
    assert row[1] == "22"
    assert row[2] == "OpenSSH"
    assert row[3] == "7.2p2"
    assert row[4] == "CVE-2016-6210"
    assert row[5] == "MEDIUM"
    assert row[6] == ""
    assert row[7] == 'OpenSSH user enumeration, "quoted"'  # Note: the csv reader will have removed the outer quotes
    assert row[8] == "Timing attack\nwith newline"
    assert row[9] == ""
    assert row[10] == ""
    assert row[11] == ""


def test_load_cache_invalid_json(tmp_path, monkeypatch) -> None:
    cache_file = tmp_path / "cve_cache.json"
    cache_file.write_text("{not valid json", encoding="utf-8")
    monkeypatch.setattr("ethscan.cve.CACHE_FILE", cache_file)
    assert _load_cache() == {}


def test_save_cache_os_error(tmp_path, monkeypatch) -> None:
    cache_file = tmp_path / "cve_cache.json"
    monkeypatch.setattr("ethscan.cve.CACHE_FILE", cache_file)

    def fake_open(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("builtins.open", fake_open)
    _save_cache({"CVE-X": {"id": "CVE-X"}})


def test_is_cache_valid_type_error() -> None:
    assert _is_cache_valid({"timestamp": "not-a-number"}) is False


def test_fetch_cve_data_non_dict(monkeypatch) -> None:
    class FakeResponse:
        def read(self) -> bytes:
            return b"[1, 2, 3]"

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

    monkeypatch.setattr(
        "ethscan.cve.urllib.request.urlopen",
        lambda req, timeout=None: FakeResponse(),
    )
    assert _fetch_cve_data("CVE-X") is None


def test_fetch_cve_data_network_error(monkeypatch) -> None:
    monkeypatch.setattr(
        "ethscan.cve.urllib.request.urlopen",
        lambda req, timeout=None: (_ for _ in ()).throw(
            urllib.error.URLError("down")
        ),
    )
    assert _fetch_cve_data("CVE-X") is None


def test_fetch_cve_data_success(monkeypatch) -> None:
    class FakeResponse:
        def read(self) -> bytes:
            return b'{"vulnerabilities": []}'

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

    monkeypatch.setattr(
        "ethscan.cve.urllib.request.urlopen",
        lambda req, timeout=None: FakeResponse(),
    )
    assert _fetch_cve_data("CVE-X") == {"vulnerabilities": []}


def test_get_cached_or_fetch_cache_hit(tmp_path, monkeypatch) -> None:
    cache_file = tmp_path / "cve_cache.json"
    monkeypatch.setattr("ethscan.cve.CACHE_FILE", cache_file)
    monkeypatch.setattr("ethscan.cve.time.time", lambda: 1000.0)
    _save_cache({"CVE-X": {"id": "CVE-X", "timestamp": 999.0}})

    result = _get_cached_or_fetch(
        "CVE-X", timeout=0.5, use_cache=True, offline_fallback=False, api_url=None
    )
    assert result["cached"] is True
    assert result["id"] == "CVE-X"


def test_get_cached_or_fetch_offline_fallback(tmp_path, monkeypatch) -> None:
    cache_file = tmp_path / "cve_cache.json"
    monkeypatch.setattr("ethscan.cve.CACHE_FILE", cache_file)
    monkeypatch.setattr("ethscan.cve._fetch_cve_data", lambda *a, **k: None)
    _save_cache({"CVE-X": {"id": "CVE-X", "timestamp": 1.0}})

    result = _get_cached_or_fetch(
        "CVE-X", timeout=0.5, use_cache=True, offline_fallback=True, api_url=None
    )
    assert result["cached"] is True
    assert result["offline_fallback"] is True


def test_get_cached_or_fetch_saves_cache(tmp_path, monkeypatch) -> None:
    cache_file = tmp_path / "cve_cache.json"
    monkeypatch.setattr("ethscan.cve.CACHE_FILE", cache_file)
    monkeypatch.setattr(
        "ethscan.cve._fetch_cve_data",
        lambda *a, **k: {"vulnerabilities": [{"cve": {"id": "CVE-X"}}]},
    )

    result = _get_cached_or_fetch(
        "CVE-X", timeout=0.5, use_cache=True, offline_fallback=False, api_url=None
    )
    assert result["cached"] is False
    assert "CVE-X" in _load_cache()


def test_extract_cve_summary_first_not_dict() -> None:
    assert _extract_cve_summary({"vulnerabilities": ["not a dict"]}) == {}


def test_extract_cve_summary_cve_not_dict() -> None:
    assert _extract_cve_summary({"vulnerabilities": [{"cve": "not a dict"}]}) == {}


def test_severity_rank_empty_string() -> None:
    assert _severity_rank("") is None


def test_run_cve_services_file_read_error(tmp_path, monkeypatch) -> None:
    services_file = tmp_path / "services.json"
    services_file.write_text("{not valid json", encoding="utf-8")
    monkeypatch.setattr("ethscan.cve._fetch_cve_data", lambda *a, **k: None)
    monkeypatch.setattr(
        "ethscan.service.run_service", lambda *a, **k: {"results": []}
    )

    result = run_cve(
        "example.com", services_file=str(services_file), timeout=0.5, use_cache=False
    )
    assert any("Failed to read services file" in n for n in result["notes"])


def test_run_cve_nvd_summary_appended(tmp_path, monkeypatch) -> None:
    services_file = tmp_path / "services.json"
    services_file.write_text(
        json.dumps(
            {
                "target": "example.com",
                "host": "example.com",
                "timeout": 3.0,
                "ports_scanned": 1,
                "services_found": 1,
                "results": [
                    {
                        "port": 22,
                        "banner": "SSH-2.0-OpenSSH_7.2p2",
                        "service": "OpenSSH",
                    }
                ],
            }
        )
    )
    cve_data = {
        "vulnerabilities": [
            {
                "cve": {
                    "id": "CVE-2016-6210",
                    "descriptions": [
                        {"lang": "en", "value": "OpenSSH user enumeration"}
                    ],
                    "metrics": {
                        "cvssMetricV31": [
                            {"cvssData": {"baseSeverity": "MEDIUM", "baseScore": 5.9}}
                        ]
                    },
                    "published": "2016-08-01",
                    "lastModified": "2026-01-01",
                    "references": [{"url": "http://example.com"}],
                }
            }
        ]
    }
    monkeypatch.setattr(
        "ethscan.cve._get_cached_or_fetch", lambda *a, **k: cve_data
    )

    result = run_cve(
        "example.com", services_file=str(services_file), timeout=0.5, use_cache=False
    )
    nvd = [e for e in result["cve_entries"] if e.get("source") == "nvd"]
    assert len(nvd) == 1
    assert nvd[0]["cve_id"] == "CVE-2016-6210"
    assert nvd[0]["cve"]["severity"] == "MEDIUM"


def test_finding_detail_non_service() -> None:
    assert _finding_detail({"kind": "protocol", "title": "Weak protocol"}) == ""


def test_format_cve_report_markdown_full_sections() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 0.5,
        "use_cache": True,
        "offline_fallback": True,
        "api_url": "https://custom.example.com/",
        "severity_filter": "high",
        "service_timeout": 3.0,
        "workers": 10,
        "profile": "fast",
        "services_checked": 1,
        "cve_entries": [],
        "cve_count": 0,
        "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "notes": [],
    }
    output = format_cve_report_markdown(data)
    assert "Profile" in output and "fast" in output
    assert "Service Timeout" in output and "3.0s" in output
    assert "Workers" in output and "10" in output
    assert "API URL" in output
    assert "Severity Filter" in output and "high" in output


def test_format_cve_report_markdown_cached_offline_flags() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 0.5,
        "use_cache": True,
        "offline_fallback": True,
        "api_url": None,
        "severity_filter": None,
        "services_checked": 1,
        "cve_entries": [
            {
                "source": "nvd",
                "port": 22,
                "product": "OpenSSH",
                "version": "7.2p2",
                "cve_id": "CVE-X",
                "cve": {
                    "id": "CVE-X",
                    "description": "desc",
                    "severity": "MEDIUM",
                    "score": 5.0,
                    "published": "",
                    "last_modified": "",
                    "references": [],
                },
                "cached": True,
                "offline_fallback": True,
            }
        ],
        "cve_count": 1,
        "severity_counts": {"critical": 0, "high": 0, "medium": 1, "low": 0},
        "notes": [],
    }
    output = format_cve_report_markdown(data)
    assert "- **Cached:** Yes" in output
    assert "- **Offline Fallback:** Yes" in output
