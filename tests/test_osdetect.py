"""Tests for the ethscan osdetect module."""

import contextlib
import csv
import io
import json
import threading

from typing import cast

from ethscan.osdetect import (
    _checksum,
    _match_os_from_banner,
    _match_os_from_behavior,
    _match_os_from_ttl,
    _normalize_host,
    _truncate,
    format_osdetect_report_csv,
    format_osdetect_report_json,
    format_osdetect_report_markdown,
    probe_ack,
    probe_fin,
    probe_rst,
    probe_syn,
    run_osdetect,
)
from ethscan.target import TargetSpecError

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


def test_normalize_host_rejects_empty_target() -> None:
    for bad in ("", "   ", "https://"):
        try:
            _normalize_host(bad)
        except TargetSpecError as exc:
            assert "Could not parse host from target" in str(exc)
        else:
            raise AssertionError(f"Expected TargetSpecError for {bad!r}")


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
    assert _checksum(b"hello") == 0xBC2D


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
        with contextlib.suppress(OSError):
            sock.close()


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
    with open(services_file, encoding="utf-8") as handle:
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


def test_format_osdetect_report_csv() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "probes": [
            {"port": 80, "probe_type": "SYN", "connected": True, "response": "SYN-ACK", "flags_observed": "SYN-ACK", "error": None},
            {"port": 22, "probe_type": "SYN", "connected": False, "response": "RST", "flags_observed": "RST", "error": "refused"},
        ],
        "inferred_os": ["Linux"],
    }
    output = format_osdetect_report_csv(data)
    reader = list(csv.reader(io.StringIO(output)))
    assert reader[0] == ["target", "host", "port", "probe_type", "connected", "response", "flags_observed", "error"]
    assert reader[1] == ["example.com", "example.com", "80", "SYN", "true", "SYN-ACK", "SYN-ACK", ""]
    assert reader[2] == ["example.com", "example.com", "22", "SYN", "false", "RST", "RST", "refused"]
    assert reader[3] == ["example.com", "example.com", "", "inferred_os", "", "", "Linux", ""]


def test_format_osdetect_report_csv_empty() -> None:
    data = {"target": "example.com", "host": "example.com", "probes": [], "inferred_os": []}
    output = format_osdetect_report_csv(data)
    reader = list(csv.reader(io.StringIO(output)))
    assert len(reader) == 1
    assert reader[0][0] == "target"


def test_errno_message_value_error() -> None:
    from unittest.mock import patch
    with patch("os.strerror", side_effect=ValueError):
        from ethscan import osdetect
        assert osdetect._errno_message(12345) == "12345"


def test_errno_message_overflow_error() -> None:
    from unittest.mock import patch
    with patch("os.strerror", side_effect=OverflowError):
        from ethscan import osdetect
        assert osdetect._errno_message(-1) == "-1"


def test_build_syn_packet_basic() -> None:
    from ethscan import osdetect
    pkt = osdetect._build_syn_packet(1234, 80)
    assert len(pkt) == 20


def test_build_syn_packet_custom() -> None:
    from ethscan import osdetect
    pkt = osdetect._build_syn_packet(1234, 80, seq=1, ack=2, flags=osdetect.SYN | osdetect.ACK, window=4096, urgent=1)
    assert len(pkt) == 20


def test_checksum_odd_length() -> None:
    from ethscan import osdetect
    assert osdetect._checksum(b"abc") == 0x3B9D


def test_checksum_even_length() -> None:
    from ethscan import osdetect
    assert osdetect._checksum(b"abcd") == 0x3B39


def test_connect_tcp_success() -> None:
    from unittest.mock import MagicMock, patch

    from ethscan import osdetect
    mock_sock = MagicMock()
    with patch("socket.create_connection", return_value=mock_sock):
        ok, err, flag = osdetect._connect_tcp("example.com", 80, 5.0)
        assert ok is True
        assert err is None
        assert flag is None
        mock_sock.close.assert_called_once()


