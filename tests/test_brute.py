"""Tests for the ethscan brute module."""

import types

import pytest

from ethscan.brute import (
    DEFAULT_FTP_PORT,
    DEFAULT_PROTOCOL,
    DEFAULT_SSH_PORT,
    DEFAULT_TIMEOUT,
    _attempt_ftp,
    _attempt_ssh,
    _normalize_host,
    format_brute_report_json,
    format_brute_report_markdown,
    load_wordlist,
    run_brute,
)


def test_defaults() -> None:
    assert DEFAULT_PROTOCOL == "ftp"
    assert DEFAULT_FTP_PORT == 21
    assert DEFAULT_SSH_PORT == 22
    assert DEFAULT_TIMEOUT == 5.0


def test_normalize_host_bare() -> None:
    assert _normalize_host("ftp.example.com") == "ftp.example.com"
    assert _normalize_host("FTP.EXAMPLE.COM") == "ftp.example.com"


def test_normalize_host_url() -> None:
    assert _normalize_host("ftp://ftp.example.com/path") == "ftp.example.com"
    assert _normalize_host("ssh://user@ssh.example.com:2222/") == "ssh.example.com"


def test_load_wordlist(tmp_path) -> None:
    wordlist = tmp_path / "users.txt"
    wordlist.write_text("# comment\nadmin\n\nroot\n")
    assert load_wordlist(str(wordlist)) == ["admin", "root"]


def test_attempt_ftp_success(monkeypatch) -> None:
    class _FakeFTP:
        def __init__(self):
            self.logged_in = False

        def connect(self, host, port, timeout=None):
            self.host = host
            self.port = port

        def login(self, username, password):
            if username == "admin" and password == "secret":
                self.logged_in = True
                return "230 Login successful"
            raise Exception("530 Login incorrect")

        def close(self):
            self.logged_in = False

    monkeypatch.setattr("ethscan.brute.FTP", _FakeFTP)

    result = _attempt_ftp("localhost", 21, "admin", "secret", 1.0)
    assert result["username"] == "admin"
    assert result["password"] == "secret"
    assert result["success"] is True
    assert result["error"] is None


def test_attempt_ftp_failure(monkeypatch) -> None:
    class _FakeFTP:
        def connect(self, host, port, timeout=None):
            pass

        def login(self, username, password):
            raise Exception("530 Login incorrect")

        def close(self):
            pass

    monkeypatch.setattr("ethscan.brute.FTP", _FakeFTP)

    result = _attempt_ftp("localhost", 21, "admin", "wrong", 1.0)
    assert result["success"] is False
    assert "530 Login incorrect" in result["error"]


def test_attempt_ftp_connect_failure(monkeypatch) -> None:
    class _FakeFTP:
        def connect(self, host, port, timeout=None):
            raise ConnectionRefusedError("connection refused")

        def login(self, username, password):
            pass

        def close(self):
            pass

    monkeypatch.setattr("ethscan.brute.FTP", _FakeFTP)

    result = _attempt_ftp("localhost", 21, "admin", "secret", 1.0)
    assert result["success"] is False
    assert "connection refused" in result["error"]


