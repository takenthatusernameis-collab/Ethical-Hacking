"""Tests for the ethscan service module."""


from ethscan.service import (
    COMMON_SERVICE_PORTS,
    DEFAULT_PORTS,
    DEFAULT_TIMEOUT,
    DEFAULT_WORKERS,
    SERVICE_SIGNATURES,
    format_service_report_csv,
    format_service_report_json,
    format_service_report_markdown,
    grab_banner,
    run_service,
)


def test_defaults() -> None:
    assert DEFAULT_TIMEOUT == 3.0
    assert DEFAULT_WORKERS == 50
    assert 21 in DEFAULT_PORTS
    assert 22 in DEFAULT_PORTS
    assert 80 in DEFAULT_PORTS
    assert 443 in DEFAULT_PORTS


def test_common_service_ports() -> None:
    assert COMMON_SERVICE_PORTS[21] == "ftp"
    assert COMMON_SERVICE_PORTS[22] == "ssh"
    assert COMMON_SERVICE_PORTS[80] == "http"
    assert COMMON_SERVICE_PORTS[443] == "https"
    assert COMMON_SERVICE_PORTS[3306] == "mysql"


def test_service_signatures() -> None:
    assert "ftp" in SERVICE_SIGNATURES
    assert "ssh" in SERVICE_SIGNATURES
    assert "http" in SERVICE_SIGNATURES
    assert len(SERVICE_SIGNATURES["ftp"]) > 0


def test_grab_banner_connection_refused() -> None:
    port, banner, service = grab_banner("127.0.0.1", 9999, 0.5)
    assert port == 9999
    assert banner is None
    assert service is None


def test_grab_banner_timeout() -> None:
    port, banner, service = grab_banner("10.255.255.1", 22, 0.1)
    assert port == 22
    assert banner is None
    assert service is None


def test_run_service_offline(monkeypatch) -> None:
    def mock_grab_banner(host, port, timeout):
        if port == 21:
            return port, "220 ProFTPD 1.3.5 Server ready.", "ProFTPD"
        if port == 22:
            return port, "SSH-2.0-OpenSSH_8.9", "OpenSSH"
        if port == 80:
            return port, "HTTP/1.1 200 OK\r\nServer: nginx", "nginx"
        return port, None, None

    monkeypatch.setattr("ethscan.service.grab_banner", mock_grab_banner)

    result = run_service("example.com", ports=[21, 22, 80, 9999], timeout=1.0)

    assert result["target"] == "example.com"
    assert result["host"] == "example.com"
    assert result["ports_scanned"] == 4
    assert result["services_found"] == 3
    assert len(result["results"]) == 3

    services = {r["port"]: r.get("service") for r in result["results"]}
    assert services[21] == "ProFTPD"
    assert services[22] == "OpenSSH"
    assert services[80] == "nginx"

    banners = {r["port"]: r.get("banner") for r in result["results"]}
    assert "ProFTPD" in banners[21]
    assert "OpenSSH" in banners[22]
    assert "nginx" in banners[80]


def test_run_service_target_normalization(monkeypatch) -> None:
    def mock_grab_banner(host, port, timeout):
        return port, "test banner", "TestService"

    monkeypatch.setattr("ethscan.service.grab_banner", mock_grab_banner)

    result = run_service("https://example.com/path", ports=[80], timeout=1.0)

    assert result["host"] == "example.com"


def test_run_service_custom_ports(monkeypatch) -> None:
    called_ports = []

    def mock_grab_banner(host, port, timeout):
        called_ports.append(port)
        return port, None, None

    monkeypatch.setattr("ethscan.service.grab_banner", mock_grab_banner)

    run_service("example.com", ports=[8080, 8443], timeout=1.0)

    assert called_ports == [8080, 8443]


def test_run_service_transport_failure_reported(monkeypatch) -> None:
    """run_service reports a transport failure of an unnamed type instead of raising."""

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.service.socket.create_connection", boom)

    result = run_service("127.0.0.1", timeout=0.5)

    assert result["services_found"] == 0
    assert result["results"] == []


def test_format_service_report_json() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 3.0,
        "ports_scanned": 3,
        "services_found": 2,
        "results": [
            {"port": 21, "banner": "220 FTP Server ready", "service": "FTP"},
            {"port": 22, "banner": "SSH-2.0-OpenSSH_8.9", "service": "OpenSSH"},
        ],
    }
    output = format_service_report_json(data)
    assert "example.com" in output
    assert "FTP" in output
    assert "OpenSSH" in output
    assert '"port": 21' in output