def test_connect_tcp_refused() -> None:
    from unittest.mock import patch

    from ethscan import osdetect
    with patch("socket.create_connection", side_effect=ConnectionRefusedError):
        ok, err, flag = osdetect._connect_tcp("example.com", 80, 5.0)
        assert ok is False
        assert err is not None
        assert "RST" in err
        assert flag == 1


def test_connect_tcp_timeout() -> None:
    from unittest.mock import patch

    from ethscan import osdetect
    with patch("socket.create_connection", side_effect=Exception):
        pass  # different behavior? socket.timeout is subclass of OSError; test actual
    import socket as sockmod
    with patch("socket.create_connection", side_effect=sockmod.timeout):
        ok, err, flag = osdetect._connect_tcp("example.com", 80, 5.0)
        assert ok is False
        assert err == "connection timed out"
        assert flag is None


def test_connect_tcp_oserror() -> None:
    from unittest.mock import patch

    from ethscan import osdetect
    with patch("socket.create_connection", side_effect=OSError("boom")):
        ok, err, flag = osdetect._connect_tcp("example.com", 80, 5.0)
        assert ok is False
        assert err == "boom"
        assert flag is None


def test_connect_tcp_oserror_truncate() -> None:
    from unittest.mock import patch

    from ethscan import osdetect
    with patch("socket.create_connection", side_effect=OSError("x" * 300)):
        ok, err, _ = osdetect._connect_tcp("example.com", 80, 5.0)
        assert ok is False
        assert err is not None
        assert err.endswith("...")


def test_connect_tcp_close_error() -> None:
    from unittest.mock import MagicMock, patch

    from ethscan import osdetect
    mock_sock = MagicMock()
    mock_sock.close.side_effect = Exception("bad")
    with patch("socket.create_connection", return_value=mock_sock):
        ok, _, _ = osdetect._connect_tcp("example.com", 80, 5.0)
        assert ok is True


def test_probe_syn_connected() -> None:
    from unittest.mock import patch

    from ethscan import osdetect
    with patch("ethscan.osdetect._connect_tcp", return_value=(True, None, None)):
        res = osdetect.probe_syn("h", 80, 1.0)
        assert res["connected"] is True
        assert res["response"] == "SYN-ACK"


def test_probe_syn_refused() -> None:
    from unittest.mock import patch

    from ethscan import osdetect
    with patch("ethscan.osdetect._connect_tcp", return_value=(False, "err", 1)):
        res = osdetect.probe_syn("h", 80, 1.0)
        assert res["response"] == "RST"


def test_probe_syn_noresp() -> None:
    from unittest.mock import patch

    from ethscan import osdetect
    with patch("ethscan.osdetect._connect_tcp", return_value=(False, "t", None)):
        res = osdetect.probe_syn("h", 80, 1.0)
        assert res["response"] == "NO-RESPONSE"


def test_probe_rst_open(monkeypatch) -> None:
    import socket

    from ethscan import osdetect

    class FakeSock:
        def __init__(self, family, socktype, proto):
            pass

        def settimeout(self, timeout):
            pass

        def connect_ex(self, sockaddr):
            return 0

        def close(self):
            pass

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 80))
        ],
    )
    monkeypatch.setattr("ethscan.osdetect.socket.socket", FakeSock)

    res = osdetect.probe_rst("h", 80, 1.0)
    assert res["connected"] is True


def test_probe_rst_refused_111(monkeypatch) -> None:
    import socket

    from ethscan import osdetect

    class FakeSock:
        def __init__(self, family, socktype, proto):
            pass

        def settimeout(self, timeout):
            pass

        def connect_ex(self, sockaddr):
            return 111

        def close(self):
            pass

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 80))
        ],
    )
    monkeypatch.setattr("ethscan.osdetect.socket.socket", FakeSock)

    assert osdetect.probe_rst("h", 80, 1.0)["response"] == "RST"


