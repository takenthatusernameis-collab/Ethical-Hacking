"""Tests for the ethscan vuln module."""

import json

from ethscan.vuln import (
    CERTIFICATE_VULNS,
    CIPHER_VULNS,
    DEFAULT_TIMEOUT,
    DEFAULT_WORKERS,
    PROTOCOL_VULNS,
    SERVICE_VULNS,
    SEVERITIES,
    VULN_DB,
    _apply_salt_pepper_to_banner,
    _compute_password_hash,
    _compute_peppered_hash,
    _normalize_host,
    _severity_rank,
    _transform_banner,
    format_vuln_report_csv,
    format_vuln_report_json,
    format_vuln_report_markdown,
    match_certificate_vulns,
    match_cipher_vulns,
    match_protocol_vulns,
    match_service_vulns,
    match_ssl_vulns,
    match_tls_vulns,
    parse_banner,
    run_vuln,
    version_in_range,
)


def test_defaults() -> None:
    assert DEFAULT_TIMEOUT == 3.0
    assert DEFAULT_WORKERS == 50
    assert SEVERITIES == ("critical", "high", "medium", "low")
    assert len(SERVICE_VULNS) > 0
    assert len(PROTOCOL_VULNS) > 0
    assert len(CIPHER_VULNS) > 0
    assert len(CERTIFICATE_VULNS) > 0
    assert len(VULN_DB) == (
        len(SERVICE_VULNS) + len(PROTOCOL_VULNS) + len(CIPHER_VULNS)
        + len(CERTIFICATE_VULNS)
    )


def test_normalize_host_bare() -> None:
    assert _normalize_host("example.com") == "example.com"
    assert _normalize_host("EXAMPLE.COM") == "example.com"


def test_normalize_host_url() -> None:
    assert _normalize_host("https://example.com/path") == "example.com"
    assert _normalize_host("http://sub.example.com:8080/foo") == "sub.example.com"


def test_parse_banner_openssh() -> None:
    assert parse_banner("SSH-2.0-OpenSSH_7.2p2 Ubuntu-1ubuntu2.14") == (
        "OpenSSH",
        "7.2p2",
    )
    assert parse_banner("SSH-2.0-OpenSSH_8.9p1") == ("OpenSSH", "8.9p1")


def test_parse_banner_proftpd() -> None:
    assert parse_banner("220 ProFTPD 1.3.5 Server (Debian)") == (
        "ProFTPD",
        "1.3.5",
    )


def test_parse_banner_vsftpd() -> None:
    assert parse_banner("220 (vsFTPd 2.3.4)") == ("vsftpd", "2.3.4")


def test_parse_banner_pureftpd() -> None:
    assert parse_banner("220 Pure-FTPd 0.14.2") == ("Pure-FTPd", "0.14.2")


def test_parse_banner_dovecot() -> None:
    assert parse_banner("220 Dovecot ready") == (None, None)
    assert parse_banner("220 Dovecot 2.3.19 ready") == ("Dovecot", "2.3.19")


def test_parse_banner_unknown() -> None:
    assert parse_banner("220 FTP Server ready") == (None, None)
    assert parse_banner("") == (None, None)


def test_version_in_range() -> None:
    assert version_in_range("7.2", {"version_max": "7.3", "max_inclusive": False})
    assert not version_in_range("7.3", {"version_max": "7.3", "max_inclusive": False})
    assert version_in_range("7.3", {"version_max": "7.3", "max_inclusive": True})
    assert not version_in_range("7.2", {"version_min": "7.3", "min_inclusive": True})
    assert version_in_range("7.4", {"version_min": "7.3", "min_inclusive": False})
    assert not version_in_range("7.3", {"version_min": "7.3", "min_inclusive": False})
    assert version_in_range("2.3.4", {"version_min": "2.3.4", "version_max": "2.3.4"})
    assert version_in_range("1.4", {"version_min": "1.3.0", "min_inclusive": True})


def test_version_in_range_garbage() -> None:
    assert not version_in_range("abc", {"version_max": "9.9"})
    assert not version_in_range("", {"version_max": "9.9"})


def test_match_service_vulns_openssh_old() -> None:
    findings = match_service_vulns("OpenSSH", "7.2p2", port=22)
    ids = {finding["id"] for finding in findings}
    assert "CVE-2016-6210" in ids
    assert "CVE-2018-15473" in ids
    assert "CVE-2016-0777" not in ids
    assert all(finding["port"] == 22 for finding in findings)
    assert all(finding["product"] == "OpenSSH" for finding in findings)
    assert all(finding["version"] == "7.2p2" for finding in findings)


def test_match_service_vulns_openssh_new() -> None:
    assert match_service_vulns("OpenSSH", "8.9p1") == []


def test_match_service_vulns_proftpd() -> None:
    findings = match_service_vulns("ProFTPD", "1.3.5")
    assert [finding["id"] for finding in findings] == ["CVE-2015-3306"]
    assert findings[0]["severity"] == "critical"


def test_match_service_vulns_proftpd_new() -> None:
    assert match_service_vulns("ProFTPD", "1.3.6") == []


def test_match_service_vulns_vsftpd_backdoor() -> None:
    findings = match_service_vulns("vsftpd", "2.3.4")
    assert [finding["id"] for finding in findings] == ["VSFTPD-2.3.4-BACKDOOR"]
    assert findings[0]["severity"] == "critical"


def test_match_service_vulns_vsftpd_other() -> None:
    assert match_service_vulns("vsftpd", "3.0.5") == []