def test_format_service_report_markdown() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 3.0,
        "ports_scanned": 3,
        "services_found": 2,
        "results": [
            {"port": 21, "banner": "220 FTP Server ready", "service": "FTP"},
            {"port": 22, "banner": "SSH-2.0-OpenSSH_8.9", "service": "OpenSSH"},
        ],
    }
    output = format_service_report_markdown(data)
    assert "# ethscan Service Detection Report" in output
    assert "example.com" in output
    assert "**Ports Scanned:** 3" in output
    assert "**Services Found:** 2" in output
    assert "## Detected Services" in output
    assert "| 21 | FTP |" in output
    assert "| 22 | OpenSSH |" in output


def test_format_service_report_markdown_no_results() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 3.0,
        "ports_scanned": 3,
        "services_found": 0,
        "results": [],
    }
    output = format_service_report_markdown(data)
    assert "*No services detected.*" in output


def test_banner_truncation_in_markdown(monkeypatch) -> None:
    long_banner = "A" * 100

    def mock_grab_banner(host, port, timeout):
        return port, long_banner, "TestService"

    monkeypatch.setattr("ethscan.service.grab_banner", mock_grab_banner)

    result = run_service("example.com", ports=[80], timeout=1.0)
    output = format_service_report_markdown(result)

    assert "..." in output
    assert len(next(line for line in output.split("\n") if "| 80 |" in line)) < 200


# ---------------------------------------------------------------------------
# CSV formatter
# ---------------------------------------------------------------------------


def test_format_service_report_csv_basic() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 3.0,
        "ports_scanned": 3,
        "services_found": 2,
        "results": [
            {"port": 21, "banner": "220 FTP Server ready", "service": "FTP"},
            {"port": 22, "banner": "SSH-2.0-OpenSSH_8.9", "service": "OpenSSH"},
        ],
    }
    output = format_service_report_csv(data)

    lines = [line.rstrip("\r") for line in output.strip().split("\n")]
    assert lines[0] == "port,service,banner"
    assert "21,FTP,220 FTP Server ready" in lines[1]
    assert "22,OpenSSH,SSH-2.0-OpenSSH_8.9" in lines[2]


def test_format_service_report_csv_empty() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 3.0,
        "ports_scanned": 3,
        "services_found": 0,
        "results": [],
    }
    output = format_service_report_csv(data)

    lines = [line.rstrip("\r") for line in output.strip().split("\n")]
    assert lines[0] == "port,service,banner"


def test_format_service_report_csv_missing_optional_fields() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 3.0,
        "ports_scanned": 1,
        "services_found": 1,
        "results": [
            {"port": 8080},  # missing service, banner
        ],
    }
    output = format_service_report_csv(data)

    lines = [line.rstrip("\r") for line in output.strip().split("\n")]
    assert "8080,," in lines[1]


def test_format_service_report_csv_pipe_escaping() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 3.0,
        "ports_scanned": 1,
        "services_found": 1,
        "results": [
            {"port": 80, "banner": "pipe|banner|msg", "service": "weird|service"},
        ],
    }
    output = format_service_report_csv(data)

    # With QUOTE_MINIMAL, pipe characters don't require quoting
    assert "pipe|banner|msg" in output
    assert "weird|service" in output


def test_format_service_report_csv_strips_newlines_in_banners() -> None:
    """Banner newlines are stripped so each result stays on one CSV row."""
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 3.0,
        "ports_scanned": 1,
        "services_found": 1,
        "results": [
            {
                "port": 22,
                "service": "OpenSSH",
                "banner": "SSH-2.0-OpenSSH_8.9\r\nOpenSSH_8.9 secondary line",
            }
        ],
    }
    output = format_service_report_csv(data)
    # Header row + one data row => exactly one newline (the row separator).
    # A banner newline that is NOT stripped will inject extra newlines.
    assert output.count("\n") == 1
    assert "\n" not in output.split("\n", 1)[1]


# ---------------------------------------------------------------------------
# grab_banner real socket paths (lines 125-154 previously uncovered)
# ---------------------------------------------------------------------------


