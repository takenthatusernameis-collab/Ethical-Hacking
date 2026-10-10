"""Tests for the ethscan tls module."""

import ssl

import pytest

from ethscan.tls import (
    COMMON_CIPHERS,
    DEFAULT_PORT,
    DEFAULT_TIMEOUT,
    DEFAULT_WORKERS,
    OBSOLETE_VERSIONS,
    TLS_VERSIONS,
    _normalize_host,
    _resolve_version,
    enumerate_tls,
    format_tls_report_json,
    format_tls_report_markdown,
    run_tls,
    probe_cipher,
    probe_version,
)


def test_defaults() -> None:
    assert DEFAULT_PORT == 443
    assert DEFAULT_TIMEOUT == 5.0
    assert DEFAULT_WORKERS == 10
    assert len(TLS_VERSIONS) == 4
    assert len(COMMON_CIPHERS) > 0
    assert "TLSv1_2" in OBSOLETE_VERSIONS or "TLSv1_2" not in OBSOLETE_VERSIONS


def test_normalize_host_bare() -> None:
    assert _normalize_host("example.com") == "example.com"
    assert _normalize_host("EXAMPLE.COM") == "example.com"


def test_normalize_host_url() -> None:
    assert _normalize_host("https://example.com/path") == "example.com"
    assert _normalize_host("http://sub.example.com:8080/foo") == "sub.example.com"


def test_resolve_version_members() -> None:
    assert _resolve_version(ssl.TLSVersion.TLSv1_2) == ssl.TLSVersion.TLSv1_2


def test_resolve_version_aliases() -> None:
    assert _resolve_version("TLSv1") == ssl.TLSVersion.TLSv1
    assert _resolve_version("tlsv1") == ssl.TLSVersion.TLSv1
    assert _resolve_version("TLSv1_1") == ssl.TLSVersion.TLSv1_1
    assert _resolve_version("tls1.2") == ssl.TLSVersion.TLSv1_2
    assert _resolve_version("TLSV1.3") == ssl.TLSVersion.TLSv1_3


def test_resolve_version_invalid() -> None:
    with pytest.raises(ValueError):
        _resolve_version("TLSv9")


def test_test_version_connection_refused() -> None:
    result = probe_version("127.0.0.1", 9999, ssl.TLSVersion.TLSv1_2, timeout=0.5)
    assert result["version"] == "TLSv1_2"
    assert result["supported"] is False
    assert result["error"] is not None
    assert result["negotiated_cipher"] is None
    assert result["negotiated_protocol"] is None


def test_test_version_invalid_spec() -> None:
    result = probe_version("127.0.0.1", 9999, "BOGUS", timeout=0.5)
    assert result["version"] == "BOGUS"
    assert result["supported"] is False
    assert "unknown TLS version" in result["error"]


def test_test_cipher_connection_refused() -> None:
    result = probe_cipher("127.0.0.1", 9999, "AES128-GCM-SHA256", timeout=0.5)
    assert result["cipher"] == "AES128-GCM-SHA256"
    assert result["supported"] is False
    assert result["error"] is not None
    assert result["negotiated_version"] is None


def test_test_cipher_not_locally_selectable() -> None:
    """TLS 1.3 cipher names cannot be pinned via set_ciphers on stdlib OpenSSL."""
    result = probe_cipher("127.0.0.1", 9999, "TLS_AES_128_GCM_SHA256", timeout=0.5)
    assert result["cipher"] == "TLS_AES_128_GCM_SHA256"
    assert result["supported"] is False
    assert result["error"] is not None


def test_test_cipher_invalid_name() -> None:
    result = probe_cipher("127.0.0.1", 9999, "NOT-A-CIPHER", timeout=0.5)
    assert result["supported"] is False
    assert result["error"] is not None


