"""Tests for the ethscan ftp module."""

from __future__ import annotations

import csv
import ftplib
import io
import json
import socket
import socketserver
import struct
import threading

import pytest

from ethscan.ftp import (
    DEFAULT_PORT,
    _connect,
    _normalize_target,
    format_ftp_report_csv,
    format_ftp_report_json,
    format_ftp_report_markdown,
    run_ftp,
)

# ---------------------------------------------------------------------------
# Fake FTP client (mirrors the ftplib.FTP interface) for deterministic tests
# ---------------------------------------------------------------------------


class _FakeFTP:
    """A stateful fake FTP client driven by class-level config.

    Behaves like ``ftplib.FTP``: ``connect`` stores host/port, ``getwelcome``
    returns the configured greeting, ``login`` simulates anonymous auth, and
    ``close`` is a no-op.
    """

    config: dict | None = None

    def __init__(self) -> None:
        self.host = None
        self.port = None
        self.config = {}
        self.connected = False
        self.closed = False

    def connect(self, host: str, port: int = 21, timeout: float = 30) -> str:
        if isinstance(self.config, dict) and self.config.get("refuse"):
            raise ConnectionRefusedError("Connection refused")
        if isinstance(self.config, dict) and self.config.get("timeout"):
            raise socket.timeout("timed out")
        self.host = host
        self.port = port
        self.connected = True
        banner = self.config.get("banner") if isinstance(self.config, dict) else None
        return banner or "220 fake.ftp.example FTP server ready"

    def getwelcome(self) -> str:
        if not self.connected:
            raise ftplib.Error("not connected")
        if isinstance(self.config, dict) and self.config.get("no_welcome"):
            raise ftplib.Error("503 Bad sequence of commands")
        return self.config.get("banner", "220 fake.ftp.example FTP server ready") if isinstance(self.config, dict) else "220 fake.ftp.example FTP server ready"

    def login(self, user: str = "anonymous", passwd: str = "", account: str = "") -> str:
        if isinstance(self.config, dict) and self.config.get("anonymous_allowed", True):
            return "230 " + self.config.get("login_msg", "Login successful")
        raise ftplib.Error(self.config.get("login_err", "530 Login incorrect"))

    def close(self) -> None:
        if isinstance(self.config, dict) and self.config.get("close_raises"):
            raise ftplib.Error("close failed")
        self.closed = True


# ---------------------------------------------------------------------------
# Fake FTP server (real socket) for the hostile-answer tests
# ---------------------------------------------------------------------------


class _FakeFTPHandler(socketserver.BaseRequestHandler):
    """A tiny stateful fake FTP server driven by the server instance config.

    The ``mode`` key of the config selects the hostile behaviour:

    * ``normal`` -- answer USER with 331 and PASS with 230 (or 530).
    * ``close_without_greeting`` -- close the connection without a greeting.
    * ``close_during_login`` -- close the connection instead of answering USER.
    * ``reset_during_login`` -- reset the connection instead of answering USER.
    * ``non_utf8_during_login`` -- answer USER with a byte that is not UTF-8.
    """

    def handle(self) -> None:
        s = self.request
        s.settimeout(5.0)
        cfg = self.server.ftp_config  # type: ignore[attr-defined]
        mode = cfg.get("mode", "normal")

        if mode == "close_without_greeting":
            s.close()
            return

        banner = cfg.get("banner", "220 fake.ftp.example ready")
        s.sendall(banner.encode("utf-8") + b"\r\n")

        sockfile = s.makefile("rb")
        while True:
            try:
                line = sockfile.readline()
            except (OSError, socket.timeout):
                break
            if not line:
                break
            command = line.decode("utf-8", errors="replace").strip().upper()

            if command.startswith("USER"):
                if mode == "close_during_login":
                    s.close()
                    return
                if mode == "reset_during_login":
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
                    s.close()
                    return
                if mode == "non_utf8_during_login":
                    s.sendall(b"331 password required \xff\r\n")
                    continue
                s.sendall(b"331 password required\r\n")
            elif command.startswith("PASS"):
                if cfg.get("anonymous_allowed", True):
                    s.sendall(b"230 logged in\r\n")
                else:
                    s.sendall(b"530 login incorrect\r\n")
            elif command.startswith("QUIT"):
                s.sendall(b"221 bye\r\n")
                break
            else:
                s.sendall(b"500 unknown command\r\n")


