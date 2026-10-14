"""Tests for the ethscan smtp module."""

import csv
import io
import json
import socket
import socketserver
import threading

import pytest

from ethscan.smtp import (
    DEFAULT_EHLO_NAME,
    DEFAULT_PORT,
    DEFAULT_TIMEOUT,
    RELAY_PROBE_DOMAIN,
    _classify_vrfy,
    _normalize_target,
    _parse_smtp_response,
    _read_response,
    _send_command,
    format_smtp_report_csv,
    format_smtp_report_json,
    format_smtp_report_markdown,
    run_smtp,
)


# ---------------------------------------------------------------------------
# Fake SMTP server for deterministic run_smtp tests
# ---------------------------------------------------------------------------


class _FakeSMTPHandler(socketserver.BaseRequestHandler):
    """A tiny stateful fake SMTP server driven by the server instance config."""

    def handle(self) -> None:  # noqa: D401 - socketserver entry point
        s = self.request
        s.settimeout(5.0)
        sockfile = s.makefile("rb")

        cfg = self.server.smtp_config  # type: ignore[attr-defined]

        # Banner (greeting).
        banner = cfg.get("banner", "220 fake.smtp.example ESMTP ethscan")
        s.sendall((banner + "\r\n").encode("utf-8"))

        while True:
            try:
                line = sockfile.readline()
            except socket.timeout:
                break
            if not line:
                break
            raw = line.decode("utf-8", errors="replace").strip()
            if not raw:
                continue
            upper = raw.upper()

            if upper.startswith("EHLO") or upper.startswith("HELO"):
                caps = cfg.get("capabilities", ["STARTTLS", "8BITMIME"])
                greet = cfg.get("greeting", "fake.smtp.example")
                resp_lines = [f"250-{greet}"]
                for cap in caps:
                    resp_lines.append(f"250-{cap}")
                resp_lines.append("250 OK")
                s.sendall(("\r\n".join(resp_lines) + "\r\n").encode("utf-8"))

            elif upper.startswith("STARTTLS"):
                s.sendall(b"220 Ready to start TLS\r\n")

            elif upper.startswith("VRFY"):
                user = raw.split(" ", 1)[1].strip() if " " in raw else ""
                code = cfg.get("vrfy_codes", {}).get(user, 250)
                s.sendall(f"{code} {user} status\r\n".encode("utf-8"))

            elif upper.startswith("MAIL FROM"):
                s.sendall(b"250 2.1.0 sender ok\r\n")

            elif upper.startswith("RCPT TO"):
                if cfg.get("open_relay", False):
                    s.sendall(b"250 2.1.5 recipient ok\r\n")
                else:
                    s.sendall(b"554 5.7.1 relay not permitted\r\n")

            elif upper.startswith("QUIT"):
                s.sendall(b"221 2.0.0 bye\r\n")
                break

            else:
                s.sendall(b"502 5.5.2 command unrecognized\r\n")


class _FakeSMTPServer(socketserver.TCPServer):
    allow_reuse_address = True
    smtp_config: dict = {}


@pytest.fixture()
def fake_smtp():
    """Start a fake SMTP server; yield (host, port, server) and shut it down."""
    server = _FakeSMTPServer(("127.0.0.1", 0), _FakeSMTPHandler)
    server.smtp_config = {}
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
    host, port = _normalize_target("mail.example.com")
    assert host == "mail.example.com"
    assert port == DEFAULT_PORT


def test_normalize_target_host_port() -> None:
    host, port = _normalize_target("mail.example.com:587")
    assert host == "mail.example.com"
    assert port == 587


def test_normalize_target_url_with_port() -> None:
    host, port = _normalize_target("smtp://mail.example.com:465")
    assert host == "mail.example.com"
    assert port == 465


def test_normalize_target_url_default_port() -> None:
    host, port = _normalize_target("smtp://mail.example.com")
    assert host == "mail.example.com"
    assert port == DEFAULT_PORT


def test_normalize_target_empty_raises() -> None:
    with pytest.raises(ValueError):
        _normalize_target("   ")


def test_normalize_target_ipv6_url() -> None:
    host, port = _normalize_target("smtp://[::1]:25")
    assert host == "::1"
    assert port == 25
    host, port = _normalize_target("[::1]:25")
    assert host == "::1"
    assert port == 25
    host, port = _normalize_target("[::1]")
    assert host == "::1"
    assert port == DEFAULT_PORT


# ---------------------------------------------------------------------------
# _parse_smtp_response
# ---------------------------------------------------------------------------


def test_parse_smtp_response_single_line() -> None:
    code, msg, complete = _parse_smtp_response(["220 mail.example ESMTP"])
    assert code == 220
    assert "mail.example" in msg
    assert complete is True