def test_run_tls_offline(monkeypatch) -> None:
    def mock_probe_version(host, port, version, timeout=DEFAULT_TIMEOUT):
        name = version.name if isinstance(version, ssl.TLSVersion) else str(version)
        if name in ("TLSv1_2", "TLSv1_3"):
            return {
                "version": name,
                "supported": True,
                "error": None,
                "negotiated_cipher": "AES128-GCM-SHA256",
                "negotiated_protocol": name.replace("TLSv", "TLSv"),
            }
        return {
            "version": name,
            "supported": False,
            "error": "handshake failure",
            "negotiated_cipher": None,
            "negotiated_protocol": None,
        }

    def mock_probe_cipher(host, port, cipher, timeout=DEFAULT_TIMEOUT):
        supported = cipher.startswith("ECDHE")
        return {
            "cipher": cipher,
            "supported": supported,
            "error": None if supported else "handshake failure",
            "negotiated_version": "TLSv1.2" if supported else None,
        }

    monkeypatch.setattr("ethscan.tls.probe_version", mock_probe_version)
    monkeypatch.setattr("ethscan.tls.probe_cipher", mock_probe_cipher)

    result = run_tls("example.com", timeout=1.0, max_workers=4)

    assert result["target"] == "example.com"
    assert result["host"] == "example.com"
    assert result["port"] == DEFAULT_PORT
    assert result["versions_tested"] == 4
    assert result["ciphers_tested"] == len(COMMON_CIPHERS)
    assert result["supported_versions"] == ["TLSv1_2", "TLSv1_3"]
    assert result["supported_version_count"] == 2
    assert result["supported_cipher_count"] > 0
    assert all(c.startswith("ECDHE") for c in result["supported_ciphers"])

    versions = {v["version"]: v for v in result["versions"]}
    assert versions["TLSv1"]["supported"] is False
    assert versions["TLSv1_2"]["supported"] is True
    assert versions["TLSv1_2"]["negotiated_cipher"] == "AES128-GCM-SHA256"

    ciphers = {c["cipher"]: c for c in result["ciphers"]}
    assert ciphers["ECDHE-RSA-AES128-GCM-SHA256"]["supported"] is True
    assert ciphers["AES128-SHA"]["supported"] is False


def test_run_tls_target_normalization(monkeypatch) -> None:
    def mock_probe_version(host, port, version, timeout=DEFAULT_TIMEOUT):
        return {
            "version": version.name,
            "supported": False,
            "error": "connection refused",
            "negotiated_cipher": None,
            "negotiated_protocol": None,
        }

    def mock_probe_cipher(host, port, cipher, timeout=DEFAULT_TIMEOUT):
        return {
            "cipher": cipher,
            "supported": False,
            "error": "connection refused",
            "negotiated_version": None,
        }

    monkeypatch.setattr("ethscan.tls.probe_version", mock_probe_version)
    monkeypatch.setattr("ethscan.tls.probe_cipher", mock_probe_cipher)

    result = run_tls("https://example.com/path", port=8443, timeout=1.0)

    assert result["host"] == "example.com"
    assert result["target"] == "https://example.com/path"
    assert result["port"] == 8443


def test_run_tls_default_versions_and_ciphers(monkeypatch) -> None:
    called_versions = []
    called_ciphers = []

    def mock_probe_version(host, port, version, timeout=DEFAULT_TIMEOUT):
        called_versions.append(version)
        return {
            "version": version.name,
            "supported": False,
            "error": "connection refused",
            "negotiated_cipher": None,
            "negotiated_protocol": None,
        }

    def mock_probe_cipher(host, port, cipher, timeout=DEFAULT_TIMEOUT):
        called_ciphers.append(cipher)
        return {
            "cipher": cipher,
            "supported": False,
            "error": "connection refused",
            "negotiated_version": None,
        }

    monkeypatch.setattr("ethscan.tls.probe_version", mock_probe_version)
    monkeypatch.setattr("ethscan.tls.probe_cipher", mock_probe_cipher)

    run_tls("example.com", timeout=1.0, max_workers=2)

    assert called_versions == TLS_VERSIONS
    assert called_ciphers == COMMON_CIPHERS


def test_run_tls_custom_versions_and_ciphers(monkeypatch) -> None:
    called_versions = []
    called_ciphers = []

    def mock_probe_version(host, port, version, timeout=DEFAULT_TIMEOUT):
        called_versions.append(version)
        return {
            "version": version.name,
            "supported": True,
            "error": None,
            "negotiated_cipher": "AES128-GCM-SHA256",
            "negotiated_protocol": "TLSv1.2",
        }

    def mock_probe_cipher(host, port, cipher, timeout=DEFAULT_TIMEOUT):
        called_ciphers.append(cipher)
        return {
            "cipher": cipher,
            "supported": True,
            "error": None,
            "negotiated_version": "TLSv1.2",
        }

    monkeypatch.setattr("ethscan.tls.probe_version", mock_probe_version)
    monkeypatch.setattr("ethscan.tls.probe_cipher", mock_probe_cipher)

    result = run_tls(
        "example.com",
        timeout=1.0,
        versions=["TLSv1_2", "tls1.3"],
        ciphers=["AES128-GCM-SHA256", "AES256-GCM-SHA384"],
        max_workers=2,
    )

    assert called_versions == [ssl.TLSVersion.TLSv1_2, ssl.TLSVersion.TLSv1_3]
    assert called_ciphers == ["AES128-GCM-SHA256", "AES256-GCM-SHA384"]
    assert result["supported_versions"] == ["TLSv1_2", "TLSv1_3"]
    assert result["supported_ciphers"] == ["AES128-GCM-SHA256", "AES256-GCM-SHA384"]