class _FakeFTPServer(socketserver.TCPServer):
    allow_reuse_address = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ftp_config: dict = {}


@pytest.fixture()
def fake_ftp():
    """Start a fake FTP server; yield (host, port, server) and shut it down."""
    server = _FakeFTPServer(("127.0.0.1", 0), _FakeFTPHandler)
    server.ftp_config = {}
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "127.0.0.1", server.server_address[1], server
    finally:
        server.shutdown()
        server.server_close()


# ---------------------------------------------------------------------------
# _normalize_target
# ---------------------------------------------------------------------------


def test_normalize_target_bare_host() -> None:
    host, port = _normalize_target("ftp.example.com")
    assert host == "ftp.example.com"
    assert port == DEFAULT_PORT


def test_normalize_target_host_port() -> None:
    host, port = _normalize_target("ftp.example.com:2121")
    assert host == "ftp.example.com"
    assert port == 2121


def test_normalize_target_url_with_port() -> None:
    host, port = _normalize_target("ftp://ftp.example.com:2121")
    assert host == "ftp.example.com"
    assert port == 2121


def test_normalize_target_url_default_port() -> None:
    host, port = _normalize_target("ftp://ftp.example.com")
    assert host == "ftp.example.com"
    assert port == DEFAULT_PORT


def test_normalize_target_empty_raises() -> None:
    with pytest.raises(ValueError):
        _normalize_target("   ")


def test_normalize_target_ipv6_url() -> None:
    host, port = _normalize_target("ftp://[::1]:21")
    assert host == "::1"
    assert port == 21
    host, port = _normalize_target("[::1]:21")
    assert host == "::1"
    assert port == 21
    host, port = _normalize_target("[::1]")
    assert host == "::1"
    assert port == DEFAULT_PORT


# ---------------------------------------------------------------------------
# _connect
# ---------------------------------------------------------------------------


def test_connect_uses_connector() -> None:
    captured = {}

    class Recorder:
        def connect(self, host, port, timeout=30):
            captured["host"] = host
            captured["port"] = port
            captured["timeout"] = timeout
            return "ok"

        def close(self):
            pass

    client = _connect("127.0.0.1", 21, 2.0, connector=Recorder)
    assert captured == {"host": "127.0.0.1", "port": 21, "timeout": 2.0}
    assert isinstance(client, Recorder)


def test_connect_real_ftplib_refused() -> None:
    # Connecting to a closed port should raise OSError (ConnectionRefusedError).
    with pytest.raises(OSError):
        _connect("127.0.0.1", 1, 1.0, connector=ftplib.FTP)


# ---------------------------------------------------------------------------
# run_ftp – against local fake FTP client
# ---------------------------------------------------------------------------


def test_run_ftp_full_interaction() -> None:
    def factory():
        c = _FakeFTP()
        c.config = {"banner": "220 fake.ftp.example FTP server ready", "anonymous_allowed": True}
        return c

    result = run_ftp("ftp.example.com", timeout=2.0, connector=factory)
    assert result["connected"] is True
    assert result["host"] == "ftp.example.com"
    assert result["port"] == DEFAULT_PORT
    assert result["banner"] == "220 fake.ftp.example FTP server ready"
    assert result["welcome_message"] == result["banner"]
    assert result["anonymous_login"] is True
    assert result["anonymous_message"] == "anonymous login successful"
    assert result["error"] is None


