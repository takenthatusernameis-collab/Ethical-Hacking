"""Tests for the scanner service-detection feature.

Covers the ``--service-detect`` code path added to ``ethscan/scanner.py`` and
``ethscan/cli.py``:

- ``scanner.grab_banner`` real-socket paths (open port banner, HTTP HEAD
  fallback, transport errors swallowed, non-HTTP port with no data).
- ``scanner.scan_ports_with_service`` with and without ``service_detect``,
  and with an open port whose banner is grabbed.
- The CLI ``scan --service-detect`` branch (previously uncovered lines
  996-998) and its JSON / markdown / CSV rendering.
- The markdown / CSV formatter ``service_detect`` branches (table header,
  banner column, banner pipe-escaping, over-long banner truncation).
"""
from __future__ import annotations

import json

from click.testing import CliRunner

import ethscan.cli as cli_module
from ethscan.cli import cli
from ethscan.scanner import (
    format_scan_report_csv,
    format_scan_report_markdown,
    grab_banner,
    scan_ports_with_service,
)


class _FakeSock:
    """Minimal socket stand-in for grab_banner tests."""

    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = list(chunks)
        self.sent = b""

    def settimeout(self, timeout: float) -> None:
        pass

    def recv(self, n: int) -> bytes:
        if self._chunks:
            return self._chunks.pop(0)
        return b""

    def sendall(self, data: bytes) -> None:
        self.sent += data

    def __enter__(self) -> "_FakeSock":
        return self

    def __exit__(self, *args: object) -> None:
        pass


def _patch_connection(monkeypatch, sock: _FakeSock) -> None:
    monkeypatch.setattr(
        "ethscan.scanner.socket.create_connection",
        lambda addr, timeout=None: sock,
    )


def test_grab_banner_returns_first_chunk(monkeypatch) -> None:
    """A port that sends a banner immediately returns it."""
    sock = _FakeSock([b"SSH-2.0-OpenSSH_8.9\r\n"])
    _patch_connection(monkeypatch, sock)

    assert grab_banner("127.0.0.1", 22, 1.0) == "SSH-2.0-OpenSSH_8.9"


def test_grab_banner_http_head_fallback(monkeypatch) -> None:
    """A silent HTTP port is elicited with a HEAD request."""
    sock = _FakeSock([b"", b"HTTP/1.1 200 OK\r\nServer: nginx\r\n\r\n"])
    _patch_connection(monkeypatch, sock)

    banner = grab_banner("127.0.0.1", 80, 1.0)
    assert banner is not None
    assert "200 OK" in banner
    assert b"HEAD / HTTP/1.0" in sock.sent


def test_grab_banner_non_http_port_no_data_returns_none(monkeypatch) -> None:
    """A non-HTTP port that sends nothing yields None."""
    sock = _FakeSock([b""])
    _patch_connection(monkeypatch, sock)

    assert grab_banner("127.0.0.1", 12345, 1.0) is None


def test_grab_banner_connection_error_returns_none(monkeypatch) -> None:
    """A transport error during connect is swallowed and yields None."""

    def boom(addr, timeout=None):
        raise OSError("refused")

    monkeypatch.setattr("ethscan.scanner.socket.create_connection", boom)

    assert grab_banner("127.0.0.1", 80, 1.0) is None


def test_grab_banner_recv_error_falls_through(monkeypatch) -> None:
    """A recv error on a non-HTTP port is swallowed and yields None."""

    class _BoomSock(_FakeSock):
        def recv(self, n: int) -> bytes:
            raise OSError("recv failed")

    _patch_connection(monkeypatch, _BoomSock([]))

    assert grab_banner("127.0.0.1", 12345, 1.0) is None


def test_grab_banner_http_send_error_returns_none(monkeypatch) -> None:
    """A send error on the HTTP HEAD fallback is swallowed and yields None."""

    class _SendBoomSock(_FakeSock):
        def recv(self, n: int) -> bytes:
            return b""

        def sendall(self, data: bytes) -> None:
            raise OSError("send failed")

    _patch_connection(monkeypatch, _SendBoomSock([]))

    assert grab_banner("127.0.0.1", 80, 1.0) is None


def test_scan_ports_with_service_disabled_skips_banner(monkeypatch) -> None:
    """With service_detect False, banners are never grabbed."""
    monkeypatch.setattr(
        "ethscan.scanner.scan_port",
        lambda host, port, timeout=1.0: (port, port == 80),
    )

    def _fail(*args, **kwargs):
        raise AssertionError("grab_banner must not be called")

    monkeypatch.setattr("ethscan.scanner.grab_banner", _fail)

    results = scan_ports_with_service(
        "127.0.0.1", [80, 81], timeout=0.1, max_workers=2, service_detect=False
    )
    assert results == [(80, True, None), (81, False, None)]