def test_match_service_vulns_no_version() -> None:
    assert match_service_vulns("OpenSSH", None) == []
    assert match_service_vulns(None, "7.2") == []
    assert match_service_vulns(None, None) == []


def test_match_service_vulns_case_insensitive() -> None:
    findings = match_service_vulns("openssh", "7.2")
    assert {finding["id"] for finding in findings} >= {"CVE-2016-6210"}


def test_match_protocol_vulns() -> None:
    findings = match_protocol_vulns(["SSLv3", "TLSv1_2"])
    assert [finding["id"] for finding in findings] == ["CVE-2014-3566"]
    assert findings[0]["protocol"] == "SSLv3"


def test_match_protocol_vulns_multiple() -> None:
    findings = match_protocol_vulns(["SSLv3", "TLSv1", "TLSv1_1", "TLSv1_3"])
    assert [finding["id"] for finding in findings] == [
        "CVE-2014-3566",
        "CVE-2011-3389",
        "DEPRECATED-TLS1.1",
    ]


def test_match_protocol_vulns_case_insensitive() -> None:
    findings = match_protocol_vulns(["sslv3"])
    assert [finding["id"] for finding in findings] == ["CVE-2014-3566"]


def test_match_cipher_vulns_rc4() -> None:
    findings = match_cipher_vulns(["RC4-SHA", "AES128-GCM-SHA256"])
    assert [finding["id"] for finding in findings] == ["CVE-2013-2566"]
    assert findings[0]["cipher"] == "RC4-SHA"


def test_match_cipher_vulns_des() -> None:
    findings = match_cipher_vulns(["DES-CBC3-SHA"])
    assert [finding["id"] for finding in findings] == ["CVE-2016-2183"]


def test_match_cipher_vulns_null() -> None:
    findings = match_cipher_vulns(["ECDHE-RSA-NULL-SHA"])
    assert [finding["id"] for finding in findings] == ["NULL-CIPHER"]


def test_match_cipher_vulns_export() -> None:
    findings = match_cipher_vulns(["EXP-IDEA-CBC-SHA"])
    assert [finding["id"] for finding in findings] == ["CVE-2015-0204"]


def test_match_cipher_vulns_export_rc4() -> None:
    findings = match_cipher_vulns(["EXP-RC4-MD5"])
    ids = [finding["id"] for finding in findings]
    assert "CVE-2013-2566" in ids
    assert "CVE-2015-0204" in ids


def test_match_cipher_vulns_modern() -> None:
    assert match_cipher_vulns(
        ["AES128-GCM-SHA256", "TLS_AES_256_GCM_SHA384", "ECDHE-RSA-AES256-SHA384"]
    ) == []


def test_match_certificate_vulns_weak_key() -> None:
    findings = match_certificate_vulns(
        {"key_size": 1024, "signature_algorithm": "sha256WithRSAEncryption"}
    )
    assert [finding["id"] for finding in findings] == ["WEAK-RSA-KEY"]
    assert findings[0]["key_size"] == 1024


def test_match_certificate_vulns_md5() -> None:
    findings = match_certificate_vulns(
        {"key_size": 2048, "signature_algorithm": "md5WithRSAEncryption"}
    )
    assert [finding["id"] for finding in findings] == ["MD5-SIGNATURE"]


def test_match_certificate_vulns_sha1() -> None:
    findings = match_certificate_vulns(
        {"key_size": 2048, "signature_algorithm": "sha1WithRSAEncryption"}
    )
    assert [finding["id"] for finding in findings] == ["SHA1-SIGNATURE"]


def test_match_certificate_vulns_sha256_not_sha1() -> None:
    assert match_certificate_vulns(
        {"key_size": 2048, "signature_algorithm": "sha256WithRSAEncryption"}
    ) == []


def test_match_certificate_vulns_strong() -> None:
    assert match_certificate_vulns(
        {"key_size": 4096, "signature_algorithm": "sha256WithRSAEncryption"}
    ) == []


def test_match_certificate_vulns_empty() -> None:
    assert match_certificate_vulns(None) == []
    assert match_certificate_vulns({}) == []


def test_match_tls_vulns() -> None:
    tls_data = {
        "supported_versions": ["TLSv1"],
        "supported_ciphers": ["AES128-SHA", "RC4-SHA"],
    }
    findings = match_tls_vulns(tls_data)
    ids = {finding["id"] for finding in findings}
    assert "CVE-2011-3389" in ids
    assert "CVE-2013-2566" in ids


def test_match_tls_vulns_empty() -> None:
    assert match_tls_vulns({}) == []


def test_match_ssl_vulns() -> None:
    ssl_data = {"cert": {"key_size": 1024}}
    findings = match_ssl_vulns(ssl_data)
    assert [finding["id"] for finding in findings] == ["WEAK-RSA-KEY"]


def test_match_ssl_vulns_empty() -> None:
    assert match_ssl_vulns({}) == []


def test_run_vuln_live_service_detection(monkeypatch) -> None:
    def mock_run_service(host, ports=None, timeout=3.0, max_workers=50):
        return {
            "target": host,
            "host": host,
            "results": [
                {"port": 22, "banner": "SSH-2.0-OpenSSH_7.2p2", "service": "OpenSSH"},
            ],
        }

    monkeypatch.setattr("ethscan.vuln.run_service", mock_run_service)

    results = run_vuln("example.com", timeout=1.0)
    assert results["host"] == "example.com"
    assert results["services_checked"] == 1
    assert results["tls_checked"] is False
    assert results["certificate_checked"] is False
    ids = {finding["id"] for finding in results["findings"]}
    assert "CVE-2016-6210" in ids
    assert "CVE-2018-15473" in ids
    assert results["finding_count"] == 2