def test_probe_rst_refused_10061(monkeypatch) -> None:
    import socket

    from ethscan import osdetect

    class FakeSock:
        def __init__(self, family, socktype, proto):
            pass

        def settimeout(self, timeout):
            pass

        def connect_ex(self, sockaddr):
            return 10061

        def close(self):
            pass

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 80))
        ],
    )
    monkeypatch.setattr("ethscan.osdetect.socket.socket", FakeSock)

    assert osdetect.probe_rst("h", 80, 1.0)["response"] == "RST"


def test_probe_rst_refused_10013(monkeypatch) -> None:
    import socket

    from ethscan import osdetect

    class FakeSock:
        def __init__(self, family, socktype, proto):
            pass

        def settimeout(self, timeout):
            pass

        def connect_ex(self, sockaddr):
            return 10013

        def close(self):
            pass

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 80))
        ],
    )
    monkeypatch.setattr("ethscan.osdetect.socket.socket", FakeSock)

    assert osdetect.probe_rst("h", 80, 1.0)["response"] == "RST"


def test_probe_rst_other(monkeypatch) -> None:
    import socket

    from ethscan import osdetect

    class FakeSock:
        def __init__(self, family, socktype, proto):
            pass

        def settimeout(self, timeout):
            pass

        def connect_ex(self, sockaddr):
            return 1

        def close(self):
            pass

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 80))
        ],
    )
    monkeypatch.setattr("ethscan.osdetect.socket.socket", FakeSock)
    monkeypatch.setattr("os.strerror", lambda *a: "other")

    assert osdetect.probe_rst("h", 80, 1.0)["response"] == "NO-RESPONSE"


def test_probe_rst_timeout(monkeypatch) -> None:
    import socket

    from ethscan import osdetect

    class FakeSock:
        def __init__(self, family, socktype, proto):
            pass

        def settimeout(self, timeout):
            pass

        def connect_ex(self, sockaddr):
            raise socket.timeout()

        def close(self):
            pass

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 80))
        ],
    )
    monkeypatch.setattr("ethscan.osdetect.socket.socket", FakeSock)

    res = osdetect.probe_rst("h", 80, 1.0)
    assert res["error"] == "connection timed out"


def test_probe_rst_oserror(monkeypatch) -> None:
    import socket

    from ethscan import osdetect

    class FakeSock:
        def __init__(self, family, socktype, proto):
            pass

        def settimeout(self, timeout):
            pass

        def connect_ex(self, sockaddr):
            raise OSError("bad")

        def close(self):
            pass

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 80))
        ],
    )
    monkeypatch.setattr("ethscan.osdetect.socket.socket", FakeSock)

    assert osdetect.probe_rst("h", 80, 1.0)["error"] == "bad"


def test_probe_rst_oserror_truncate(monkeypatch) -> None:
    import socket

    from ethscan import osdetect

    class FakeSock:
        def __init__(self, family, socktype, proto):
            pass

        def settimeout(self, timeout):
            pass

        def connect_ex(self, sockaddr):
            raise OSError("y" * 300)

        def close(self):
            pass

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 80))
        ],
    )
    monkeypatch.setattr("ethscan.osdetect.socket.socket", FakeSock)

    assert cast(str, osdetect.probe_rst("h", 80, 1.0)["error"]).endswith("...")


def test_probe_rst_close_err(monkeypatch) -> None:
    import socket

    from ethscan import osdetect

    class FakeSock:
        def __init__(self, family, socktype, proto):
            pass

        def settimeout(self, timeout):
            pass

        def connect_ex(self, sockaddr):
            return 1

        def close(self):
            raise Exception("bad")

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 80))
        ],
    )
    monkeypatch.setattr("ethscan.osdetect.socket.socket", FakeSock)
    monkeypatch.setattr("os.strerror", lambda *a: "other")

    assert osdetect.probe_rst("h", 80, 1.0)["response"] == "NO-RESPONSE"


