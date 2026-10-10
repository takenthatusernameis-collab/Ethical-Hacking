"""Tests for the ethscan osdetect module."""

import json
import threading
from typing import List

import pytest

from ethscan.osdetect import (
    DEFAULT_TIMEOUT,
    OS_SIGNATURES,
    _checksum,
    _connect_tcp,
    _match_os_from_banner,
    _match_os_from_behavior,
    _match_os_from_ttl,
    _normalize_host,
    _truncate,
    format_osdetect_report_json,
    format_osdetect_report_markdown,
    probe_ack,
    probe_fin,
    probe_rst,
    probe_syn,
    run_osdetect,
)


# ---------------------------------------------------------------------------
# Domain normalization
# ---------------------------------------------------------------------------


def test_normalize_host_bare() -> None:
    assert _normalize_host("example.com") == "example.com"


def test_normalize_host_uppercase() -> None:
    assert _normalize_host("Example.COM") == "example.com"


def test_normalize_host_https_url() -> None:
    assert _normalize_host("https://example.com/path") == "example.com"


def test_normalize_host_strips_whitespace() -> None:
    assert _normalize_host("  example.com  ") == "example.com"


def test_normalize_host_with_port() -> None:
    assert _normalize_host("http://example.com:8080") == "example.com"


# ---------------------------------------------------------------------------
# Truncate helper
# ---------------------------------------------------------------------------


def test_truncate_short() -> None:
    assert _truncate("short") == "short"


def test_truncate_long() -> None:
    msg = "x" * 300
    result = _truncate(msg, 50)
    assert len(result) == 50
    assert result.endswith("...")


def test_truncate_exact() -> None:
    msg = "x" * 50
    assert _truncate(msg, 50) == msg


# ---------------------------------------------------------------------------
# Checksum helper
# ---------------------------------------------------------------------------


def test_checksum_empty() -> None:
    assert _checksum(b"") == 0xFFFF


def test_checksum_known() -> None:
    # "hello" -> known checksum value
    result = _checksum(b"hello")
    assert isinstance(result, int)
    assert 0 <= result <= 0xFFFF


# ---------------------------------------------------------------------------
# OS signature matching
# ---------------------------------------------------------------------------


def test_match_os_from_banner_linux() -> None:
    matches = _match_os_from_banner("SSH-2.0-OpenSSH_7.9 Linux")
    assert "Linux" in matches


def test_match_os_from_banner_windows() -> None:
    matches = _match_os_from_banner("Microsoft Windows Server")
    assert "Windows" in matches


def test_match_os_from_banner_unknown() -> None:
    matches = _match_os_from_banner("Some unknown banner")
    assert matches == []


def test_match_os_from_ttl_linux() -> None:
    matches = _match_os_from_ttl(64)
    assert "Linux" in matches


def test_match_os_from_ttl_windows() -> None:
    matches = _match_os_from_ttl(128)
    assert "Windows" in matches


def test_match_os_from_ttl_unknown() -> None:
    matches = _match_os_from_ttl(50)
    assert matches == []


def test_match_os_from_behavior_rst() -> None:
    behavior = {"response": "RST", "flags_observed": "RST", "probe_type": "FIN"}
    matches = _match_os_from_behavior(behavior)
    assert "Windows" in matches


def test_match_os_from_behavior_no_response() -> None:
    behavior = {"response": "NO-RESPONSE", "flags_observed": None, "probe_type": "FIN"}
    matches = _match_os_from_behavior(behavior)
    assert "Linux" in matches


def test_match_os_from_behavior_no_match() -> None:
    behavior = {"response": "SYN-ACK", "flags_observed": "SYN-ACK", "probe_type": "SYN"}
    matches = _match_os_from_behavior(behavior)
    assert matches == []


# ---------------------------------------------------------------------------
# Probe functions (offline / refused)
# ---------------------------------------------------------------------------


def test_probe_syn_offline() -> None:
    result = probe_syn("nonexistent.invalid.domain.tld", 80, timeout=1.0)
    assert result["port"] == 80
    assert result["connected"] is False
    assert result["response"] in ("NO-RESPONSE", "RST")


def test_probe_syn_loopback_closed() -> None:
    result = probe_syn("127.0.0.1", 1, timeout=1.0)
    assert result["port"] == 1
    assert result["connected"] is False


def test_probe_rst_offline() -> None:
    result = probe_rst("nonexistent.invalid.domain.tld", 80, timeout=1.0)
    assert result["port"] == 80
    assert result["connected"] is False


def test_probe_fin_offline() -> None:
    result = probe_fin("nonexistent.invalid.domain.tld", 80, timeout=1.0)
    assert result["port"] == 80
    assert result["connected"] is False


def test_probe_ack_offline() -> None:
    result = probe_ack("nonexistent.invalid.domain.tld", 80, timeout=1.0)
    assert result["port"] == 80
    assert result["connected"] is False