def test_run_vuln_services_data_skips_live_detection(monkeypatch) -> None:
    def mock_run_service(host, ports=None, timeout=3.0, max_workers=50):
        raise AssertionError("run_service must not be called with services data")

    monkeypatch.setattr("ethscan.vuln.run_service", mock_run_service)

    services = {
        "target": "example.com",
        "host": "example.com",
        "results": [
            {"port": 21, "banner": "220 ProFTPD 1.3.5 Server (Debian)"},
        ],
    }
    results = run_vuln("example.com", services=services)
    assert results["services_checked"] == 1
    assert [finding["id"] for finding in results["findings"]] == ["CVE-2015-3306"]


def test_run_vuln_with_tls_and_certificate_data() -> None:
    services = {"results": [{"port": 22, "banner": "SSH-2.0-OpenSSH_8.9"}]}
    tls_data = {
        "supported_versions": ["TLSv1_2", "TLSv1_3"],
        "supported_ciphers": ["AES128-GCM-SHA256"],
    }
    certificate = {
        "cert": {"key_size": 2048, "signature_algorithm": "sha256WithRSAEncryption"}
    }
    results = run_vuln(
        "https://example.com",
        services=services,
        tls=tls_data,
        certificate=certificate,
    )
    assert results["host"] == "example.com"
    assert results["tls_checked"] is True
    assert results["certificate_checked"] is True
    assert results["finding_count"] == 0
    assert "No known vulnerabilities matched" in results["notes"]


def test_run_vuln_combined_findings() -> None:
    services = {
        "results": [
            {"port": 21, "banner": "220 (vsFTPd 2.3.4)"},
            {"port": 22, "banner": "SSH-2.0-OpenSSH_7.2p2"},
        ]
    }
    tls_data = {
        "supported_versions": ["SSLv3"],
        "supported_ciphers": ["RC4-SHA"],
    }
    certificate = {"cert": {"key_size": 1024}}
    results = run_vuln(
        "example.com",
        services=services,
        tls=tls_data,
        certificate=certificate,
    )
    ids = {finding["id"] for finding in results["findings"]}
    assert "VSFTPD-2.3.4-BACKDOOR" in ids
    assert "CVE-2016-6210" in ids
    assert "CVE-2018-15473" in ids
    assert "CVE-2014-3566" in ids
    assert "CVE-2013-2566" in ids
    assert "WEAK-RSA-KEY" in ids
    assert results["finding_count"] == 6
    assert results["severity_counts"]["critical"] == 1
    assert results["severity_counts"]["high"] == 2
    assert results["severity_counts"]["medium"] == 3
    assert results["severity_counts"]["low"] == 0


def test_run_vuln_severity_filter(monkeypatch) -> None:
    def mock_run_service(host, ports=None, timeout=3.0, max_workers=50):
        return {
            "results": [
                {"port": 22, "banner": "SSH-2.0-OpenSSH_7.2p2"},
                {"port": 21, "banner": "220 (vsFTPd 2.3.4)"},
            ]
        }

    monkeypatch.setattr("ethscan.vuln.run_service", mock_run_service)

    results = run_vuln("example.com", severity="critical")
    assert results["severity_filter"] == "critical"
    assert results["finding_count"] == 1
    assert all(finding["severity"] == "critical" for finding in results["findings"])
    assert results["findings"][0]["id"] == "VSFTPD-2.3.4-BACKDOOR"
    assert results["severity_counts"]["critical"] == 1
    assert results["severity_counts"]["medium"] == 0


def test_run_vuln_no_services(monkeypatch) -> None:
    def mock_run_service(host, ports=None, timeout=3.0, max_workers=50):
        return {"results": []}

    monkeypatch.setattr("ethscan.vuln.run_service", mock_run_service)

    results = run_vuln("example.com")
    assert results["services_checked"] == 0
    assert results["finding_count"] == 0
    assert "No service banners detected" in results["notes"]
    assert "No known vulnerabilities matched" in results["notes"]


def test_run_vuln_unparseable_banner(monkeypatch) -> None:
    def mock_run_service(host, ports=None, timeout=3.0, max_workers=50):
        return {"results": [{"port": 80, "banner": "HTTP/1.1 200 OK"}]}

    monkeypatch.setattr("ethscan.vuln.run_service", mock_run_service)

    results = run_vuln("example.com")
    assert results["services_checked"] == 1
    assert results["finding_count"] == 0


def test_run_vuln_ports_passed_through(monkeypatch) -> None:
    called_args = {}

    def mock_run_service(host, ports=None, timeout=3.0, max_workers=50):
        called_args["host"] = host
        called_args["ports"] = ports
        called_args["timeout"] = timeout
        called_args["max_workers"] = max_workers
        return {"results": []}

    monkeypatch.setattr("ethscan.vuln.run_service", mock_run_service)

    run_vuln("example.com", ports=[22, 80], timeout=1.5, max_workers=10)
    assert called_args["host"] == "example.com"
    assert called_args["ports"] == [22, 80]
    assert called_args["timeout"] == 1.5
    assert called_args["max_workers"] == 10