def test_probe_fin_open(monkeypatch) -> None:
    import socket

    from ethscan import osdetect

    class FakeSock:
        def __init__(self, family, socktype, proto):
            pass

        def settimeout(self, timeout):
            pass

        def connect_ex(self, sockaddr):
            return 0

        def close(self):
            pass

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 80))
        ],
    )
    monkeypatch.setattr("ethscan.osdetect.socket.socket", FakeSock)

    assert osdetect.probe_fin("h", 80, 1.0)["connected"] is True


def test_probe_fin_refused(monkeypatch) -> None:
    import socket

    from ethscan import osdetect

    class FakeSock:
        def __init__(self, family, socktype, proto):
            pass

        def settimeout(self, timeout):
            pass

        def connect_ex(self, sockaddr):
            return 111

        def close(self):
            pass

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 80))
        ],
    )
    monkeypatch.setattr("ethscan.osdetect.socket.socket", FakeSock)

    assert osdetect.probe_fin("h", 80, 1.0)["response"] == "RST"


def test_probe_fin_other(monkeypatch) -> None:
    import socket

    from ethscan import osdetect

    class FakeSock:
        def __init__(self, family, socktype, proto):
            pass

        def settimeout(self, timeout):
            pass

        def connect_ex(self, sockaddr):
            return 2

        def close(self):
            pass

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 80))
        ],
    )
    monkeypatch.setattr("ethscan.osdetect.socket.socket", FakeSock)
    monkeypatch.setattr("os.strerror", lambda *a: "e")

    assert osdetect.probe_fin("h", 80, 1.0)["response"] == "NO-RESPONSE"


def test_probe_fin_timeout(monkeypatch) -> None:
    import socket

    from ethscan import osdetect

    class FakeSock:
        def __init__(self, family, socktype, proto):
            pass

        def settimeout(self, timeout):
            pass

        def connect_ex(self, sockaddr):
            raise socket.timeout()

        def close(self):
            pass

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 80))
        ],
    )
    monkeypatch.setattr("ethscan.osdetect.socket.socket", FakeSock)

    assert osdetect.probe_fin("h", 80, 1.0)["error"] == "connection timed out"


def test_probe_fin_oserror(monkeypatch) -> None:
    import socket

    from ethscan import osdetect

    class FakeSock:
        def __init__(self, family, socktype, proto):
            pass

        def settimeout(self, timeout):
            pass

        def connect_ex(self, sockaddr):
            raise OSError("bad")

        def close(self):
            pass

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 80))
        ],
    )
    monkeypatch.setattr("ethscan.osdetect.socket.socket", FakeSock)

    assert osdetect.probe_fin("h", 80, 1.0)["error"] == "bad"


def test_probe_fin_oserror_truncate(monkeypatch) -> None:
    import socket

    from ethscan import osdetect

    class FakeSock:
        def __init__(self, family, socktype, proto):
            pass

        def settimeout(self, timeout):
            pass

        def connect_ex(self, sockaddr):
            raise OSError("z" * 300)

        def close(self):
            pass

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 80))
        ],
    )
    monkeypatch.setattr("ethscan.osdetect.socket.socket", FakeSock)

    assert cast(str, osdetect.probe_fin("h", 80, 1.0)["error"]).endswith("...")


def test_probe_fin_close_err(monkeypatch) -> None:
    import socket

    from ethscan import osdetect

    class FakeSock:
        def __init__(self, family, socktype, proto):
            pass

        def settimeout(self, timeout):
            pass

        def connect_ex(self, sockaddr):
            return 0

        def close(self):
            raise Exception("bad")

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 80))
        ],
    )
    monkeypatch.setattr("ethscan.osdetect.socket.socket", FakeSock)

    assert osdetect.probe_fin("h", 80, 1.0)["connected"] is True


