"""Focused branch-coverage tests for ethscan.postgresql.

Closes reachable partial branches identified in branch-coverage analysis of
ethscan/postgresql.py.

Covered in this file (reachable):
- 138->140: an empty request skips ``sendall`` and still reads a reply.
- 241->253: a BackendKeyData ('K') message whose body is shorter than four
  bytes is ignored without raising.
"""
from __future__ import annotations

from ethscan.postgresql import _parse_startup_response, _send_recv


class _FakeSocket:
    def __init__(self) -> None:
        self.sent: list[bytes] = []

    def __enter__(self) -> "_FakeSocket":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def sendall(self, data: bytes) -> None:
        self.sent.append(data)

    def recv(self, _n: int) -> bytes:
        return b""


def _pg_msg(msg_type: bytes, body: bytes = b"") -> bytes:
    """Build a length-prefixed PostgreSQL backend message (big-endian)."""
    length = 4 + len(body)
    return msg_type + length.to_bytes(4, "big") + body


def test_send_recv_empty_request_skips_send(monkeypatch) -> None:
    # 138->140: a falsy request must not be sent, but the reply is still read.
    fake = _FakeSocket()
    monkeypatch.setattr(
        "ethscan.postgresql.socket.create_connection",
        lambda *args, **kwargs: fake,
    )
    data, err = _send_recv("127.0.0.1", 5432, b"", 1.0)
    assert data is None
    assert err is None
    assert fake.sent == []


def test_parse_startup_response_backend_key_data_short_body() -> None:
    # 241->253: a 'K' message with a two-byte body is shorter than the four
    # bytes needed for a process id, so it is ignored.
    result = _parse_startup_response(_pg_msg(b"K", b"\x00\x00"))
    assert result["process_id"] is None