def test_probe_syn_loopback_open() -> None:
    # Start a local TCP server on a free port and probe it
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    port = sock.getsockname()[1]

    def _serve():
        try:
            conn, _ = sock.accept()
            conn.close()
        except OSError:
            pass

    thread = threading.Thread(target=_serve, daemon=True)
    thread.start()
    try:
        result = probe_syn("127.0.0.1", port, timeout=2.0)
        assert result["connected"] is True
        assert result["response"] == "SYN-ACK"
    finally:
        try:
            sock.close()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# run_osdetect
# ---------------------------------------------------------------------------


def test_run_osdetect_offline_target() -> None:
    result = run_osdetect(
        "nonexistent.invalid.domain.tld",
        ports=[80, 443],
        timeout=1.0,
        max_workers=2,
    )
    assert result["target"] == "nonexistent.invalid.domain.tld"
    assert result["host"] == "nonexistent.invalid.domain.tld"
    assert result["ports_probed"] == 2
    assert len(result["probes"]) == 2
    assert result["inferred_os_count"] >= 0
    assert isinstance(result["notes"], list)


def test_run_osdetect_default_ports() -> None:
    result = run_osdetect(
        "nonexistent.invalid.domain.tld",
        timeout=1.0,
        max_workers=2,
    )
    assert result["ports_probed"] == 3
    assert {p["port"] for p in result["probes"]} == {22, 80, 443}


def test_run_osdetect_url_target() -> None:
    result = run_osdetect(
        "https://example.com",
        ports=[80],
        timeout=1.0,
        max_workers=1,
    )
    assert result["host"] == "example.com"
    assert result["ports_probed"] == 1


def test_run_osdetect_with_banners() -> None:
    banners = {22: "SSH-2.0-OpenSSH_7.9 Linux"}
    result = run_osdetect(
        "nonexistent.invalid.domain.tld",
        ports=[22],
        timeout=1.0,
        max_workers=1,
        banners=banners,
    )
    assert result["banners_provided"] is True
    assert "Linux" in result["inferred_os"]


def test_run_osdetect_banners_file(tmp_path) -> None:
    services_file = tmp_path / "service_report.json"
    services_file.write_text(
        json.dumps(
            {
                "results": [
                    {"port": 22, "banner": "SSH-2.0-OpenSSH_8.9 Linux"},
                    {"port": 80, "banner": "Microsoft-IIS/10.0 Windows"},
                ]
            }
        )
    )
    with open(services_file, "r", encoding="utf-8") as handle:
        services = json.load(handle)
    banners = {}
    for entry in services.get("results") or []:
        port = entry.get("port")
        banner = entry.get("banner")
        if port is not None and banner:
            banners[port] = banner

    result = run_osdetect(
        "nonexistent.invalid.domain.tld",
        ports=[22, 80],
        timeout=1.0,
        max_workers=2,
        banners=banners,
    )
    assert "Linux" in result["inferred_os"]
    assert "Windows" in result["inferred_os"]


def test_run_osdetect_no_open_ports() -> None:
    result = run_osdetect(
        "nonexistent.invalid.domain.tld",
        ports=[80, 443],
        timeout=1.0,
        max_workers=2,
    )
    assert any("No open ports" in note for note in result["notes"])


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


def test_format_osdetect_report_json() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 1.0,
        "ports_probed": 1,
        "probes": [
            {"port": 80, "connected": True, "response": "SYN-ACK",
             "flags_observed": "SYN-ACK", "error": None}
        ],
        "inferred_os": ["Linux"],
        "inferred_os_count": 1,
        "banners_provided": False,
        "notes": [],
    }
    output = format_osdetect_report_json(data)
    parsed = json.loads(output)
    assert parsed["target"] == "example.com"
    assert parsed["inferred_os"] == ["Linux"]


def test_format_osdetect_report_markdown() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 1.0,
        "ports_probed": 1,
        "probes": [
            {"port": 80, "connected": True, "response": "SYN-ACK",
             "flags_observed": "SYN-ACK", "error": None}
        ],
        "inferred_os": ["Linux"],
        "inferred_os_count": 1,
        "banners_provided": False,
        "notes": ["test note"],
    }
    output = format_osdetect_report_markdown(data)
    assert "OS Detection Report" in output
    assert "example.com" in output
    assert "Linux" in output
    assert "test note" in output


def test_format_osdetect_report_markdown_no_probes() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 1.0,
        "ports_probed": 0,
        "probes": [],
        "inferred_os": [],
        "inferred_os_count": 0,
        "banners_provided": False,
        "notes": [],
    }
    output = format_osdetect_report_markdown(data)
    assert "No probes performed" in output
    assert "Unknown" in output


def test_format_osdetect_report_markdown_pipe_escape() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 1.0,
        "ports_probed": 1,
        "probes": [
            {"port": 80, "connected": False, "response": "RST",
             "flags_observed": "RST", "error": "connection | refused"}
        ],
        "inferred_os": ["Windows"],
        "inferred_os_count": 1,
        "banners_provided": False,
        "notes": [],
    }
    output = format_osdetect_report_markdown(data)
    assert "\\|" in output
