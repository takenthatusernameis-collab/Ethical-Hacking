"""Tests for the ethscan ftp module."""

import csv
import io
import json
import socket
import threading

import ftplib
import pytest

from ethscan.ftp import (
    DEFAULT_PORT,
    DEFAULT_TIMEOUT,
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

    config: dict = {}

    def __init__(self) -> None:
        self.host = None
        self.port = None
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
        self.closed = True


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