def test_format_vuln_report_json() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 3.0,
        "ports": None,
        "services_checked": 1,
        "tls_checked": False,
        "certificate_checked": False,
        "severity_filter": None,
        "findings": [
            {
                "id": "CVE-2018-15473",
                "kind": "service",
                "title": "OpenSSH user enumeration",
                "severity": "medium",
                "description": "OpenSSH before 7.7 allows user enumeration.",
                "product": "OpenSSH",
                "version": "7.2p2",
                "port": 22,
            }
        ],
        "finding_count": 1,
        "severity_counts": {"critical": 0, "high": 0, "medium": 1, "low": 0},
        "notes": [],
    }
    output = format_vuln_report_json(data)
    parsed = json.loads(output)
    assert parsed["finding_count"] == 1
    assert parsed["findings"][0]["id"] == "CVE-2018-15473"
    assert parsed["severity_counts"]["medium"] == 1


def test_format_vuln_report_markdown() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "services_checked": 1,
        "tls_checked": True,
        "certificate_checked": False,
        "finding_count": 1,
        "severity_counts": {"critical": 0, "high": 0, "medium": 1, "low": 0},
        "findings": [
            {
                "id": "CVE-2018-15473",
                "kind": "service",
                "title": "OpenSSH user enumeration",
                "severity": "medium",
                "description": "OpenSSH before 7.7 allows user enumeration.",
                "product": "OpenSSH",
                "version": "7.2p2",
                "port": 22,
            }
        ],
        "notes": [],
    }
    output = format_vuln_report_markdown(data)
    assert "# ethscan Vulnerability Report" in output
    assert "- **Target:** example.com" in output
    assert "- **Services Checked:** 1" in output
    assert "- **TLS Checked:** Yes" in output
    assert "- **Certificate Checked:** No" in output
    assert "## Severity Summary" in output
    assert "**Medium:** 1" in output
    assert "### CVE-2018-15473 (MEDIUM)" in output
    assert "- **Type:** service" in output
    assert "- **Details:** OpenSSH 7.2p2 (port 22)" in output
    assert "- **Title:** OpenSSH user enumeration" in output


def test_format_vuln_report_markdown_no_findings() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "services_checked": 0,
        "tls_checked": False,
        "certificate_checked": False,
        "finding_count": 0,
        "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "findings": [],
        "notes": ["No service banners detected"],
    }
    output = format_vuln_report_markdown(data)
    assert "*No known vulnerabilities matched.*" in output
    assert "## Notes" in output
    assert "- No service banners detected" in output


def test_format_vuln_report_markdown_escapes_pipes() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "services_checked": 0,
        "tls_checked": False,
        "certificate_checked": False,
        "finding_count": 1,
        "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 1},
        "findings": [
            {
                "id": "TEST-1",
                "kind": "protocol",
                "title": "A | B",
                "severity": "low",
                "description": "contains | pipe",
                "protocol": "TLSv1_1",
            }
        ],
        "notes": [],
    }
    output = format_vuln_report_markdown(data)
    assert "A \\| B" in output
    assert "contains \\| pipe" in output


def test_format_vuln_report_markdown_detail_variants() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "services_checked": 0,
        "tls_checked": True,
        "certificate_checked": True,
        "finding_count": 3,
        "severity_counts": {"critical": 1, "high": 1, "medium": 1, "low": 0},
        "findings": [
            {
                "id": "CVE-2014-3566",
                "kind": "protocol",
                "title": "POODLE",
                "severity": "high",
                "description": "SSLv3 POODLE.",
                "protocol": "SSLv3",
            },
            {
                "id": "CVE-2013-2566",
                "kind": "cipher",
                "title": "RC4 weak",
                "severity": "high",
                "description": "RC4 is weak.",
                "cipher": "RC4-SHA",
            },
            {
                "id": "WEAK-RSA-KEY",
                "kind": "certificate",
                "title": "Weak key",
                "severity": "medium",
                "description": "Key too small.",
                "key_size": 1024,
            },
        ],
        "notes": [],
    }
    output = format_vuln_report_markdown(data)
    assert "- **Details:** SSLv3" in output
    assert "- **Details:** RC4-SHA" in output
    assert "- **Details:** key size 1024 bits" in output


def test_severity_rank() -> None:
    assert _severity_rank("critical") == 3
    assert _severity_rank("high") == 2
    assert _severity_rank("medium") == 1
    assert _severity_rank("low") == 0


def test_severity_rank_case_insensitive() -> None:
    assert _severity_rank("CRITICAL") == 3
    assert _severity_rank("High") == 2


def test_severity_rank_unknown() -> None:
    assert _severity_rank("unknown") is None
    assert _severity_rank(None) is None
    assert _severity_rank("") is None


def test_run_vuln_min_severity_drops_lower(monkeypatch) -> None:
    def mock_run_service(host, ports=None, timeout=3.0, max_workers=50):
        return {
            "results": [
                {"port": 22, "banner": "SSH-2.0-OpenSSH_7.2p2"},
                {"port": 21, "banner": "220 (vsFTPd 2.3.4)"},
            ]
        }

    monkeypatch.setattr("ethscan.vuln.run_service", mock_run_service)

    results = run_vuln("example.com", min_severity="high")
    assert results["min_severity_filter"] == "high"
    # OpenSSH 7.2p2 matches medium findings, vsFTPd 2.3.4 is critical
    # min_severity=high should drop the medium findings
    for finding in results["findings"]:
        assert finding["severity"] in ("high", "critical")
    assert results["severity_counts"]["medium"] == 0
    assert results["severity_counts"]["critical"] == 1


def test_run_vuln_min_severity_none_keeps_all(monkeypatch) -> None:
    def mock_run_service(host, ports=None, timeout=3.0, max_workers=50):
        return {
            "results": [
                {"port": 22, "banner": "SSH-2.0-OpenSSH_7.2p2"},
                {"port": 21, "banner": "220 (vsFTPd 2.3.4)"},
            ]
        }

    monkeypatch.setattr("ethscan.vuln.run_service", mock_run_service)

    results = run_vuln("example.com")
    assert results["min_severity_filter"] is None
    assert results["finding_count"] >= 1
    assert results["severity_counts"]["medium"] >= 1


