"""Tests for the ethscan tls module."""

import csv
import io
import socket
import ssl
from unittest.mock import patch, MagicMock

import pytest

from ethscan.tls import (
    ERROR_MAX_LENGTH,
    COMMON_CIPHERS,
    DEFAULT_PORT,
    DEFAULT_TIMEOUT,
    DEFAULT_WORKERS,
    OBSOLETE_VERSIONS,
    TLS_VERSIONS,
    _build_context,
    _cipher_sort_key,
    _normalize_host,
    _probe,
    _resolve_version,
    _resolve_versions,
    _truncate,
    _version_name,
    _version_sort_key,
    enumerate_tls,
    format_tls_report_csv,
    format_tls_report_json,
    format_tls_report_markdown,
    probe_cipher,
    probe_version,
    run_tls,
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


def test_format_tls_report_csv() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "port": 443,
        "versions": [
            {"version": "TLSv1_2", "supported": True, "error": None, "negotiated_cipher": "AES128-GCM-SHA256", "negotiated_protocol": "TLSv1.2"},
            {"version": "TLSv1", "supported": False, "error": "no cipher", "negotiated_cipher": None, "negotiated_protocol": None},
        ],
        "ciphers": [
            {"cipher": "AES128-GCM-SHA256", "supported": True, "error": None, "negotiated_version": "TLSv1.2"},
        ],
    }
    output = format_tls_report_csv(data)
    reader = list(csv.reader(io.StringIO(output)))
    assert reader[0] == ["target", "host", "port", "probe_type", "probe", "supported", "negotiated", "error"]
    assert reader[1] == ["example.com", "example.com", "443", "version", "TLSv1_2", "true", "AES128-GCM-SHA256", ""]
    assert reader[2] == ["example.com", "example.com", "443", "version", "TLSv1", "false", "", "no cipher"]
    assert reader[3] == ["example.com", "example.com", "443", "cipher", "AES128-GCM-SHA256", "true", "TLSv1.2", ""]


def test_format_tls_report_csv_empty() -> None:
    data = {"target": "example.com", "host": "example.com", "port": 443, "versions": [], "ciphers": []}
    output = format_tls_report_csv(data)
    reader = list(csv.reader(io.StringIO(output)))
    assert len(reader) == 1
    assert reader[0][0] == "target"


# ---------------------------------------------------------------------------
# _version_name
# ---------------------------------------------------------------------------


def test_version_name_from_member() -> None:
    assert _version_name(ssl.TLSVersion.TLSv1) == "TLSv1"
    assert _version_name(ssl.TLSVersion.TLSv1_2) == "TLSv1_2"
    assert _version_name(ssl.TLSVersion.TLSv1_3) == "TLSv1_3"


def test_version_name_from_string() -> None:
    assert _version_name("TLSv1") == "TLSv1"
    assert _version_name("tlsv1.2") == "tlsv1.2"
    assert _version_name("BOGUS") == "BOGUS"


# ---------------------------------------------------------------------------
# _resolve_versions
# ---------------------------------------------------------------------------


def test_resolve_versions_all_valid() -> None:
    specs = ["TLSv1", "tls1.2", "TLSv1_3"]
    assert _resolve_versions(specs) == [
        ssl.TLSVersion.TLSv1,
        ssl.TLSVersion.TLSv1_2,
        ssl.TLSVersion.TLSv1_3,
    ]


def test_resolve_versions_accepts_members() -> None:
    assert _resolve_versions([ssl.TLSVersion.TLSv1_2, ssl.TLSVersion.TLSv1_3]) == [
        ssl.TLSVersion.TLSv1_2,
        ssl.TLSVersion.TLSv1_3,
    ]


def test_resolve_versions_empty_returns_empty() -> None:
    assert _resolve_versions([]) == []


def test_resolve_versions_invalid_raises() -> None:
    with pytest.raises(ValueError) as excinfo:
        _resolve_versions(["TLSv1_2", "NOPE", "BOGUS"])
    msg = str(excinfo.value)
    assert "Unknown TLS versions" in msg
    assert "NOPE" in msg
    assert "BOGUS" in msg


# ---------------------------------------------------------------------------
# _build_context
# ---------------------------------------------------------------------------