def test_probe_ack_open(monkeypatch) -> None:
    import socket

    from ethscan import osdetect

    class FakeSock:
        def __init__(self, family, socktype, proto):
            pass

        def settimeout(self, timeout):
            pass

        def connect_ex(self, sockaddr):
            return 0

        def close(self):
            pass

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 80))
        ],
    )
    monkeypatch.setattr("ethscan.osdetect.socket.socket", FakeSock)

    assert osdetect.probe_ack("h", 80, 1.0)["connected"] is True


def test_probe_ack_refused(monkeypatch) -> None:
    import socket

    from ethscan import osdetect

    class FakeSock:
        def __init__(self, family, socktype, proto):
            pass

        def settimeout(self, timeout):
            pass

        def connect_ex(self, sockaddr):
            return 111

        def close(self):
            pass

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 80))
        ],
    )
    monkeypatch.setattr("ethscan.osdetect.socket.socket", FakeSock)

    assert osdetect.probe_ack("h", 80, 1.0)["response"] == "RST"


def test_probe_ack_other(monkeypatch) -> None:
    import socket

    from ethscan import osdetect

    class FakeSock:
        def __init__(self, family, socktype, proto):
            pass

        def settimeout(self, timeout):
            pass

        def connect_ex(self, sockaddr):
            return 3

        def close(self):
            pass

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 80))
        ],
    )
    monkeypatch.setattr("ethscan.osdetect.socket.socket", FakeSock)
    monkeypatch.setattr("os.strerror", lambda *a: "e")

    assert osdetect.probe_ack("h", 80, 1.0)["error"] == "e"


def test_probe_ack_timeout(monkeypatch) -> None:
    import socket

    from ethscan import osdetect

    class FakeSock:
        def __init__(self, family, socktype, proto):
            pass

        def settimeout(self, timeout):
            pass

        def connect_ex(self, sockaddr):
            raise socket.timeout()

        def close(self):
            pass

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 80))
        ],
    )
    monkeypatch.setattr("ethscan.osdetect.socket.socket", FakeSock)

    assert osdetect.probe_ack("h", 80, 1.0)["response"] == "NO-RESPONSE"


def test_probe_ack_oserror(monkeypatch) -> None:
    import socket

    from ethscan import osdetect

    class FakeSock:
        def __init__(self, family, socktype, proto):
            pass

        def settimeout(self, timeout):
            pass

        def connect_ex(self, sockaddr):
            raise OSError("x")

        def close(self):
            pass

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 80))
        ],
    )
    monkeypatch.setattr("ethscan.osdetect.socket.socket", FakeSock)

    assert osdetect.probe_ack("h", 80, 1.0)["error"] == "x"


def test_probe_ack_oserror_truncate(monkeypatch) -> None:
    import socket

    from ethscan import osdetect

    class FakeSock:
        def __init__(self, family, socktype, proto):
            pass

        def settimeout(self, timeout):
            pass

        def connect_ex(self, sockaddr):
            raise OSError("w" * 300)

        def close(self):
            pass

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 80))
        ],
    )
    monkeypatch.setattr("ethscan.osdetect.socket.socket", FakeSock)

    assert cast(str, osdetect.probe_ack("h", 80, 1.0)["error"]).endswith("...")


def test_probe_ack_close_err(monkeypatch) -> None:
    import socket

    from ethscan import osdetect

    class FakeSock:
        def __init__(self, family, socktype, proto):
            pass

        def settimeout(self, timeout):
            pass

        def connect_ex(self, sockaddr):
            return 0

        def close(self):
            raise Exception("bad")

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 80))
        ],
    )
    monkeypatch.setattr("ethscan.osdetect.socket.socket", FakeSock)

    assert osdetect.probe_ack("h", 80, 1.0)["connected"] is True


# --- Family-aware transport tests for probe_rst ---