def test_run_vuln_min_severity_low_keeps_all(monkeypatch) -> None:
    def mock_run_service(host, ports=None, timeout=3.0, max_workers=50):
        return {
            "results": [
                {"port": 22, "banner": "SSH-2.0-OpenSSH_7.2p2"},
                {"port": 21, "banner": "220 (vsFTPd 2.3.4)"},
            ]
        }

    monkeypatch.setattr("ethscan.vuln.run_service", mock_run_service)

    results = run_vuln("example.com", min_severity="low")
    assert results["min_severity_filter"] == "low"
    assert results["finding_count"] >= 1
    assert results["severity_counts"]["medium"] >= 1


def test_run_vuln_min_severity_critical_drops_all(monkeypatch) -> None:
    def mock_run_service(host, ports=None, timeout=3.0, max_workers=50):
        return {
            "results": [
                {"port": 22, "banner": "SSH-2.0-OpenSSH_7.2p2"},
            ]
        }

    monkeypatch.setattr("ethscan.vuln.run_service", mock_run_service)

    results = run_vuln("example.com", min_severity="critical")
    assert results["min_severity_filter"] == "critical"
    assert results["finding_count"] == 0


def test_format_vuln_report_markdown_with_min_severity() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "services_checked": 1,
        "tls_checked": False,
        "certificate_checked": False,
        "finding_count": 1,
        "severity_counts": {"critical": 0, "high": 0, "medium": 1, "low": 0},
        "severity_filter": None,
        "min_severity_filter": "high",
        "findings": [],
        "notes": [],
    }
    output = format_vuln_report_markdown(data)
    assert "Min Severity" in output
    assert "high" in output


def test_format_vuln_report_json_includes_min_severity() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "services_checked": 1,
        "tls_checked": False,
        "certificate_checked": False,
        "finding_count": 1,
        "severity_counts": {"critical": 0, "high": 0, "medium": 1, "low": 0},
        "severity_filter": None,
        "min_severity_filter": "high",
        "findings": [],
        "notes": [],
    }
    output = format_vuln_report_json(data)
    parsed = json.loads(output)
    assert parsed["min_severity_filter"] == "high"


def test_extract_hosts_from_banner_hostname() -> None:
    from ethscan.vuln import _extract_hosts_from_banner

    banner = "Server: nginx/1.18.0 (Ubuntu) via proxy.example.com"
    hosts = _extract_hosts_from_banner(banner)
    assert "proxy.example.com" in hosts


def test_extract_hosts_from_banner_ip() -> None:
    from ethscan.vuln import _extract_hosts_from_banner

    banner = "Connected to 192.168.1.100 on port 8080"
    hosts = _extract_hosts_from_banner(banner)
    assert "192.168.1.100" in hosts


def test_extract_hosts_from_banner_multiple() -> None:
    from ethscan.vuln import _extract_hosts_from_banner

    banner = "Backend: api.internal.example.com, db.internal.example.com, 10.0.0.50"
    hosts = _extract_hosts_from_banner(banner)
    assert "api.internal.example.com" in hosts
    assert "db.internal.example.com" in hosts
    assert "10.0.0.50" in hosts


def test_extract_hosts_from_banner_dedup() -> None:
    from ethscan.vuln import _extract_hosts_from_banner

    banner = "Host: example.com and example.com again"
    hosts = _extract_hosts_from_banner(banner)
    assert hosts.count("example.com") == 1


def test_run_vuln_recursive_disabled_by_default(monkeypatch) -> None:
    def mock_run_service(host, ports=None, timeout=3.0, max_workers=50):
        return {
            "results": [
                {"port": 22, "banner": "SSH-2.0-OpenSSH_7.2p2", "service": "OpenSSH"},
            ]
        }

    monkeypatch.setattr("ethscan.vuln.run_service", mock_run_service)

    results = run_vuln("example.com")
    assert results["recursive"] is False
    assert results["max_depth"] == 0
    assert results["recursive_hosts_scanned"] == []
    assert results["recursive_findings"] == []