def test_build_context_defaults() -> None:
    ctx = _build_context()
    assert ctx.check_hostname is False
    assert ctx.verify_mode == ssl.CERT_NONE


def test_build_context_with_version() -> None:
    ctx = _build_context(version=ssl.TLSVersion.TLSv1_2)
    assert ctx.minimum_version == ssl.TLSVersion.TLSv1_2
    assert ctx.maximum_version == ssl.TLSVersion.TLSv1_2


def test_build_context_with_cipher(monkeypatch) -> None:
    calls = []

    def recorder(self, ciphers):
        calls.append(ciphers)

    monkeypatch.setattr(ssl.SSLContext, "set_ciphers", recorder)
    ctx = _build_context(cipher="AES128-SHA")
    assert calls == ["AES128-SHA"]
    assert ctx.check_hostname is False


# ---------------------------------------------------------------------------
# _probe
# ---------------------------------------------------------------------------


@patch("ethscan.tls.socket.create_connection")
def test_probe_returns_cipher(mock_create_connection) -> None:
    mock_sock = MagicMock()
    mock_create_connection.return_value.__enter__.return_value = mock_sock
    mock_ctx = MagicMock()
    mock_ssock = MagicMock()
    mock_ctx.wrap_socket.return_value.__enter__.return_value = mock_ssock
    mock_ssock.cipher.return_value = ("AES128-GCM-SHA256", "TLSv1.2")

    cipher_name, protocol = _probe("example.com", 443, mock_ctx, timeout=5.0)
    assert cipher_name == "AES128-GCM-SHA256"
    assert protocol == "TLSv1.2"
    mock_sock.settimeout.assert_called_once_with(5.0)
    mock_ctx.wrap_socket.assert_called_once_with(mock_sock, server_hostname="example.com")


@patch("ethscan.tls.socket.create_connection")
def test_probe_no_cipher_returns_none(mock_create_connection) -> None:
    mock_sock = MagicMock()
    mock_create_connection.return_value.__enter__.return_value = mock_sock
    mock_ctx = MagicMock()
    mock_ssock = MagicMock()
    mock_ctx.wrap_socket.return_value.__enter__.return_value = mock_ssock
    mock_ssock.cipher.return_value = None

    cipher_name, protocol = _probe("example.com", 443, mock_ctx, timeout=2.0)
    assert cipher_name is None
    assert protocol is None


@patch("ethscan.tls.socket.create_connection")
def test_probe_propagates_oserror(mock_create_connection) -> None:
    mock_create_connection.side_effect = OSError("connection refused")
    mock_ctx = MagicMock()
    with pytest.raises(OSError):
        _probe("example.com", 443, mock_ctx, timeout=1.0)


# ---------------------------------------------------------------------------
# probe_version dispatch
# ---------------------------------------------------------------------------


def test_probe_version_success(monkeypatch) -> None:
    monkeypatch.setattr(
        "ethscan.tls._probe",
        lambda *a, **kw: ("AES128-GCM-SHA256", "TLSv1.2"),
    )
    result = probe_version("example.com", 443, ssl.TLSVersion.TLSv1_2, timeout=1.0)
    assert result["version"] == "TLSv1_2"
    assert result["supported"] is True
    assert result["negotiated_cipher"] == "AES128-GCM-SHA256"
    assert result["negotiated_protocol"] == "TLSv1.2"
    assert result["error"] is None


def test_probe_version_ssl_error(monkeypatch) -> None:
    def raise_ssl(*args, **kwargs):
        raise ssl.SSLError("SSLV3_ALERT_HANDSHAKE_FAILURE")

    monkeypatch.setattr("ethscan.tls._probe", raise_ssl)
    result = probe_version("example.com", 443, ssl.TLSVersion.TLSv1_2, timeout=1.0)
    assert result["version"] == "TLSv1_2"
    assert result["supported"] is False
    assert result["error"] is not None
    assert "SSLV3_ALERT_HANDSHAKE_FAILURE" in result["error"]