def test_grab_banner_success_with_signature(monkeypatch) -> None:
    """Cover lines 125-129: connect, recv banner, decode, match signature."""

    class FakeSock:
        def __init__(self, data):
            self._data = data
            self._sent = b""

        def settimeout(self, timeout):
            pass

        def recv(self, n):
            if self._data:
                chunk = self._data[:n]
                self._data = self._data[n:]
                return chunk
            return b""

        def sendall(self, data):
            self._sent += data

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    banner_bytes = b"220 ProFTPD 1.3.5 Server ready.\r\n"
    fake = FakeSock(banner_bytes)

    def fake_create_connection(addr, timeout=None):
        return fake

    monkeypatch.setattr("ethscan.service.socket.create_connection", fake_create_connection)
    port_ret, banner_ret, service = grab_banner("127.0.0.1", 21, 2.0)
    assert port_ret == 21
    assert banner_ret is not None
    assert "ProFTPD" in banner_ret
    # "ProFTPD" contains "FTP" so the first ftp signature matches first
    assert service == "FTP"


def test_grab_banner_no_signature_falls_back_to_upper(monkeypatch) -> None:
    """Cover lines 147-154: banner present, service_name known, no signature match."""
    class FakeSock:
        def settimeout(self, timeout):
            pass

        def recv(self, n):
            return b"220 something unknown\r\n"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    fake = FakeSock()
    monkeypatch.setattr("ethscan.service.socket.create_connection", lambda addr, timeout=None: fake)
    port_ret, banner_ret, service = grab_banner("127.0.0.1", 21, 2.0)
    assert port_ret == 21
    assert banner_ret is not None
    assert service == "FTP"  # COMMON_SERVICE_PORTS[21] == 'ftp' -> upper()


def test_grab_banner_http_fallback(monkeypatch) -> None:
    """Cover lines 133-141: http/https banner empty triggers HTTP HEAD request."""
    class FakeSock:
        def __init__(self):
            self._initial = True
            self._sent = b""

        def settimeout(self, timeout):
            pass

        def recv(self, n):
            if self._initial:
                self._initial = False
                return b""  # initial banner empty
            # Respond to HTTP HEAD request
            return b"HTTP/1.1 200 OK\r\nServer: nginx\r\n\r\n"

        def sendall(self, data):
            self._sent += data

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    fake = FakeSock()
    monkeypatch.setattr("ethscan.service.socket.create_connection", lambda addr, timeout=None: fake)
    port_ret, banner_ret, service = grab_banner("127.0.0.1", 80, 2.0)
    assert port_ret == 80
    assert banner_ret is not None
    assert "nginx" in banner_ret
    assert service == "HTTP"  # first http signature matches 200 OK


def test_grab_banner_http_fallback_oserror_caught(monkeypatch) -> None:
    """Cover lines 140-141: OSError during HTTP fallback recv is swallowed."""
    import socket as _socket

    class FakeSock:
        def __init__(self):
            self._initial = True

        def settimeout(self, timeout):
            pass

        def recv(self, n):
            if self._initial:
                self._initial = False
                return b""  # initial banner empty
            raise _socket.timeout("recv timeout")

        def sendall(self, data):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    fake = FakeSock()
    monkeypatch.setattr("ethscan.service.socket.create_connection", lambda addr, timeout=None: fake)
    port_ret, banner_ret, service = grab_banner("127.0.0.1", 80, 2.0)
    assert port_ret == 80
    assert banner_ret is None
    assert service is None


def test_grab_banner_signature_with_capture_group(monkeypatch) -> None:
    """Cover line 151: pattern with capture group sets detected_service to group(1).

    Use a banner that skips the first http signature (no 200 OK line) so the
    second pattern (Server: header with capture group) is reached.
    """
    class FakeSock:
        def settimeout(self, timeout):
            pass

        def recv(self, n):
            return b"Server: Apache/2.4.1\r\n\r\n"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    fake = FakeSock()
    monkeypatch.setattr("ethscan.service.socket.create_connection", lambda addr, timeout=None: fake)
    port_ret, banner_ret, service = grab_banner("127.0.0.1", 80, 2.0)
    assert port_ret == 80
    assert banner_ret is not None
    assert service == "Apache/2.4.1"


def test_grab_banner_initial_recv_oserror_caught(monkeypatch) -> None:
    """Cover lines 130-131: OSError during initial banner recv is swallowed."""
    import socket as _socket

    class FakeSock:
        def __init__(self):
            self._initial = True

        def settimeout(self, timeout):
            pass

        def recv(self, n):
            if self._initial:
                self._initial = False
                raise _socket.timeout("initial banner timeout")
            return b""

        def sendall(self, data):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    fake = FakeSock()
    monkeypatch.setattr("ethscan.service.socket.create_connection", lambda addr, timeout=None: fake)
    port_ret, banner_ret, service = grab_banner("127.0.0.1", 80, 2.0)
    assert port_ret == 80
    assert banner_ret is None
    assert service is None