def test_run_ftp_anonymous_disallowed() -> None:
    def factory():
        c = _FakeFTP()
        c.config = {
            "banner": "220 fake.ftp.example FTP server ready",
            "anonymous_allowed": False,
            "login_err": "530 Anonymous access denied",
        }
        return c

    result = run_ftp("ftp.example.com", timeout=2.0, connector=factory)
    assert result["connected"] is True
    assert result["anonymous_login"] is False
    assert "Anonymous access denied" in result["anonymous_message"]
    assert result["error"] is None


def test_run_ftp_no_anonymous_check() -> None:
    def factory():
        c = _FakeFTP()
        c.config = {"banner": "220 fake.ftp.example FTP server ready"}
        return c

    result = run_ftp("ftp.example.com", timeout=2.0, check_anonymous=False, connector=factory)
    assert result["connected"] is True
    assert result["anonymous_login"] is None
    assert result["anonymous_message"] is None
    assert result["check_anonymous"] is False


def test_run_ftp_connection_refused() -> None:
    def factory():
        c = _FakeFTP()
        c.config = {"refuse": True}
        return c

    result = run_ftp("127.0.0.1", port=1, timeout=1.0, connector=factory)
    assert result["connected"] is False
    assert result["banner"] is None
    assert result["anonymous_login"] is None
    assert result["error"] is not None
    assert "connection failed" in result["error"]


def test_run_ftp_connection_timeout() -> None:
    def factory():
        c = _FakeFTP()
        c.config = {"timeout": True}
        return c

    result = run_ftp("127.0.0.1", port=1, timeout=1.0, connector=factory)
    assert result["connected"] is False
    assert result["error"] is not None
    assert "connection failed" in result["error"]


def test_run_ftp_banner_read_failed() -> None:
    def factory():
        c = _FakeFTP()
        c.config = {"banner": "220 fake.ftp.example", "no_welcome": True}
        return c

    result = run_ftp("ftp.example.com", timeout=2.0, connector=factory)
    assert result["connected"] is True
    assert result["banner"] is None
    assert "banner read failed" in result["error"]


def test_run_ftp_transport_failure_is_reported() -> None:
    """A transport failure of an unnamed type is reported, not raised."""

    def factory():
        raise RuntimeError("hostile transport")

    result = run_ftp("ftp.example.com", timeout=2.0, connector=factory)
    assert result["connected"] is False
    assert result["error"] is not None
    assert "connection failed" in result["error"]
    assert "hostile transport" in result["error"]


def test_run_ftp_banner_read_transport_failure_is_reported() -> None:
    """A banner that cannot be read is reported, not raised."""

    class _BoomBanner:
        def connect(self, host, port, timeout=30):
            return "220 ready"

        def getwelcome(self):
            raise RuntimeError("hostile transport")

        def login(self, user="anonymous", passwd="", account=""):
            raise ftplib.Error("530 Login incorrect")

        def close(self):
            pass

    result = run_ftp("ftp.example.com", timeout=2.0, connector=_BoomBanner)
    assert result["connected"] is True
    assert result["banner"] is None
    assert "banner read failed" in result["error"]
    assert "hostile transport" in result["error"]


def test_run_ftp_close_raises_swallowed() -> None:
    def factory():
        c = _FakeFTP()
        c.config = {"banner": "220 fake.ftp.example FTP server ready", "close_raises": True}
        return c

    result = run_ftp("ftp.example.com", timeout=2.0, connector=factory)
    assert result["connected"] is True
    assert result["error"] is None


def test_run_ftp_port_override() -> None:
    captured = {}

    class Recorder:
        def connect(self, host, port, timeout=30):
            captured["port"] = port
            captured["host"] = host
            return "220 ready"

        def getwelcome(self):
            return "220 ready"

        def login(self, user="anonymous", passwd="", account=""):
            return "230 ok"

        def close(self):
            pass

    result = run_ftp("ftp.example.com", port=2121, timeout=2.0, check_anonymous=False, connector=Recorder)
    assert captured["port"] == 2121
    assert captured["host"] == "ftp.example.com"
    assert result["port"] == 2121