def test_run_tls_invalid_version_raises() -> None:
    with pytest.raises(ValueError) as excinfo:
        run_tls("example.com", versions=["TLSv1_2", "BOGUS"], timeout=1.0)
    assert "Unknown TLS versions" in str(excinfo.value)
    assert "BOGUS" in str(excinfo.value)


def test_run_tls_empty_versions_and_ciphers(monkeypatch) -> None:
    def mock_probe_version(host, port, version, timeout=DEFAULT_TIMEOUT):
        raise AssertionError("should not be called")

    def mock_probe_cipher(host, port, cipher, timeout=DEFAULT_TIMEOUT):
        raise AssertionError("should not be called")

    monkeypatch.setattr("ethscan.tls.probe_version", mock_probe_version)
    monkeypatch.setattr("ethscan.tls.probe_cipher", mock_probe_cipher)

    result = run_tls("example.com", versions=[], ciphers=[], timeout=1.0)

    assert result["versions"] == []
    assert result["ciphers"] == []
    assert result["supported_versions"] == []
    assert result["supported_ciphers"] == []
    assert result["notes"] == []


def test_run_tls_notes_flag_obsolete_versions(monkeypatch) -> None:
    def mock_probe_version(host, port, version, timeout=DEFAULT_TIMEOUT):
        return {
            "version": version.name,
            "supported": True,
            "error": None,
            "negotiated_cipher": "AES128-SHA",
            "negotiated_protocol": "TLSv1",
        }

    def mock_probe_cipher(host, port, cipher, timeout=DEFAULT_TIMEOUT):
        return {
            "cipher": cipher,
            "supported": True,
            "error": None,
            "negotiated_version": "TLSv1",
        }

    monkeypatch.setattr("ethscan.tls.probe_version", mock_probe_version)
    monkeypatch.setattr("ethscan.tls.probe_cipher", mock_probe_cipher)

    result = run_tls("example.com", versions=["TLSv1"], ciphers=["AES128-SHA"], timeout=1.0)

    assert result["supported_versions"] == ["TLSv1"]
    assert any("Obsolete protocol version supported: TLSv1" in note for note in result["notes"])


def test_run_tls_offline_connection_refused() -> None:
    result = run_tls("127.0.0.1", port=9999, timeout=0.5, max_workers=4)

    assert result["target"] == "127.0.0.1"
    assert result["host"] == "127.0.0.1"
    assert result["port"] == 9999
    assert result["supported_versions"] == []
    assert result["supported_ciphers"] == []
    assert result["supported_version_count"] == 0
    assert result["supported_cipher_count"] == 0
    for entry in result["versions"]:
        assert entry["supported"] is False
        assert entry["error"] is not None
    for entry in result["ciphers"]:
        assert entry["supported"] is False
        assert entry["error"] is not None


def test_format_tls_report_json() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "port": 443,
        "timeout": 5.0,
        "versions_tested": 2,
        "ciphers_tested": 2,
        "versions": [
            {
                "version": "TLSv1_2",
                "supported": True,
                "error": None,
                "negotiated_cipher": "AES128-GCM-SHA256",
                "negotiated_protocol": "TLSv1.2",
            },
            {
                "version": "TLSv1",
                "supported": False,
                "error": "handshake failure",
                "negotiated_cipher": None,
                "negotiated_protocol": None,
            },
        ],
        "ciphers": [
            {
                "cipher": "AES128-GCM-SHA256",
                "supported": True,
                "error": None,
                "negotiated_version": "TLSv1.2",
            },
            {
                "cipher": "AES128-SHA",
                "supported": False,
                "error": "handshake failure",
                "negotiated_version": None,
            },
        ],
        "supported_versions": ["TLSv1_2"],
        "supported_ciphers": ["AES128-GCM-SHA256"],
        "supported_version_count": 1,
        "supported_cipher_count": 1,
        "notes": [],
    }
    output = format_tls_report_json(data)
    assert "example.com" in output
    assert "TLSv1_2" in output
    assert "AES128-GCM-SHA256" in output
    assert '"supported": true' in output
    assert '"port": 443' in output