def test_parse_smtp_response_continuation() -> None:
    lines = ["250-fake.example.com", "250-STARTTLS", "250 OK"]
    code, msg, complete = _parse_smtp_response(lines)
    assert code == 250
    assert complete is False  # first line uses '-'


def test_parse_smtp_response_empty() -> None:
    assert _parse_smtp_response([]) == (0, "", False)


# ---------------------------------------------------------------------------
# _classify_vrfy
# ---------------------------------------------------------------------------


def test_classify_vrfy_known_codes() -> None:
    assert _classify_vrfy(250)[0] is None  # server confirms local knowledge ambiguously
    assert _classify_vrfy(550)[0] is False
    assert _classify_vrfy(551)[0] is False
    assert _classify_vrfy(252)[0] is None
    assert "enumeration not allowed" in _classify_vrfy(252)[1]


def test_classify_vrfy_unknown_code() -> None:
    found, desc = _classify_vrfy(421)
    assert found is None
    assert "code" in desc


# ---------------------------------------------------------------------------
# run_smtp – against the local fake SMTP server
# ---------------------------------------------------------------------------


def test_run_smtp_full_interaction(fake_smtp) -> None:
    host, port, _server = fake_smtp
    result = run_smtp(
        f"{host}:{port}",
        timeout=2.0,
        users=["admin", "root"],
        check_starttls=True,
        check_relay=False,
    )
    assert result["connected"] is True
    assert result["host"] == host
    assert result["port"] == port
    assert result["banner"].startswith("220")
    assert result["ehlo_success"] is True
    assert result["starttls_advertised"] is True
    assert "STARTTLS" in result["capabilities"]
    assert "ADMIN" not in result["capabilities"]  # greeting is skipped
    assert len(result["users"]) == 2
    for entry in result["users"]:
        assert entry["code"] == 250
        assert entry["error"] is None
    assert result["open_relay"] is None  # relay check disabled
    assert result["error"] is None


def test_run_smtp_connection_refused() -> None:
    # Use a definitely-closed port on localhost.
    result = run_smtp("127.0.0.1:1", timeout=1.0)
    assert result["connected"] is False
    assert result["banner"] is None
    assert result["error"] is not None
    assert "connection failed" in result["error"]


def test_run_smtp_open_relay_detected(fake_smtp) -> None:
    host, port, server = fake_smtp
    server.smtp_config["open_relay"] = True
    result = run_smtp(f"{host}:{port}", timeout=2.0, users=None, check_relay=True)
    assert result["open_relay"] is True


def test_run_smtp_relay_blocked(fake_smtp) -> None:
    host, port, server = fake_smtp
    server.smtp_config["open_relay"] = False
    result = run_smtp(f"{host}:{port}", timeout=2.0, users=None, check_relay=True)
    assert result["open_relay"] is False


def test_run_smtp_starttls_disabled(fake_smtp) -> None:
    host, port, _server = fake_smtp
    result = run_smtp(f"{host}:{port}", timeout=2.0, check_starttls=False, check_relay=False)
    assert result["ehlo_success"] is False
    assert result["starttls_advertised"] is False
    assert result["capabilities"] == []


def test_run_smtp_vrfy_user_found(fake_smtp) -> None:
    host, port, server = fake_smtp
    server.smtp_config["vrfy_codes"] = {"admin": 550}
    result = run_smtp(f"{host}:{port}", timeout=2.0, users=["admin"], check_relay=False)
    assert len(result["users"]) == 1
    assert result["users"][0]["code"] == 550
    assert result["users"][0]["found"] is False


def test_run_smtp_vrfy_not_permitted(fake_smtp) -> None:
    host, port, server = fake_smtp
    server.smtp_config["vrfy_codes"] = {"root": 252}
    result = run_smtp(f"{host}:{port}", timeout=2.0, users=["root"], check_relay=False)
    entry = result["users"][0]
    assert entry["code"] == 252
    assert entry["found"] is None
    assert "enumeration not allowed" in entry["description"]


def test_run_smtp_no_starttls_advertised(fake_smtp) -> None:
    host, port, server = fake_smtp
    server.smtp_config["capabilities"] = []
    result = run_smtp(f"{host}:{port}", timeout=2.0, users=None, check_relay=True)
    assert result["starttls_advertised"] is False
    assert result["capabilities"] == []


def test_run_smtp_relay_code_path_skipped_without_ehlo(fake_smtp) -> None:
    host, port, _server = fake_smtp
    # disable ehlo so relay check is skipped even though check_relay=True
    result = run_smtp(f"{host}:{port}", timeout=2.0, check_starttls=False, check_relay=True)
    assert result["open_relay"] is None