def test_probe_rst_ipv6_uses_af_inet6(monkeypatch) -> None:
    """An IPv6 target resolves to an AF_INET6 TCP socket."""
    import socket

    from ethscan import osdetect

    captured: dict[str, object] = {}

    class FakeSock:
        def __init__(self, family, socktype, proto):
            captured["family"] = family
            captured["socktype"] = socktype
            captured["proto"] = proto

        def settimeout(self, timeout):
            pass

        def connect_ex(self, sockaddr):
            captured["sockaddr"] = sockaddr
            return 111  # Connection refused

        def close(self):
            pass

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [
            (
                socket.AF_INET6,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("::1", 80, 0, 0),
            )
        ],
    )
    monkeypatch.setattr("ethscan.osdetect.socket.socket", FakeSock)

    res = osdetect.probe_rst("::1", 80, 1.0)
    assert res["response"] == "RST"
    assert captured["family"] == socket.AF_INET6
    assert captured["sockaddr"] == ("::1", 80, 0, 0)


def test_probe_rst_ipv4_uses_af_inet(monkeypatch) -> None:
    """An IPv4 target resolves to an AF_INET TCP socket."""
    import socket

    from ethscan import osdetect

    captured: dict[str, object] = {}

    class FakeSock:
        def __init__(self, family, socktype, proto):
            captured["family"] = family

        def settimeout(self, timeout):
            pass

        def connect_ex(self, sockaddr):
            captured["sockaddr"] = sockaddr
            return 111  # Connection refused

        def close(self):
            pass

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("127.0.0.1", 80),
            )
        ],
    )
    monkeypatch.setattr("ethscan.osdetect.socket.socket", FakeSock)

    res = osdetect.probe_rst("127.0.0.1", 80, 1.0)
    assert res["response"] == "RST"
    assert captured["family"] == socket.AF_INET
    assert captured["sockaddr"] == ("127.0.0.1", 80)


def test_probe_rst_getaddrinfo_failure_is_reported(monkeypatch) -> None:
    """getaddrinfo OSError is reported as NO-RESPONSE with error."""
    import socket

    from ethscan import osdetect

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: (_ for _ in ()).throw(socket.gaierror("name resolution failed")),
    )

    res = osdetect.probe_rst("bad.host", 80, 1.0)
    assert res["response"] == "NO-RESPONSE"
    assert res["error"] is not None
    assert "name resolution failed" in str(res["error"])


def test_probe_rst_empty_getaddrinfo_is_reported(monkeypatch) -> None:
    """Empty getaddrinfo result is reported as NO-RESPONSE with error."""
    from ethscan import osdetect

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [],
    )

    res = osdetect.probe_rst("bad.host", 80, 1.0)
    assert res["response"] == "NO-RESPONSE"
    assert res["error"] is not None
    assert "no address found" in str(res["error"])


# --- Family-aware transport tests for probe_fin ---


def test_probe_fin_ipv6_uses_af_inet6(monkeypatch) -> None:
    """An IPv6 target resolves to an AF_INET6 TCP socket."""
    import socket

    from ethscan import osdetect

    captured: dict[str, object] = {}

    class FakeSock:
        def __init__(self, family, socktype, proto):
            captured["family"] = family
            captured["socktype"] = socktype
            captured["proto"] = proto

        def settimeout(self, timeout):
            pass

        def connect_ex(self, sockaddr):
            captured["sockaddr"] = sockaddr
            return 111  # Connection refused

        def close(self):
            pass

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [
            (
                socket.AF_INET6,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("::1", 80, 0, 0),
            )
        ],
    )
    monkeypatch.setattr("ethscan.osdetect.socket.socket", FakeSock)

    res = osdetect.probe_fin("::1", 80, 1.0)
    assert res["response"] == "RST"
    assert captured["family"] == socket.AF_INET6
    assert captured["sockaddr"] == ("::1", 80, 0, 0)