def test_run_ftp_real_connection_refused() -> None:
    # Integration check: real ftplib against a closed port.
    result = run_ftp("127.0.0.1", port=1, timeout=1.0)
    assert result["connected"] is False
    assert result["error"] is not None
    assert "connection failed" in result["error"]


# ---------------------------------------------------------------------------
# run_ftp – against a real socket, with a hostile server
# ---------------------------------------------------------------------------


def test_run_ftp_anonymous_login_over_socket(fake_ftp) -> None:
    # Control: an ordinary server is still probed over a real socket.
    host, port, server = fake_ftp
    server.ftp_config = {"mode": "normal"}
    result = run_ftp(host, port=port, timeout=5.0)
    assert result["connected"] is True
    assert result["banner"] == "220 fake.ftp.example ready"
    assert result["anonymous_login"] is True
    assert result["error"] is None


def test_run_ftp_login_denied_over_socket(fake_ftp) -> None:
    # Control: a server that refuses the login is reported as "not allowed".
    host, port, server = fake_ftp
    server.ftp_config = {"mode": "normal", "anonymous_allowed": False}
    result = run_ftp(host, port=port, timeout=5.0)
    assert result["connected"] is True
    assert result["anonymous_login"] is False
    assert result["error"] is None


def test_run_ftp_server_closes_without_greeting(fake_ftp) -> None:
    # A server that closes the connection without a greeting makes ftplib
    # raise EOFError, which the module's guard did not catch.
    host, port, server = fake_ftp
    server.ftp_config = {"mode": "close_without_greeting"}
    result = run_ftp(host, port=port, timeout=5.0)
    assert result["connected"] is False
    assert result["banner"] is None
    assert result["error"] is not None
    assert "connection failed" in result["error"]
    assert "closed the connection" in result["error"]


def test_run_ftp_server_closes_during_login(fake_ftp) -> None:
    # A server that drops the connection instead of answering USER makes
    # ftplib raise EOFError.
    host, port, server = fake_ftp
    server.ftp_config = {"mode": "close_during_login"}
    result = run_ftp(host, port=port, timeout=5.0)
    assert result["connected"] is True
    assert result["anonymous_login"] is None
    assert result["error"] is not None
    assert "login failed" in result["error"]
    assert "closed the connection" in result["error"]


def test_run_ftp_server_resets_connection_during_login(fake_ftp) -> None:
    # A server that resets the connection instead of answering USER makes
    # ftplib raise ConnectionResetError, an OSError.
    host, port, server = fake_ftp
    server.ftp_config = {"mode": "reset_during_login"}
    result = run_ftp(host, port=port, timeout=5.0)
    assert result["connected"] is True
    assert result["anonymous_login"] is None
    assert result["error"] is not None
    assert "login failed" in result["error"]


def test_run_ftp_non_utf8_reply_during_login(fake_ftp) -> None:
    # A server that answers USER with a byte that is not UTF-8 makes ftplib
    # raise a UnicodeDecodeError, which is a ValueError.
    host, port, server = fake_ftp
    server.ftp_config = {"mode": "non_utf8_during_login"}
    result = run_ftp(host, port=port, timeout=5.0)
    assert result["connected"] is True
    assert result["anonymous_login"] is None
    assert result["error"] is not None
    assert "login failed" in result["error"]
    assert "decode" in result["error"]


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


_FTP_SAMPLE = {
    "target": "ftp.example.com",
    "host": "ftp.example.com",
    "port": 21,
    "connected": True,
    "banner": "220 (vsFTPd 3.0.3)",
    "welcome_message": "220 (vsFTPd 3.0.3)",
    "anonymous_login": True,
    "anonymous_message": "anonymous login successful",
    "check_anonymous": True,
    "error": None,
}