def test_scan_ports_with_service_enabled_grabs_banner(monkeypatch) -> None:
    """With service_detect True, open ports get a banner grabbed."""
    monkeypatch.setattr(
        "ethscan.scanner.scan_port",
        lambda host, port, timeout=1.0: (port, port == 80),
    )
    monkeypatch.setattr(
        "ethscan.scanner.grab_banner",
        lambda host, port, timeout: "banner-80",
    )

    results = scan_ports_with_service(
        "127.0.0.1", [80, 81], timeout=0.1, max_workers=2, service_detect=True
    )
    assert results == [(80, True, "banner-80"), (81, False, None)]


def test_scan_report_markdown_service_detect_banner_column() -> None:
    """Markdown service-detect output includes the banner column and escapes pipes."""
    data = {
        "target": "example.com",
        "host": "example.com",
        "ports_scanned": 2,
        "open_ports": [80],
        "service_detect": True,
        "details": [
            {"port": 80, "open": True, "banner": "a|b"},
            {"port": 81, "open": False},
        ],
    }
    md = format_scan_report_markdown(data)
    assert "- **Service Detection:** Enabled" in md
    assert "| Port | Status | Service / Banner |" in md
    assert "a\\|b" in md


def test_scan_report_markdown_service_detect_truncates_long_banner() -> None:
    """An over-long banner is truncated to 77 chars plus an ellipsis."""
    long_banner = "X" * 200
    data = {
        "target": "example.com",
        "service_detect": True,
        "details": [{"port": 80, "open": True, "banner": long_banner}],
    }
    md = format_scan_report_markdown(data)
    assert "X" * 77 + "..." in md


def test_scan_report_csv_service_detect_banner_column() -> None:
    """CSV service-detect output has a banner column with values."""
    data = {
        "target": "example.com",
        "service_detect": True,
        "details": [
            {"port": 80, "open": True, "banner": "nginx"},
            {"port": 81, "open": False},
        ],
    }
    csv_text = format_scan_report_csv(data)
    lines = csv_text.splitlines()
    assert lines[0] == "port,open,banner"
    assert lines[1] == "80,true,nginx"
    assert lines[2] == "81,false,"


def test_cli_scan_service_detect_json(monkeypatch) -> None:
    """`scan --service-detect` routes through scan_ports_with_service (JSON)."""
    called: dict[str, object] = {}

    def mock_scan_with_service(host, ports, timeout=1.0, max_workers=100, service_detect=False):
        called["host"] = host
        called["ports"] = ports
        called["service_detect"] = service_detect
        return [(80, True, "nginx"), (81, False, None)]

    # Patch the module object the ``cli`` group is bound to. A string target
    # would re-import ``ethscan.cli`` after a prior test popped it from
    # ``sys.modules``, patching a fresh module the captured ``cli`` does not
    # use, which would let the real network path run.
    monkeypatch.setattr(cli_module, "scan_ports_with_service", mock_scan_with_service)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["scan", "--target", "example.com", "--ports", "80,81", "--service-detect"],
    )
    assert result.exit_code == 0, result.output
    assert called["service_detect"] is True
    payload = json.loads(result.output)
    assert payload["open_ports"] == [80]
    assert payload["service_detect"] is True
    assert payload["details"][0]["banner"] == "nginx"


def test_cli_scan_service_detect_markdown(monkeypatch) -> None:
    """`scan --service-detect --output-format markdown` renders the banner column."""

    def mock_scan_with_service(host, ports, timeout=1.0, max_workers=100, service_detect=False):
        return [(80, True, "nginx")]

    monkeypatch.setattr(cli_module, "scan_ports_with_service", mock_scan_with_service)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "scan",
            "--target",
            "example.com",
            "--ports",
            "80",
            "--service-detect",
            "--output-format",
            "markdown",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Service / Banner" in result.output
    assert "nginx" in result.output


def test_cli_scan_no_service_detect_uses_plain_scan(monkeypatch) -> None:
    """Without --service-detect the plain scan_ports path is used."""

    def mock_scan_ports(host, ports, timeout=1.0, max_workers=100):
        return [(p, False) for p in ports]

    def _fail(*args, **kwargs):
        raise AssertionError("scan_ports_with_service must not be called")

    monkeypatch.setattr(cli_module, "scan_ports", mock_scan_ports)
    monkeypatch.setattr(cli_module, "scan_ports_with_service", _fail)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["scan", "--target", "example.com", "--ports", "80,81"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["service_detect"] is False