def test_attempt_ssh_without_paramiko(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.brute.PARAMIKO_AVAILABLE", False)

    result = _attempt_ssh("localhost", 22, "root", "secret", 1.0)
    assert result["success"] is False
    assert "paramiko is required" in result["error"]


def test_attempt_ssh_with_paramiko(monkeypatch) -> None:
    class _FakeSSHClient:
        def __init__(self):
            self.closed = False

        def set_missing_host_key_policy(self, policy):
            pass

        def connect(self, host, port=None, username=None, password=None, **kwargs):
            if password != "secret":
                raise Exception("Authentication failed")

        def close(self):
            self.closed = True

    fake_paramiko = types.ModuleType("paramiko")
    fake_paramiko.SSHClient = _FakeSSHClient
    fake_paramiko.AutoAddPolicy = lambda: None

    monkeypatch.setattr("ethscan.brute.paramiko", fake_paramiko, raising=False)
    monkeypatch.setattr("ethscan.brute.PARAMIKO_AVAILABLE", True)

    result = _attempt_ssh("localhost", 22, "root", "secret", 1.0)
    assert result["success"] is True
    assert result["error"] is None


def test_attempt_ssh_with_paramiko_failure(monkeypatch) -> None:
    class _FakeSSHClient:
        def set_missing_host_key_policy(self, policy):
            pass

        def connect(self, host, port=None, username=None, password=None, **kwargs):
            raise Exception("Authentication failed")

        def close(self):
            pass

    fake_paramiko = types.ModuleType("paramiko")
    fake_paramiko.SSHClient = _FakeSSHClient
    fake_paramiko.AutoAddPolicy = lambda: None

    monkeypatch.setattr("ethscan.brute.paramiko", fake_paramiko, raising=False)
    monkeypatch.setattr("ethscan.brute.PARAMIKO_AVAILABLE", True)

    result = _attempt_ssh("localhost", 22, "root", "wrong", 1.0)
    assert result["success"] is False
    assert "Authentication failed" in result["error"]


def test_run_brute_offline(monkeypatch) -> None:
    def mock_attempt(host, port, username, password, timeout):
        success = username == "admin" and password == "password"
        return {
            "username": username,
            "password": password,
            "success": success,
            "error": None if success else "530 Login incorrect",
        }

    monkeypatch.setattr("ethscan.brute._attempt_ftp", mock_attempt)

    result = run_brute(
        "ftp.example.com",
        protocol="ftp",
        usernames=["admin"],
        passwords=["password", "wrong"],
        timeout=1.0,
    )

    assert result["target"] == "ftp.example.com"
    assert result["host"] == "ftp.example.com"
    assert result["protocol"] == "ftp"
    assert result["port"] == DEFAULT_FTP_PORT
    assert result["usernames_tested"] == 1
    assert result["passwords_tested"] == 2
    assert result["attempts"] == 2
    assert result["successful_count"] == 1
    assert result["successful"][0]["username"] == "admin"
    assert result["successful"][0]["password"] == "password"
    assert len(result["results"]) == 2


def test_run_brute_ssh_default_port(monkeypatch) -> None:
    def mock_attempt(host, port, username, password, timeout):
        return {
            "username": username,
            "password": password,
            "success": False,
            "error": "Authentication failed",
        }

    monkeypatch.setattr("ethscan.brute._attempt_ssh", mock_attempt)

    result = run_brute(
        "ssh.example.com",
        protocol="ssh",
        usernames=["root"],
        passwords=["wrong"],
        timeout=1.0,
    )

    assert result["protocol"] == "ssh"
    assert result["port"] == DEFAULT_SSH_PORT
    assert result["attempts"] == 1
    assert result["successful_count"] == 0


def test_run_brute_custom_port(monkeypatch) -> None:
    def mock_attempt(host, port, username, password, timeout):
        return {
            "username": username,
            "password": password,
            "success": False,
            "error": None,
        }

    monkeypatch.setattr("ethscan.brute._attempt_ftp", mock_attempt)

    result = run_brute(
        "ftp.example.com",
        protocol="ftp",
        usernames=["admin"],
        passwords=["password"],
        port=2121,
        timeout=1.0,
    )

    assert result["port"] == 2121


def test_run_brute_unknown_protocol() -> None:
    with pytest.raises(ValueError):
        run_brute("example.com", protocol="smtp")


def test_run_brute_target_normalization(monkeypatch) -> None:
    def mock_attempt(host, port, username, password, timeout):
        return {
            "username": username,
            "password": password,
            "success": False,
            "error": None,
        }

    monkeypatch.setattr("ethscan.brute._attempt_ftp", mock_attempt)

    result = run_brute(
        "ftp://FTP.Example.com/path",
        protocol="ftp",
        usernames=["admin"],
        passwords=["password"],
        timeout=1.0,
    )

    assert result["host"] == "ftp.example.com"


def test_format_brute_report_json() -> None:
    data = {
        "target": "ftp.example.com",
        "host": "ftp.example.com",
        "protocol": "ftp",
        "port": 21,
        "timeout": 5.0,
        "usernames_tested": 1,
        "passwords_tested": 1,
        "attempts": 1,
        "successful_count": 1,
        "successful": [
            {
                "username": "admin",
                "password": "secret",
                "success": True,
                "error": None,
            }
        ],
        "results": [
            {
                "username": "admin",
                "password": "secret",
                "success": True,
                "error": None,
            }
        ],
    }
    output = format_brute_report_json(data)
    assert "ftp.example.com" in output
    assert "admin" in output
    assert "secret" in output
    assert '"success": true' in output


def test_format_brute_report_json_error() -> None:
    data = {
        "target": "ftp.example.com",
        "host": "ftp.example.com",
        "protocol": "ftp",
        "port": 21,
        "timeout": 5.0,
        "usernames_tested": 1,
        "passwords_tested": 1,
        "attempts": 1,
        "successful_count": 0,
        "successful": [],
        "results": [
            {
                "username": "admin",
                "password": "wrong",
                "success": False,
                "error": "connection refused",
            }
        ],
    }
    output = format_brute_report_json(data)
    assert "connection refused" in output


def test_format_brute_report_markdown() -> None:
    data = {
        "target": "ftp.example.com",
        "host": "ftp.example.com",
        "protocol": "ftp",
        "port": 21,
        "timeout": 5.0,
        "usernames_tested": 1,
        "passwords_tested": 2,
        "attempts": 2,
        "successful_count": 1,
        "successful": [
            {
                "username": "admin",
                "password": "secret",
                "success": True,
                "error": None,
            }
        ],
        "results": [
            {
                "username": "admin",
                "password": "secret",
                "success": True,
                "error": None,
            },
            {
                "username": "admin",
                "password": "wrong",
                "success": False,
                "error": "530 Login incorrect",
            },
        ],
    }
    output = format_brute_report_markdown(data)
    assert "# ethscan Brute Force Report" in output
    assert "ftp.example.com" in output
    assert "**Protocol:** ftp" in output
    assert "**Port:** 21" in output
    assert "**Attempts:** 2" in output
    assert "**Successful Logins:** 1" in output
    assert "## Successful Logins" in output
    assert "| admin | secret |" in output
    assert "## All Attempts" in output
    assert "530 Login incorrect" in output


def test_format_brute_report_markdown_no_success() -> None:
    data = {
        "target": "ftp.example.com",
        "host": "ftp.example.com",
        "protocol": "ftp",
        "port": 21,
        "timeout": 5.0,
        "usernames_tested": 1,
        "passwords_tested": 1,
        "attempts": 1,
        "successful_count": 0,
        "successful": [],
        "results": [
            {
                "username": "admin",
                "password": "wrong",
                "success": False,
                "error": "connection refused",
            }
        ],
    }
    output = format_brute_report_markdown(data)
    assert "*No successful logins.*" in output
    assert "connection refused" in output
