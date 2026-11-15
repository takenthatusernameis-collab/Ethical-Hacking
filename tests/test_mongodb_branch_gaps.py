"""Focused branch-coverage tests for ethscan.mongodb.

Closes reachable partial branches identified in branch-coverage analysis of
ethscan/mongodb.py over tests/test_mongodb.py,
tests/test_mongodb_hostile_sweep.py and tests/test_mongodb_formatter_hostile_sweep.py.

Covered in this file (reachable):
- 59->70: _normalize_target("[::1") bracketed host with no closing bracket
- 66->70: _normalize_target("host:abc") unbracketed host with non-digit port
- 95->97: _send_recv with empty request skips sendall
- 196->207: _parse_buildinfo_response version field present but truncated
  (str_start + 4 > len(doc_data)) skips string parsing
- 212->207: _parse_buildinfo_response field present but truncated skips parsing
"""
from __future__ import annotations

from unittest.mock import patch

from ethscan.mongodb import (
    DEFAULT_PORT,
    _normalize_target,
    _parse_buildinfo_response,
    _send_recv,
)


# --- _normalize_target reachable branch gaps (59->70, 66->70) ---


def test_normalize_target_bracket_without_close() -> None:
    # 59->70: "[::1" starts with "[" but has no closing "]", so
    # close == -1 and the bracket-port branch is skipped; the host is
    # returned verbatim.
    host, port = _normalize_target("[::1")
    assert host == "[::1"
    assert port == DEFAULT_PORT


def test_normalize_target_unbracketed_nondigit_port() -> None:
    # 66->70: "host:abc" takes the unbracketed host:port branch but
    # the suffix "abc" is not digits, so the port-assignment arc is not
    # taken and the host is returned verbatim.
    host, port = _normalize_target("host:abc")
    assert host == "host:abc"
    assert port == DEFAULT_PORT


# --- _send_recv reachable branch gap (95->97) ---


def test_send_recv_empty_request_skips_sendall() -> None:
    # 95->97: an empty request skips sock.sendall and goes straight to recv.

    class FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def sendall(self, data):  # pragma: no cover - must NOT be called
            raise AssertionError("sendall should not be called for empty request")

        def recv(self, n):
            return b"pong"

    with patch("ethscan.mongodb.socket.create_connection") as mock_create:
        mock_create.return_value = FakeConn()
        data, err = _send_recv("localhost", 27017, b"", 1.0)
    assert data == b"pong"
    assert err is None


# --- _parse_buildinfo_response reachable branch gaps (196->207, 212->207) ---


def _build_version_payload(version_bytes_tail: bytes) -> bytes:
    """Build an OP_REPLY payload with a version field whose length prefix
    straddles the end of the document so str_start + 4 > len(doc_data)."""
    # \x02version\x00 then a 4-byte length prefix that we control.
    doc = b"\x02version\x00" + version_bytes_tail
    header = b"\x00" * 16 + (1).to_bytes(4, byteorder="little")  # numberReturned = 1
    return header + doc


def test_parse_buildinfo_response_version_truncated_length() -> None:
    # 196->207: the version field is present but the 4-byte length prefix
    # straddles the end of the document (str_start + 4 > len(doc_data)),
    # so the dedicated version block is skipped and parsing jumps to the
    # generic field loop.
    payload = _build_version_payload(b"\x01\x02")  # only 2 bytes after tag
    result = _parse_buildinfo_response(payload)
    assert result == {}


def test_parse_buildinfo_response_field_truncated_length() -> None:
    # 212->207: a generic field (sysInfo) is present but its 4-byte length
    # prefix straddles the end of the document, so that field's parse is
    # skipped and the loop continues.
    doc = b"\x02version\x00\x05\x00\x00\x00hello\x00" + b"\x02sysInfo\x00\x01\x02\x03"
    header = b"\x00" * 16 + (1).to_bytes(4, byteorder="little")  # numberReturned = 1
    result = _parse_buildinfo_response(header + doc)
    assert result.get("version") == "hello"
    assert "sysInfo" not in result