def test_probe_fin_ipv4_uses_af_inet(monkeypatch) -> None:
    """An IPv4 target resolves to an AF_INET TCP socket."""
    import socket

    from ethscan import osdetect

    captured: dict[str, object] = {}

    class FakeSock:
        def __init__(self, family, socktype, proto):
            captured["family"] = family

        def settimeout(self, timeout):
            pass

        def connect_ex(self, sockaddr):
            captured["sockaddr"] = sockaddr
            return 111  # Connection refused

        def close(self):
            pass

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("127.0.0.1", 80),
            )
        ],
    )
    monkeypatch.setattr("ethscan.osdetect.socket.socket", FakeSock)

    res = osdetect.probe_fin("127.0.0.1", 80, 1.0)
    assert res["response"] == "RST"
    assert captured["family"] == socket.AF_INET
    assert captured["sockaddr"] == ("127.0.0.1", 80)


def test_probe_fin_getaddrinfo_failure_is_reported(monkeypatch) -> None:
    """getaddrinfo OSError is reported as NO-RESPONSE with error."""
    import socket

    from ethscan import osdetect

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: (_ for _ in ()).throw(socket.gaierror("name resolution failed")),
    )

    res = osdetect.probe_fin("bad.host", 80, 1.0)
    assert res["response"] == "NO-RESPONSE"
    assert res["error"] is not None
    assert "name resolution failed" in str(res["error"])


def test_probe_fin_empty_getaddrinfo_is_reported(monkeypatch) -> None:
    """Empty getaddrinfo result is reported as NO-RESPONSE with error."""
    from ethscan import osdetect

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [],
    )

    res = osdetect.probe_fin("bad.host", 80, 1.0)
    assert res["response"] == "NO-RESPONSE"
    assert res["error"] is not None
    assert "no address found" in str(res["error"])


# --- Family-aware transport tests for probe_ack ---


def test_probe_ack_ipv6_uses_af_inet6(monkeypatch) -> None:
    """An IPv6 target resolves to an AF_INET6 TCP socket."""
    import socket

    from ethscan import osdetect

    captured: dict[str, object] = {}

    class FakeSock:
        def __init__(self, family, socktype, proto):
            captured["family"] = family
            captured["socktype"] = socktype
            captured["proto"] = proto

        def settimeout(self, timeout):
            pass

        def connect_ex(self, sockaddr):
            captured["sockaddr"] = sockaddr
            return 111  # Connection refused

        def close(self):
            pass

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [
            (
                socket.AF_INET6,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("::1", 80, 0, 0),
            )
        ],
    )
    monkeypatch.setattr("ethscan.osdetect.socket.socket", FakeSock)

    res = osdetect.probe_ack("::1", 80, 1.0)
    assert res["response"] == "RST"
    assert captured["family"] == socket.AF_INET6
    assert captured["sockaddr"] == ("::1", 80, 0, 0)


def test_probe_ack_ipv4_uses_af_inet(monkeypatch) -> None:
    """An IPv4 target resolves to an AF_INET TCP socket."""
    import socket

    from ethscan import osdetect

    captured: dict[str, object] = {}

    class FakeSock:
        def __init__(self, family, socktype, proto):
            captured["family"] = family

        def settimeout(self, timeout):
            pass

        def connect_ex(self, sockaddr):
            captured["sockaddr"] = sockaddr
            return 111  # Connection refused

        def close(self):
            pass

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("127.0.0.1", 80),
            )
        ],
    )
    monkeypatch.setattr("ethscan.osdetect.socket.socket", FakeSock)

    res = osdetect.probe_ack("127.0.0.1", 80, 1.0)
    assert res["response"] == "RST"
    assert captured["family"] == socket.AF_INET
    assert captured["sockaddr"] == ("127.0.0.1", 80)


def test_probe_ack_getaddrinfo_failure_is_reported(monkeypatch) -> None:
    """getaddrinfo OSError is reported as NO-RESPONSE with error."""
    import socket

    from ethscan import osdetect

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: (_ for _ in ()).throw(socket.gaierror("name resolution failed")),
    )

    res = osdetect.probe_ack("bad.host", 80, 1.0)
    assert res["response"] == "NO-RESPONSE"
    assert res["error"] is not None
    assert "name resolution failed" in str(res["error"])