def test_run_vuln_recursive_enabled(monkeypatch) -> None:
    call_count = {"count": 0}

    def mock_run_service(host, ports=None, timeout=3.0, max_workers=50):
        call_count["count"] += 1
        if host == "example.com":
            return {
                "results": [
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
    assert results["recursive"] is True
    assert results["max_depth"] == 1
    assert "backend.internal.example.com" in results["recursive_hosts_scanned"]
    assert len(results["recursive_findings"]) >= 1
    # Should have findings from both hosts
    assert results["finding_count"] >= 2
    # Should have called run_service twice (once for each host)
    assert call_count["count"] == 2


def test_run_vuln_recursive_respects_max_depth(monkeypatch) -> None:
    call_count = {"count": 0}

    def mock_run_service(host, ports=None, timeout=3.0, max_workers=50):
        call_count["count"] += 1
        if host == "example.com":
            return {
                "results": [
                    {"port": 80, "banner": "Server: nginx via backend.internal.example.com", "service": "nginx"},
                ]
            }
        elif host == "backend.internal.example.com":
            return {
                "results": [
                    {"port": 80, "banner": "Server: apache via deeper.internal.example.com", "service": "apache"},
                ]
            }
        elif host == "deeper.internal.example.com":
            return {
                "results": [
                    {"port": 22, "banner": "SSH-2.0-OpenSSH_7.2p2", "service": "OpenSSH"},
                ]
            }
        return {"results": []}

    monkeypatch.setattr("ethscan.vuln.run_service", mock_run_service)

    results = run_vuln("example.com", recursive=True, max_depth=1)
    # Should only scan example.com (depth 0) and backend.internal.example.com (depth 1)
    # Should NOT scan deeper.internal.example.com (depth 2)
    assert "deeper.internal.example.com" not in results["recursive_hosts_scanned"]
    assert call_count["count"] == 2


def test_run_vuln_recursive_stops_when_no_new_hosts(monkeypatch) -> None:
    def mock_run_service(host, ports=None, timeout=3.0, max_workers=50):
        if host == "example.com":
            return {
                "results": [
                    {"port": 80, "banner": "Server: nginx", "service": "nginx"},
                ]
            }
        return {"results": []}

    monkeypatch.setattr("ethscan.vuln.run_service", mock_run_service)

    results = run_vuln("example.com", recursive=True, max_depth=2)
    # No hosts discovered in banners, so no recursive scans
    assert results["recursive_hosts_scanned"] == []


def test_format_vuln_report_markdown_with_recursive() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "services_checked": 1,
        "tls_checked": False,
        "certificate_checked": False,
        "finding_count": 2,
        "severity_counts": {"critical": 0, "high": 0, "medium": 2, "low": 0},
        "severity_filter": None,
        "min_severity_filter": None,
        "findings": [
            {
                "id": "CVE-2018-15473",
                "kind": "service",
                "title": "OpenSSH user enumeration",
                "severity": "medium",
                "description": "OpenSSH before 7.7 allows user enumeration.",
                "product": "OpenSSH",
                "version": "7.2p2",
                "port": 22,
            },
            {
                "id": "CVE-2016-6210",
                "kind": "service",
                "title": "OpenSSH user enumeration timing",
                "severity": "medium",
                "description": "OpenSSH timing attack.",
                "product": "OpenSSH",
                "version": "7.2p2",
                "port": 22,
            },
        ],
        "notes": [],
        "recursive": True,
        "max_depth": 1,
        "recursive_hosts_scanned": ["backend.internal.example.com"],
        "recursive_findings": [
            {
                "host": "backend.internal.example.com",
                "depth": 1,
                "finding_count": 1,
                "services_checked": 1,
                "severity_counts": {"critical": 0, "high": 0, "medium": 1, "low": 0},
                "findings": [
                    {
                        "id": "VSFTPD-2.3.4-BACKDOOR",
                        "kind": "service",
                        "title": "vsftpd backdoor",
                        "severity": "critical",
                        "description": "vsftpd 2.3.4 backdoor.",
                        "product": "vsftpd",
                        "version": "2.3.4",
                        "port": 21,
                    }
                ],
            }
        ],
    }
    output = format_vuln_report_markdown(data)
    assert "**Recursive:** Yes" in output
    assert "**Max Depth:** 1" in output
    assert "**Recursive Hosts Scanned:** 1" in output
    assert "## Recursive Scan Results" in output
    assert "backend.internal.example.com" in output
    assert "VSFTPD-2.3.4-BACKDOOR" in output


def test_format_vuln_report_json_includes_recursive() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "services_checked": 1,
        "tls_checked": False,
        "certificate_checked": False,
        "finding_count": 1,
        "severity_counts": {"critical": 0, "high": 0, "medium": 1, "low": 0},
        "severity_filter": None,
        "min_severity_filter": None,
        "findings": [],
        "notes": [],
        "recursive": True,
        "max_depth": 2,
        "recursive_hosts_scanned": ["host1.example.com", "host2.example.com"],
        "recursive_findings": [
            {"host": "host1.example.com", "depth": 1, "finding_count": 1},
            {"host": "host2.example.com", "depth": 1, "finding_count": 0},
        ],
    }
    output = format_vuln_report_json(data)
    parsed = json.loads(output)
    assert parsed["recursive"] is True
    assert parsed["max_depth"] == 2
    assert len(parsed["recursive_hosts_scanned"]) == 2
    assert len(parsed["recursive_findings"]) == 2


# ---------------------------------------------------------------------------
# Salt/pepper banner matching
# ---------------------------------------------------------------------------


def _mock_service_with_banner(banner: str):
    def _inner(host, ports=None, timeout=3.0, max_workers=50):
        return {"results": [{"port": 22, "banner": banner}]}

    return _inner


def test_transform_banner_no_salt_no_pepper() -> None:
    from ethscan.vuln import _transform_banner

    assert _transform_banner("SSH-2.0-OpenSSH_7.2p2", "sha256") == "SSH-2.0-OpenSSH_7.2p2"


def test_transform_banner_salt_only() -> None:
    import hashlib

    from ethscan.vuln import _transform_banner

    expected = hashlib.new("sha256", ("salt" + "SSH-2.0-OpenSSH_7.2p2").encode("utf-8")).hexdigest()
    assert _transform_banner("SSH-2.0-OpenSSH_7.2p2", "sha256", salt="salt") == expected


def test_transform_banner_pepper_only() -> None:
    import hmac

    from ethscan.vuln import _transform_banner

    expected = hmac.new(b"pepper", b"SSH-2.0-OpenSSH_7.2p2", "sha256").hexdigest()
    assert _transform_banner("SSH-2.0-OpenSSH_7.2p2", "sha256", pepper="pepper") == expected