def test_format_tls_report_markdown() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "port": 443,
        "timeout": 5.0,
        "versions_tested": 2,
        "ciphers_tested": 2,
        "versions": [
            {
                "version": "TLSv1_2",
                "supported": True,
                "error": None,
                "negotiated_cipher": "AES128-GCM-SHA256",
                "negotiated_protocol": "TLSv1.2",
            },
            {
                "version": "TLSv1",
                "supported": False,
                "error": "handshake failure",
                "negotiated_cipher": None,
                "negotiated_protocol": None,
            },
        ],
        "ciphers": [
            {
                "cipher": "AES128-GCM-SHA256",
                "supported": True,
                "error": None,
                "negotiated_version": "TLSv1.2",
            },
            {
                "cipher": "AES128-SHA",
                "supported": False,
                "error": "handshake failure",
                "negotiated_version": None,
            },
        ],
        "supported_versions": ["TLSv1_2"],
        "supported_ciphers": ["AES128-GCM-SHA256"],
        "supported_version_count": 1,
        "supported_cipher_count": 1,
        "notes": [],
    }
    output = format_tls_report_markdown(data)
    assert "# ethscan TLS Enumeration Report" in output
    assert "example.com" in output
    assert "**Port:** 443" in output
    assert "**Supported Versions:** TLSv1_2" in output
    assert "**Supported Ciphers:** 1" in output
    assert "## Protocol Versions" in output
    assert "| TLSv1_2 | Yes | AES128-GCM-SHA256 | TLSv1.2 |  |" in output
    assert "| TLSv1 | No |  |  | handshake failure |" in output
    assert "## Cipher Suites" in output
    assert "| AES128-GCM-SHA256 | Yes | TLSv1.2 |  |" in output
    assert "| AES128-SHA | No |  | handshake failure |" in output


def test_format_tls_report_markdown_no_data() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "port": 443,
        "versions_tested": 0,
        "ciphers_tested": 0,
        "versions": [],
        "ciphers": [],
        "supported_versions": [],
        "supported_ciphers": [],
        "supported_version_count": 0,
        "supported_cipher_count": 0,
        "notes": [],
    }
    output = format_tls_report_markdown(data)
    assert "*No protocol versions tested.*" in output
    assert "*No cipher suites tested.*" in output
    assert "**Supported Versions:** None" in output


def test_format_tls_report_markdown_notes() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "port": 443,
        "versions_tested": 1,
        "ciphers_tested": 1,
        "versions": [
            {
                "version": "TLSv1",
                "supported": True,
                "error": None,
                "negotiated_cipher": "AES128-SHA",
                "negotiated_protocol": "TLSv1",
            }
        ],
        "ciphers": [
            {
                "cipher": "AES128-SHA",
                "supported": True,
                "error": None,
                "negotiated_version": "TLSv1",
            }
        ],
        "supported_versions": ["TLSv1"],
        "supported_ciphers": ["AES128-SHA"],
        "supported_version_count": 1,
        "supported_cipher_count": 1,
        "notes": ["Obsolete protocol version supported: TLSv1"],
    }
    output = format_tls_report_markdown(data)
    assert "## Findings" in output
    assert "Obsolete protocol version supported: TLSv1" in output


def test_format_tls_report_markdown_error_truncation_and_escaping() -> None:
    long_error = "E" * 30 + " | injected" + "E" * 200
    data = {
        "target": "example.com",
        "host": "example.com",
        "port": 443,
        "versions_tested": 1,
        "ciphers_tested": 0,
        "versions": [
            {
                "version": "TLSv1_2",
                "supported": False,
                "error": long_error,
                "negotiated_cipher": None,
                "negotiated_protocol": None,
            }
        ],
        "ciphers": [],
        "supported_versions": [],
        "supported_ciphers": [],
        "supported_version_count": 0,
        "supported_cipher_count": 0,
        "notes": [],
    }
    output = format_tls_report_markdown(data)
    error_line = [line for line in output.split("\n") if "TLSv1_2" in line][0]
    assert len(error_line) < 250
    assert "\\|" in error_line
    assert "..." in error_line


def test_enumerate_tls_result_ordering(monkeypatch) -> None:
    def mock_probe_version(host, port, version, timeout=DEFAULT_TIMEOUT):
        return {
            "version": version.name,
            "supported": True,
            "error": None,
            "negotiated_cipher": "AES128-GCM-SHA256",
            "negotiated_protocol": "TLSv1.2",
        }

    def mock_probe_cipher(host, port, cipher, timeout=DEFAULT_TIMEOUT):
        return {
            "cipher": cipher,
            "supported": True,
            "error": None,
            "negotiated_version": "TLSv1.2",
        }

    monkeypatch.setattr("ethscan.tls.probe_version", mock_probe_version)
    monkeypatch.setattr("ethscan.tls.probe_cipher", mock_probe_cipher)

    result = enumerate_tls(
        "example.com",
        timeout=1.0,
        versions=["TLSv1_3", "TLSv1_2", "TLSv1_1"],
        ciphers=["AES256-GCM-SHA384", "AES128-GCM-SHA256"],
        max_workers=2,
    )

    assert [v["version"] for v in result["versions"]] == [
        "TLSv1_1",
        "TLSv1_2",
        "TLSv1_3",
    ]
    assert [c["cipher"] for c in result["ciphers"]] == [
        "AES128-GCM-SHA256",
        "AES256-GCM-SHA384",
    ]