def test_probe_ack_empty_getaddrinfo_is_reported(monkeypatch) -> None:
    """Empty getaddrinfo result is reported as NO-RESPONSE with error."""
    from ethscan import osdetect

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [],
    )

    res = osdetect.probe_ack("bad.host", 80, 1.0)
    assert res["response"] == "NO-RESPONSE"
    assert res["error"] is not None
    assert "no address found" in str(res["error"])


def test_run_osdetect_connected_infers_linux() -> None:
    from unittest.mock import patch

    from ethscan import osdetect
    syn1 = {"port": 80, "connected": True, "response": "SYN-ACK", "probe_type": "SYN", "flags_observed": "SYN-ACK", "error": None}
    syn2 = {"port": 443, "connected": False, "response": "NO-RESPONSE", "probe_type": "SYN", "flags_observed": None, "error": None}
    with patch("ethscan.osdetect.probe_syn", side_effect=[syn1, syn2]):
        res = osdetect.run_osdetect("example.com", ports=[80, 443], timeout=1.0, max_workers=2)
        assert "Linux" in res["inferred_os"]


def test_format_markdown_truncates_long_error() -> None:
    from ethscan import osdetect
    data = {
        "target": "example.com", "host": "example.com", "timeout": 1.0,
        "ports_probed": 1, "probes": [
            {"port": 80, "connected": False, "response": "NO-RESPONSE", "flags_observed": None, "error": "e" * 200}
        ],
        "inferred_os": [], "inferred_os_count": 0, "banners_provided": False, "notes": []
    }
    out = osdetect.format_osdetect_report_markdown(data)
    assert "..." in out


def test_match_os_from_banner_solaris() -> None:
    from ethscan import osdetect
    assert "Solaris" in osdetect._match_os_from_banner("SunOS 5.10")


def test_match_os_from_ttl_bsd_solaris() -> None:
    from ethscan import osdetect
    assert "BSD" in osdetect._match_os_from_ttl(255)
    assert "Solaris" in osdetect._match_os_from_ttl(255)


def test_run_osdetect_no_inferred_adds_notes() -> None:
    from unittest.mock import patch

    from ethscan import osdetect
    with patch("ethscan.osdetect.probe_syn", return_value={
        "port": 80, "connected": False, "response": "NO-RESPONSE", "probe_type": "SYN", "flags_observed": None, "error": None
    }), patch("ethscan.osdetect._match_os_from_banner", return_value=[]), patch("ethscan.osdetect._match_os_from_behavior", return_value=[]):
            res = osdetect.run_osdetect("example.com", ports=[80], timeout=1.0, max_workers=1)
            assert any("No OS signature matched" in n for n in res["notes"])


def test_osdetect_transport_failure_is_reported_not_raised(monkeypatch) -> None:
    """A failing TCP connect is reported as a NO-RESPONSE probe, not raised."""
    import ethscan.osdetect

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.osdetect.socket.create_connection", boom)

    results = ethscan.osdetect.run_osdetect("127.0.0.1", ports=[80])

    assert isinstance(results, dict)
    probe = results["probes"][0]
    assert probe["response"] == "NO-RESPONSE"
    assert "hostile transport" in cast(str, probe.get("error") or "")


def test_run_osdetect_invalid_max_workers_reports_probes() -> None:
    """A non-positive max_workers fails executor creation; the outer except
    reports NO-RESPONSE probes for every port instead of raising (lines 424-425)."""
    result = run_osdetect("example.com", ports=[22, 80], max_workers=0)
    assert result["ports_probed"] == 2
    assert len(result["probes"]) == 2
    assert {p["port"] for p in result["probes"]} == {22, 80}
    for probe in result["probes"]:
        assert probe["connected"] is False
        assert probe["response"] == "NO-RESPONSE"
        assert probe["probe_type"] == "SYN"
        assert probe["flags_observed"] is None
        assert probe["error"]