def test_transform_banner_salt_and_pepper() -> None:
    import hmac

    from ethscan.vuln import _transform_banner

    expected = hmac.new(b"pepper", (b"salt" + b"SSH-2.0-OpenSSH_7.2p2"), "sha256").hexdigest()
    assert (
        _transform_banner(
            "SSH-2.0-OpenSSH_7.2p2", "sha256", salt="salt", pepper="pepper"
        )
        == expected
    )


def test_transform_banner_empty_banner() -> None:
    from ethscan.vuln import _transform_banner

    assert _transform_banner("", "sha256", salt="salt") == ""


def test_run_vuln_salt_flags_salt_field(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.vuln.run_service", _mock_service_with_banner("SSH-2.0-OpenSSH_7.2p2"))
    results = run_vuln("example.com", salt="salt")
    assert results["salt"] is True
    assert results["pepper"] is False
    assert results["algorithm"] == "sha256"


def test_run_vuln_pepper_flags_pepper_field(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.vuln.run_service", _mock_service_with_banner("SSH-2.0-OpenSSH_7.2p2"))
    results = run_vuln("example.com", pepper="pepper")
    assert results["salt"] is False
    assert results["pepper"] is True


def test_run_vuln_algorithm_field_echoed(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.vuln.run_service", _mock_service_with_banner("SSH-2.0-OpenSSH_7.2p2"))
    results = run_vuln("example.com", algorithm="md5")
    assert results["algorithm"] == "md5"


def test_run_vuln_salt_defaults_to_none(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.vuln.run_service", _mock_service_with_banner("SSH-2.0-OpenSSH_7.2p2"))
    results = run_vuln("example.com")
    assert results["salt"] is False
    assert results["pepper"] is False


def test_format_vuln_report_markdown_with_salt() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "services_checked": 1,
        "tls_checked": False,
        "certificate_checked": False,
        "finding_count": 0,
        "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "severity_filter": None,
        "min_severity_filter": None,
        "findings": [],
        "notes": [],
        "salt": True,
        "pepper": False,
        "algorithm": "sha256",
    }
    output = format_vuln_report_markdown(data)
    assert "**Salt:** applied" in output
    assert "**Pepper:**" not in output
    assert "**Algorithm:** sha256" in output


def test_format_vuln_report_markdown_with_pepper() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "services_checked": 1,
        "tls_checked": False,
        "certificate_checked": False,
        "finding_count": 0,
        "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "severity_filter": None,
        "min_severity_filter": None,
        "findings": [],
        "notes": [],
        "salt": False,
        "pepper": True,
        "algorithm": "sha256",
    }
    output = format_vuln_report_markdown(data)
    assert "**Pepper:** applied" in output
    assert "**Salt:**" not in output


def test_format_vuln_report_json_includes_salt_pepper() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "services_checked": 1,
        "tls_checked": False,
        "certificate_checked": False,
        "finding_count": 0,
        "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "severity_filter": None,
        "min_severity_filter": None,
        "findings": [],
        "notes": [],
        "salt": True,
        "pepper": True,
        "algorithm": "sha256",
    }
    output = format_vuln_report_json(data)
    parsed = json.loads(output)
    assert parsed["salt"] is True
    assert parsed["pepper"] is True
    assert parsed["algorithm"] == "sha256"


def test_format_vuln_report_csv() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "services_checked": 1,
        "tls_checked": False,
        "certificate_checked": False,
        "finding_count": 2,
        "severity_counts": {"critical": 0, "high": 0, "medium": 1, "low": 1},
        "findings": [
            {
                "id": "CVE-2018-15473",
                "kind": "service",
                "title": "OpenSSH user enumeration",
                "severity": "medium",
                "description": "OpenSSH before 7.7 allows user enumeration.",
                "product": "OpenSSH",
                "version": "7.2p2",
                "port": 22,
            },
            {
                "id": "CVE-2014-3566",
                "kind": "protocol",
                "title": "SSLv3 is vulnerable to POODLE",
                "severity": "high",
                "description": "SSLv3 supports CBC-mode ciphers.",
                "protocol": "SSLv3",
            },
        ],
        "notes": [],
    }
    output = format_vuln_report_csv(data)
    lines = output.strip().split("\n")
    header = lines[0]
    assert "id,type,severity,product,version,port,title,description" in header
    # First finding row (service kind - has product/version/port)
    row1 = lines[1]
    assert "CVE-2018-15473" in row1
    assert "service" in row1
    assert "medium" in row1
    assert "OpenSSH" in row1
    assert "7.2p2" in row1
    assert "22" in row1
    # Second finding row (protocol kind - no product/version/port)
    row2 = lines[2]
    assert "CVE-2014-3566" in row2
    assert "protocol" in row2
    assert "high" in row2
    assert "SSLv3 is vulnerable to POODLE" in row2


def test_format_vuln_report_csv_no_findings() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "services_checked": 0,
        "tls_checked": False,
        "certificate_checked": False,
        "finding_count": 0,
        "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "findings": [],
        "notes": [],
    }
    output = format_vuln_report_csv(data)
    lines = output.strip().split("\n")
    assert lines[0] == "id,type,severity,product,version,port,title,description"
    assert len(lines) == 1  # header only, no finding rows


def test_format_vuln_report_csv_missing_optional_fields() -> None:
    """CSV formatter handles findings with missing optional fields gracefully."""
    data = {
        "target": "example.com",
        "host": "example.com",
        "services_checked": 0,
        "tls_checked": False,
        "certificate_checked": False,
        "finding_count": 1,
        "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "findings": [
            {
                "id": "TEST-1",
                "kind": "cipher",
                "title": "Weak cipher",
                "severity": "high",
                "description": "Weak cipher detected",
            },
        ],
        "notes": [],
    }
    output = format_vuln_report_csv(data)
    lines = output.strip().split("\n")
    assert len(lines) == 2  # header + 1 finding
    row = lines[1]
    assert "TEST-1" in row
    assert "cipher" in row
    assert "high" in row