_FTP_SAMPLE_DENIED = {
    "target": "ftp.example.com",
    "host": "ftp.example.com",
    "port": 21,
    "connected": True,
    "banner": "220 (vsFTPd 3.0.3)",
    "welcome_message": "220 (vsFTPd 3.0.3)",
    "anonymous_login": False,
    "anonymous_message": "530 Login incorrect",
    "check_anonymous": True,
    "error": None,
}

_FTP_SAMPLE_FAILED = {
    "target": "dead.example.com",
    "host": "dead.example.com",
    "port": 21,
    "connected": False,
    "banner": None,
    "welcome_message": None,
    "anonymous_login": None,
    "anonymous_message": None,
    "check_anonymous": True,
    "error": "connection failed: [Errno 111] Connection refused",
}


def test_format_ftp_report_json() -> None:
    output = format_ftp_report_json(_FTP_SAMPLE)
    parsed = json.loads(output)
    assert parsed["host"] == "ftp.example.com"
    assert parsed["anonymous_login"] is True
    assert parsed["banner"] == "220 (vsFTPd 3.0.3)"


def test_format_ftp_report_json_failed() -> None:
    output = format_ftp_report_json(_FTP_SAMPLE_FAILED)
    parsed = json.loads(output)
    assert parsed["connected"] is False
    assert "refused" in parsed["error"]


def test_format_ftp_report_markdown() -> None:
    output = format_ftp_report_markdown(_FTP_SAMPLE)
    assert "# ethscan FTP Report" in output
    assert "ftp.example.com" in output
    assert "220 (vsFTPd 3.0.3)" in output
    assert "Anonymous Login:** allowed" in output


def test_format_ftp_report_markdown_denied() -> None:
    output = format_ftp_report_markdown(_FTP_SAMPLE_DENIED)
    assert "Anonymous Login:** disallowed" in output
    assert "530 Login incorrect" in output


def test_format_ftp_report_markdown_not_checked() -> None:
    data = dict(_FTP_SAMPLE)
    data = {**_FTP_SAMPLE, "anonymous_login": None, "anonymous_message": None, "check_anonymous": False}
    output = format_ftp_report_markdown(data)
    assert "Anonymous Login:** not checked" in output


def test_format_ftp_report_markdown_connection_failed() -> None:
    output = format_ftp_report_markdown(_FTP_SAMPLE_FAILED)
    assert "Connected:** False" in output
    assert "Connection refused" in output
    assert "Anonymous Login:** not checked" in output


def test_format_ftp_report_csv() -> None:
    output = format_ftp_report_csv(_FTP_SAMPLE)
    reader = list(csv.reader(io.StringIO(output)))
    assert reader[0] == ["target", "host", "port", "banner", "anonymous_login", "anonymous_message", "error"]
    assert reader[1] == ["ftp.example.com", "ftp.example.com", "21", "220 (vsFTPd 3.0.3)", "true", "anonymous login successful", ""]


def test_format_ftp_report_csv_denied() -> None:
    output = format_ftp_report_csv(_FTP_SAMPLE_DENIED)
    reader = list(csv.reader(io.StringIO(output)))
    assert reader[1][4] == "false"
    assert reader[1][5] == "530 Login incorrect"


def test_format_ftp_report_csv_failed() -> None:
    output = format_ftp_report_csv(_FTP_SAMPLE_FAILED)
    reader = list(csv.reader(io.StringIO(output)))
    assert reader[1][4] == ""  # anonymous_login is None
    assert "Connection refused" in reader[1][6]


def test_format_ftp_report_csv_comma_escaping() -> None:
    data = {
        "target": "ftp.example.com",
        "host": "ftp.example.com",
        "port": 21,
        "banner": "220 server, ready, for you",
        "anonymous_login": False,
        "anonymous_message": "530, no, way",
        "error": "err, one, two",
    }
    output = format_ftp_report_csv(data)
    reader = list(csv.reader(io.StringIO(output)))
    assert reader[1][3] == "220 server, ready, for you"
    assert reader[1][5] == "530, no, way"
    assert reader[1][6] == "err, one, two"