# ---------------------------------------------------------------------------
# _read_response / _send_command against the fake server
# ---------------------------------------------------------------------------


def test_send_command_vrfy(fake_smtp) -> None:
    host, port, _server = fake_smtp
    sock = socket.create_connection((host, port))
    try:
        # swallow banner
        _read_response(sock, 2.0)
        lines = _send_command(sock, "VRFY alice", 2.0)
        assert lines[0].startswith("250")
    finally:
        sock.close()


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


_SAMPLE = {
    "target": "mail.example.com",
    "host": "mail.example.com",
    "port": 25,
    "connected": True,
    "banner": "220 mail.example.com ESMTP Postfix",
    "ehlo_success": True,
    "starttls_advertised": True,
    "starttls_checked": True,
    "capabilities": ["STARTTLS", "AUTH", "8BITMIME"],
    "users": [
        {"user": "admin", "found": None, "description": "will accept", "code": 252, "error": None},
        {"user": "root", "found": False, "description": "no such user", "code": 550, "error": None},
    ],
    "open_relay": False,
    "error": None,
}


def test_format_smtp_report_json() -> None:
    output = format_smtp_report_json(_SAMPLE)
    parsed = json.loads(output)
    assert parsed["host"] == "mail.example.com"
    assert parsed["starttls_advertised"] is True
    assert parsed["open_relay"] is False
    assert len(parsed["users"]) == 2
    assert parsed["users"][1]["found"] is False


def test_format_smtp_report_markdown() -> None:
    output = format_smtp_report_markdown(_SAMPLE)
    assert "# ethscan SMTP Report" in output
    assert "mail.example.com" in output
    assert "STARTTLS" in output
    assert "VRFY User Enumeration" in output
    assert "admin" in output
    assert "**Open Relay:** not vulnerable" in output


def test_format_smtp_report_markdown_no_users() -> None:
    data = {
        "target": "mail.example.com",
        "host": "mail.example.com",
        "port": 25,
        "connected": True,
        "banner": "220 mail.example.com",
        "ehlo_success": True,
        "starttls_advertised": False,
        "starttls_checked": True,
        "capabilities": [],
        "users": [],
        "open_relay": True,
        "error": None,
    }
    output = format_smtp_report_markdown(data)
    assert "VRFY User Enumeration" not in output
    assert "**Open Relay:** VULNERABLE" in output


def test_format_smtp_report_markdown_connection_failed() -> None:
    data = {
        "target": "dead.example.com",
        "host": "dead.example.com",
        "port": 25,
        "connected": False,
        "banner": None,
        "ehlo_success": False,
        "starttls_advertised": False,
        "starttls_checked": True,
        "capabilities": [],
        "users": [],
        "open_relay": None,
        "error": "connection failed: [Errno 111] Connection refused",
    }
    output = format_smtp_report_markdown(data)
    assert "connected" in output.lower()
    assert "Connection refused" in output


def test_format_smtp_report_csv_with_users() -> None:
    output = format_smtp_report_csv(_SAMPLE)
    reader = list(csv.reader(io.StringIO(output)))
    assert reader[0] == ["target", "host", "port", "user", "found", "code", "description"]
    assert reader[1] == ["mail.example.com", "mail.example.com", "25", "admin", "", "252", "will accept"]
    assert reader[2] == ["mail.example.com", "mail.example.com", "25", "root", "false", "550", "no such user"]


def test_format_smtp_report_csv_no_users_open_relay() -> None:
    data = {
        "target": "mail.example.com",
        "host": "mail.example.com",
        "port": 25,
        "open_relay": True,
        "users": [],
    }
    output = format_smtp_report_csv(data)
    reader = list(csv.reader(io.StringIO(output)))
    assert len(reader) == 2
    assert reader[0][0] == "target"
    assert reader[1][4] == "true"
    assert reader[1][6] == "open relay"


def test_format_smtp_report_csv_no_users_no_relay() -> None:
    data = {
        "target": "mail.example.com",
        "host": "mail.example.com",
        "port": 25,
        "open_relay": False,
        "users": [],
    }
    output = format_smtp_report_csv(data)
    reader = list(csv.reader(io.StringIO(output)))
    assert reader[1][4] == "false"
    assert reader[1][6] == "closed relay"


def test_format_smtp_report_csv_comma_escaping() -> None:
    data = {
        "target": "mail.example.com",
        "host": "mail.example.com",
        "port": 25,
        "users": [
            {"user": "a,b", "found": True, "code": 250, "description": "x, y, z"},
        ],
        "open_relay": None,
    }
    output = format_smtp_report_csv(data)
    reader = list(csv.reader(io.StringIO(output)))
    assert reader[1][3] == "a,b"
    assert reader[1][5] == "250"
    assert reader[1][6] == "x, y, z"