# ---------------------------------------------------------------------------
# _compute_password_hash direct tests
# ---------------------------------------------------------------------------


def test_compute_password_hash_no_salt_no_pepper() -> None:
    import hashlib

    expected = hashlib.new("sha256", b"hello world").hexdigest()
    assert _compute_password_hash("hello world", "sha256") == expected


def test_compute_password_hash_salt_only() -> None:
    import hashlib

    expected = hashlib.new("sha256", ("salt" + "hello world").encode("utf-8")).hexdigest()
    assert _compute_password_hash("hello world", "sha256", salt="salt") == expected


def test_compute_password_hash_pepper_only() -> None:
    import hmac

    expected = hmac.new(b"pepper", b"hello world", "sha256").hexdigest()
    assert _compute_password_hash("hello world", "sha256", pepper="pepper") == expected


def test_compute_password_hash_salt_and_pepper() -> None:
    import hmac

    expected = hmac.new(b"pepper", (b"salt" + b"hello world"), "sha256").hexdigest()
    assert (
        _compute_password_hash("hello world", "sha256", salt="salt", pepper="pepper")
        == expected
    )


def test_compute_password_hash_unsupported_algorithm_with_pepper() -> None:
    try:
        _compute_password_hash("hello world", "md4", pepper="pepper")
    except ValueError as exc:
        assert "does not support HMAC" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unsupported algorithm with pepper")


# ---------------------------------------------------------------------------
# _compute_peppered_hash direct tests
# ---------------------------------------------------------------------------


def test_compute_peppered_hash_unsupported_algorithm() -> None:
    try:
        _compute_peppered_hash("message", "md4", "pepper")
    except ValueError as exc:
        assert "does not support HMAC" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unsupported algorithm")


# ---------------------------------------------------------------------------
# _transform_banner error path
# ---------------------------------------------------------------------------


def test_transform_banner_salt_and_pepper_unsupported_algorithm() -> None:
    try:
        _transform_banner("SSH-2.0-OpenSSH_7.2p2", "md4", salt="salt", pepper="pepper")
    except ValueError as exc:
        assert "does not support HMAC" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unsupported algorithm")


# ---------------------------------------------------------------------------
# _apply_salt_pepper_to_banner graceful fallback
# ---------------------------------------------------------------------------


def test_apply_salt_pepper_to_banner_unsupported_algorithm_returns_banner() -> None:
    assert (
        _apply_salt_pepper_to_banner("SSH-2.0-OpenSSH_7.2p2", "salt", "pepper", "md4")
        == "SSH-2.0-OpenSSH_7.2p2"
    )


def test_apply_salt_pepper_to_banner_no_salt_no_pepper_returns_banner() -> None:
    assert (
        _apply_salt_pepper_to_banner("SSH-2.0-OpenSSH_7.2p2", None, None, "sha256")
        == "SSH-2.0-OpenSSH_7.2p2"
    )


# ---------------------------------------------------------------------------
# _finding_detail certificate paths
# ---------------------------------------------------------------------------


def test_finding_detail_certificate_signature_only() -> None:
    from ethscan.vuln import _finding_detail

    assert _finding_detail(
        {"kind": "certificate", "signature_algorithm": "md5WithRSAEncryption"}
    ) == "signature algorithm md5WithRSAEncryption"


def test_finding_detail_certificate_no_fields() -> None:
    from ethscan.vuln import _finding_detail

    assert _finding_detail({"kind": "certificate"}) == ""


# ---------------------------------------------------------------------------
# format_vuln_report_markdown severity_filter line
# ---------------------------------------------------------------------------


def test_format_vuln_report_markdown_with_severity_filter() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "services_checked": 1,
        "tls_checked": False,
        "certificate_checked": False,
        "finding_count": 0,
        "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "severity_filter": "critical",
        "min_severity_filter": None,
        "findings": [],
        "notes": [],
    }
    output = format_vuln_report_markdown(data)
    assert "**Severity Filter:** critical" in output


# ---------------------------------------------------------------------------
# format_vuln_report_markdown recursive "no findings" branch
# ---------------------------------------------------------------------------


def test_format_vuln_report_markdown_recursive_findings_no_vulnerabilities() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "services_checked": 1,
        "tls_checked": False,
        "certificate_checked": False,
        "finding_count": 0,
        "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "recursive": True,
        "max_depth": 1,
        "recursive_hosts_scanned": ["backend.internal.example.com"],
        "recursive_findings": [
            {
                "host": "backend.internal.example.com",
                "depth": 1,
                "finding_count": 0,
                "services_checked": 1,
                "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
                "findings": [],
            }
        ],
        "findings": [],
        "notes": [],
    }
    output = format_vuln_report_markdown(data)
    assert "**Recursive:** Yes" in output
    assert "## Recursive Scan Results" in output
    assert "backend.internal.example.com" in output
    assert "*No vulnerabilities found.*" in output


def test_finding_detail_fallback_empty() -> None:
    """Hit the final fallback return in _finding_detail for unknown kinds (line ~1047)."""
    from ethscan.vuln import _finding_detail

    assert _finding_detail({"kind": "nonexistent"}) == ""
    assert _finding_detail({}) == ""
