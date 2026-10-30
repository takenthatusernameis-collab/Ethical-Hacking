from __future__ import annotations

import struct
from unittest.mock import MagicMock

from ethscan import ssh


def test_read_packet_generic_exception() -> None:
    sock = MagicMock()
    def raise_exc(*args, **kwargs):
        raise RuntimeError("boom")
    sock.recv.side_effect = raise_exc
    assert ssh._read_packet(sock) is None


def test_read_packet_payload_empty_len_nonzero() -> None:
    # length says 0? but we read length bytes; if length is 0, payload becomes empty after reading
    sock = MagicMock()
    # Send length 0
    sock.recv.side_effect = [struct.pack(">I", 0)]
    # After reading length 0, we need to read 0 bytes for payload? length is 0, so the while loop won't run
    # But in code: we read payload until len(payload) < length; if length is 0, loop doesn't run, payload is empty
    # Then we check if len(payload)>0? no, so we skip returning payload[1:] and fall through to return None
    result = ssh._read_packet(sock)
    assert result is None