def test_probe_version_oserror(monkeypatch) -> None:
    def raise_os(*args, **kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr("ethscan.tls._probe", raise_os)
    result = probe_version("example.com", 443, ssl.TLSVersion.TLSv1_2, timeout=1.0)
    assert result["supported"] is False
    assert result["error"] == "connection refused"


# ---------------------------------------------------------------------------
# probe_cipher dispatch
# ---------------------------------------------------------------------------


def test_probe_cipher_success(monkeypatch) -> None:
    monkeypatch.setattr(
        "ethscan.tls._probe",
        lambda *a, **kw: ("AES128-GCM-SHA256", "TLSv1.2"),
    )
    result = probe_cipher("example.com", 443, "AES128-GCM-SHA256", timeout=1.0)
    assert result["cipher"] == "AES128-GCM-SHA256"
    assert result["supported"] is True
    assert result["negotiated_version"] == "TLSv1.2"
    assert result["error"] is None


def test_probe_cipher_ssl_error(monkeypatch) -> None:
    def raise_ssl(*args, **kwargs):
        raise ssl.SSLError("bad decrypt")

    monkeypatch.setattr("ethscan.tls._probe", raise_ssl)
    result = probe_cipher("example.com", 443, "AES128-SHA", timeout=1.0)
    assert result["cipher"] == "AES128-SHA"
    assert result["supported"] is False
    assert result["error"] is not None
    assert "bad decrypt" in result["error"]


# ---------------------------------------------------------------------------
# _truncate
# ---------------------------------------------------------------------------


def test_truncate_short_message() -> None:
    assert _truncate("short") == "short"


def test_truncate_exact_limit() -> None:
    message = "a" * ERROR_MAX_LENGTH
    assert _truncate(message) == message


def test_truncate_long_message_default_limit() -> None:
    message = "x" * (ERROR_MAX_LENGTH + 50)
    truncated = _truncate(message)
    assert len(truncated) == ERROR_MAX_LENGTH
    assert truncated.endswith("...")
    assert truncated == "x" * (ERROR_MAX_LENGTH - 3) + "..."


def test_truncate_long_message_custom_limit() -> None:
    message = "y" * 100
    truncated = _truncate(message, limit=30)
    assert len(truncated) == 30
    assert truncated.endswith("...")


# ---------------------------------------------------------------------------
# _version_sort_key / _cipher_sort_key
# ---------------------------------------------------------------------------


def test_version_sort_key_known() -> None:
    assert _version_sort_key("TLSv1") == TLS_VERSIONS.index(ssl.TLSVersion.TLSv1)
    assert _version_sort_key("TLSv1_2") == TLS_VERSIONS.index(ssl.TLSVersion.TLSv1_2)
    assert _version_sort_key("TLSv1_3") == TLS_VERSIONS.index(ssl.TLSVersion.TLSv1_3)


def test_version_sort_key_unknown() -> None:
    sentinel = len(TLS_VERSIONS)
    assert _version_sort_key("SSLv3") == sentinel
    assert _version_sort_key("BOGUS") == sentinel


def test_cipher_sort_key_known() -> None:
    assert _cipher_sort_key("AES128-SHA") == 0
    assert _cipher_sort_key("AES256-GCM-SHA384") == COMMON_CIPHERS.index("AES256-GCM-SHA384")


def test_cipher_sort_key_unknown() -> None:
    sentinel = len(COMMON_CIPHERS)
    assert _cipher_sort_key("SOME-CIPHER") == sentinel
    assert _cipher_sort_key("") == sentinel


# ---------------------------------------------------------------------------
# enumerate_tls notes
# ---------------------------------------------------------------------------


def test_enumerate_tls_note_versions_without_ciphers(monkeypatch) -> None:
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
            "supported": False,
            "error": "no cipher",
            "negotiated_version": None,
        }

    monkeypatch.setattr("ethscan.tls.probe_version", mock_probe_version)
    monkeypatch.setattr("ethscan.tls.probe_cipher", mock_probe_cipher)

    result = enumerate_tls(
        "example.com",
        versions=["TLSv1_2"],
        ciphers=["AES128-SHA"],
        timeout=1.0,
        max_workers=2,
    )
    assert result["supported_versions"] == ["TLSv1_2"]
    assert result["supported_ciphers"] == []
    assert any("no tested cipher succeeded" in note for note in result["notes"])


def test_build_context_default_version_unchanged(monkeypatch) -> None:
    ctx = _build_context()
    assert ctx.minimum_version == ssl.TLSVersion.MINIMUM_SUPPORTED
    assert ctx.maximum_version == ssl.TLSVersion.MAXIMUM_SUPPORTED
