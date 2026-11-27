"""Focused branch-coverage tests for ethscan.mongodb.

Closes reachable partial branches identified in branch-coverage analysis of
ethscan/mongodb.py over tests/test_mongodb.py,
tests/test_mongodb_hostile_sweep.py and tests/test_mongodb_formatter_hostile_sweep.py.

Covered in this file (reachable):
- 59->70: _normalize_target("[::1") bracketed host with no closing bracket
- 66->70: _normalize_target("host:abc") unbracketed host with non-digit port
- 95->97: _send_recv with empty request skips sendall
- 177->178: _parse_buildinfo_response number_returned == 0 returns early
- 190->197: _parse_buildinfo_response version field present but truncated
  (str_start + 4 > len(doc_data)) skips string parsing
- 192->197: _parse_buildinfo_response version field present, length OK but
  string content truncated (str_start + 4 + str_len > len(doc_data))
- 204->214: _parse_buildinfo_response generic field loop version field
  truncated length prefix
- 208->214: _parse_buildinfo_response generic field loop version field
  truncated string content
- 313->315: run_mongodb buildinfo_data.get('version') true branch
- 313->316: run_mongodb buildinfo_data.get('version') false branch
- 310->316: run_mongodb resp falsy branch
- 305->320: run_mongodb exception branch
"""
from __future__ import annotations

import struct
from unittest.mock import patch

from ethscan.mongodb import (
    DEFAULT_PORT,
    _normalize_target,
    _parse_buildinfo_response,
    _send_recv,
    run_mongodb,
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


# --- _parse_buildinfo_response reachable branch gaps ---


def _build_op_reply(doc: bytes, number_returned: int = 1) -> bytes:
    """Build a proper OP_REPLY message with 36-byte header + document."""
    msg_header = struct.pack("<iiii", 36 + len(doc), 7, 3, 1)
    return (
        msg_header
        + struct.pack("<I", 0)  # responseFlags
        + struct.pack("<q", 0)  # cursorID
        + struct.pack("<I", 0)  # startingFrom
        + struct.pack("<I", number_returned)  # numberReturned
        + doc
    )


def test_parse_buildinfo_response_number_returned_zero() -> None:
    # 177->178: number_returned == 0 returns empty dict early
    doc = b"\x02version\x00\x06\x00\x00\x00hello\x00"
    payload = _build_op_reply(doc, number_returned=0)
    result = _parse_buildinfo_response(payload)
    assert result == {}


def test_parse_buildinfo_response_version_truncated_length_prefix() -> None:
    # 190->197: version field present but length prefix truncated
    # (str_start + 4 > len(doc_data)) skips dedicated version block
    doc = b"\x02version\x00" + b"\x01\x02"  # only 2 bytes after tag, need 4 for length
    payload = _build_op_reply(doc)
    result = _parse_buildinfo_response(payload)
    assert result == {}


def test_parse_buildinfo_response_version_truncated_string_content() -> None:
    # 192->197: version field present, length OK but string content truncated
    # (str_start + 4 + str_len > len(doc_data)) skips version assignment
    # Length says 100 (including null) but only "short" (5 chars + null = 6) provided
    doc = b"\x02version\x00" + (100).to_bytes(4, "little") + b"short\x00"
    payload = _build_op_reply(doc)
    result = _parse_buildinfo_response(payload)
    assert result == {}


def test_parse_buildinfo_response_generic_field_truncated_length_prefix() -> None:
    # 204->214: generic field loop - field present but length prefix truncated
    # version="hello" (len 6), sysInfo has only 2 bytes for length
    doc = b"\x02version\x00\x06\x00\x00\x00hello\x00" + b"\x02sysInfo\x00\x01\x02"
    payload = _build_op_reply(doc)
    result = _parse_buildinfo_response(payload)
    assert result.get("version") == "hello"
    assert "sysInfo" not in result


def test_parse_buildinfo_response_generic_field_truncated_string_content() -> None:
    # 208->214: generic field loop - field present, length OK but content truncated
    # version="hello" (len 6), sysInfo length=100 but only 4 bytes provided
    doc = (
        b"\x02version\x00\x06\x00\x00\x00hello\x00"
        + b"\x02sysInfo\x00"
        + (100).to_bytes(4, "little")
        + b"short"
    )
    payload = _build_op_reply(doc)
    result = _parse_buildinfo_response(payload)
    assert result.get("version") == "hello"
    assert "sysInfo" not in result


# --- run_mongodb reachable branch gaps ---


def test_run_mongodb_version_true_branch() -> None:
    # 313->315: buildinfo_data.get('version') is truthy
    def connector(host, port, request, timeout):
        doc = b"\x02version\x00\x06\x00\x00\x005.0.0\x00"
        return _build_op_reply(doc), None

    result = run_mongodb("localhost", connector=connector)
    assert result["accessible"] is True
    assert result["version"] == "5.0.0"


def test_run_mongodb_version_false_branch() -> None:
    # 313->316: buildinfo_data.get('version') is falsy (empty dict)
    def connector(host, port, request, timeout):
        # Valid response but no version field
        doc = b"\x02sysInfo\x00\x0c\x00\x00\x00Linux x86_64\x00"
        return _build_op_reply(doc), None

    result = run_mongodb("localhost", connector=connector)
    assert result["accessible"] is True
    assert result["version"] is None


def test_run_mongodb_resp_falsy_branch() -> None:
    # 310->316: resp is falsy (empty bytes)
    def connector(host, port, request, timeout):
        return b"", None

    result = run_mongodb("localhost", connector=connector)
    assert result["accessible"] is False
    assert result["error"] == "No response from server"


def test_run_mongodb_exception_branch() -> None:
    # 305->320: exception during _send_recv
    def connector(host, port, request, timeout):
        raise ConnectionError("network down")

    result = run_mongodb("localhost", connector=connector)
    assert result["accessible"] is False
    assert "network down" in result["error"]