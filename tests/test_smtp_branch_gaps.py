"""Branch-coverage gap tests for ethscan/smtp.py."""

from __future__ import annotations

import socket

import pytest

import ethscan.smtp as smtp_mod


class _SeqSock:
    """Minimal socket-like object driven by a recv queue and sent log."""

    def __init__(self, recv_chunks: list[bytes]) -> None:
        self._chunks = list(recv_chunks)
        self.sent: list[bytes] = []
        self.closed = False

    def settimeout(self, t: float) -> None:
        return None

    def send(self, data: bytes) -> int:
        self.sent.append(data)
        return len(data)

    def recv(self, n: int) -> bytes:
        if not self._chunks:
            return b""
        return self._chunks.pop(0)

    def close(self) -> None:
        self.closed = True


def test_normalize_target_bracket_without_port_sep_falls_through() -> None:
    host, port = smtp_mod._normalize_target("[::1]")
    assert host == "::1"
    assert port == smtp_mod.DEFAULT_PORT


def test_normalize_target_bracket_colon_non_numeric_port() -> None:
    # bracket_end > 0 but port_part not digits -> 63->74 fallthrough
    host, port = smtp_mod._normalize_target("[::1]:abc")
    assert host == "[::1]:abc"
    assert port == smtp_mod.DEFAULT_PORT


def test_normalize_target_bare_host_colon_non_numeric_port() -> None:
    # base:rest with non-digit rest -> 68->74 fallthrough
    host, port = smtp_mod._normalize_target("mail.example.com:smtp")
    assert host == "mail.example.com:smtp"
    assert port == smtp_mod.DEFAULT_PORT


def test_ehlo_capability_empty_keyword_continues(monkeypatch: pytest.MonkeyPatch) -> None:
    """EHLO line with only whitespace keyword triggers 325/330->318 continue."""
    # recv queue: banner, EHLO multi-line (has blank-keyword line), QUIT
    recv = [
        b"220 mail.example.com ESMTP\r\n",
        b"250-mail.example.com\r\n250-   \r\n250-STARTTLS\r\n250 OK\r\n",
        b"221 Bye\r\n",
    ]
    sock = _SeqSock(recv)

    result = smtp_mod.run_smtp(
        "mail.example.com",
        timeout=1.0,
        connector=lambda h, p, timeout=None: sock,
        check_starttls=True,
        check_relay=False,
    )

    assert result["connected"] is True
    assert result["ehlo_success"] is True
    assert result["capabilities"] == ["STARTTLS"]
    assert result["starttls_advertised"] is True


def test_read_response_skips_empty_text_line(monkeypatch: pytest.MonkeyPatch) -> None:
    """A CRLF-only line decodes to empty text and is skipped (142->139)."""
    # banner: empty line followed by real 220 line in same/next chunk? easier
    # to call _read_response directly with a raw socket yielding \r\n then banner.
    s1, s2 = socket.socketpair()
    try:
        s2.sendall(b"\r\n220 ready\r\n")
        s2.close()
        lines = smtp_mod._read_response(s1, timeout=1.0)
    finally:
        s1.close()
    assert lines == ["220 ready"]


def test_relay_oserror_sets_error_when_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Relay OSError records error when none set (380 branch taken)."""
    recv = [
        b"220 mail.example.com ESMTP\r\n",
        b"250-mail.example.com\r\n250 OK\r\n",
    ]
    sock = _SeqSock(recv)

    orig_send = smtp_mod._send_command

    def fake_send(s, command: str, timeout: float):
        if command.startswith("MAIL FROM"):
            raise OSError("relay down")
        return orig_send(s, command, timeout)

    monkeypatch.setattr(smtp_mod, "_send_command", fake_send)
    result = smtp_mod.run_smtp(
        "mail.example.com",
        timeout=1.0,
        connector=lambda h, p, timeout=None: sock,
        check_starttls=True,
        check_relay=True,
    )
    assert result["open_relay"] is None
    assert result["error"] == "relay check failed: relay down"


def test_relay_generic_exception_sets_error_when_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Relay generic Exception records error when none set (384 branch taken)."""
    recv = [
        b"220 mail.example.com ESMTP\r\n",
        b"250-mail.example.com\r\n250 OK\r\n",
    ]
    sock = _SeqSock(recv)

    orig_send = smtp_mod._send_command

    def fake_send(s, command: str, timeout: float):
        if command.startswith("MAIL FROM"):
            raise RuntimeError("boom")
        return orig_send(s, command, timeout)

    monkeypatch.setattr(smtp_mod, "_send_command", fake_send)
    result = smtp_mod.run_smtp(
        "mail.example.com",
        timeout=1.0,
        connector=lambda h, p, timeout=None: sock,
        check_starttls=True,
        check_relay=True,
    )
    assert result["open_relay"] is None
    assert result["error"] == "relay check failed: boom"



def test_normalize_target_bracket_close_at_start() -> None:
    """bracket_end == 0 makes 61 false and falls through to 74."""
    host, port = smtp_mod._normalize_target("]:25")
    assert host == "]:25"
    assert port == smtp_mod.DEFAULT_PORT

def test_run_smtp_outer_exception_closes_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    """Outer exception after connect exercises outer handler/finally (392-396)."""
    recv = [b"220 mail.example.com ESMTP\r\n"]
    sock = _SeqSock(recv)

    orig_send = smtp_mod._send_command

    def fake_send(s, command: str, timeout: float):
        if command.startswith("EHLO"):
            # BaseException escapes inner `except Exception` handlers
            raise KeyboardInterrupt("boom")
        return orig_send(s, command, timeout)

    monkeypatch.setattr(smtp_mod, "_send_command", fake_send)
    with pytest.raises(KeyboardInterrupt):
        smtp_mod.run_smtp(
            "mail.example.com",
            timeout=1.0,
            connector=lambda h, p, timeout=None: sock,
            check_starttls=True,
        )
    assert sock.closed is True


def test_format_smtp_csv_error_without_findings_no_findings_block() -> None:
    """CSV error row with no findings exercises 504->509 false branch."""
    data = {
        "target": "mail.example.com",
        "host": "mail.example.com",
        "port": 25,
        "error": "boom",
        "findings": [],
    }
    out = smtp_mod.format_smtp_report_csv(data)
    assert "boom" in out
    assert "finding" not in out.splitlines()[-1] if out.splitlines() else True
    # no findings section emitted
    assert "\nfinding\n" not in "\n" + out + "\n"
