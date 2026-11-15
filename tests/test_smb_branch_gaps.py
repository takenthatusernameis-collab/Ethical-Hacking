"""Branch-coverage gap tests for ethscan/smb.py.

Each test drives one previously-uncovered branch arc of the SMB1/SMB2
negotiate parser, banner builder, and Markdown formatter through the public
or module-level API. No production code is exercised differently than in
normal operation; these are additional hostile/boundary inputs.
"""

from __future__ import annotations

import struct
from typing import Any

from ethscan.smb import (
    SMB1_MAGIC,
    SMB2_DIALECT_311,
    SMB2_MAGIC,
    SMB2_SIGNING_ENABLED,
    SMB_COM_NEGOTIATE,
    _build_banner,
    _parse_smb_response,
    format_smb_report_markdown,
    run_smb2,
)


def _build_smb1_response(
    dialect_index: int = 0,
    security_mode: int = 0x01,
    data: bytes = b"",
) -> bytes:
    """Build a raw SMB1 SMB_COM_NEGOTIATE response message."""
    header = SMB1_MAGIC + bytes([SMB_COM_NEGOTIATE]) + b"\x00" * 27  # 32 bytes
    params = struct.pack("<H", dialect_index) + bytes([security_mode]) + b"\x00" * 31
    return header + bytes([0x11]) + params + struct.pack("<H", len(data)) + data


def _build_smb2_header(command: int = 0) -> bytes:
    """Build a 64-byte SMB2 header (all control fields zeroed)."""
    header = bytearray()
    header += SMB2_MAGIC
    header += struct.pack("<H", 64)      # StructureSize
    header += struct.pack("<H", 0)       # CreditCharge
    header += b"\x00" * 4                # Status
    header += struct.pack("<H", command)  # Command (0 = SMB2_NEGOTIATE)
    header += struct.pack("<H", 0)       # CreditRequest
    header += struct.pack("<I", 0)       # Flags
    header += struct.pack("<I", 0)       # NextCommand
    header += struct.pack("<Q", 0)       # MessageId
    header += b"\x00" * 4                # ProcessId
    header += b"\x00" * 4                # TreeId
    header += b"\x00" * 8                # SessionId
    header += b"\x00" * 16               # Signature
    assert len(header) == 64
    return bytes(header)


def _build_smb2_negotiate_response(
    dialect_revision: int = SMB2_DIALECT_311,
    security_mode: int = SMB2_SIGNING_ENABLED,
    capabilities: int = 0,
    server_guid: bytes = b"\x11" * 16,
    negotiate_context_count: int = 0,
    negotiate_context_offset: int = 0,
) -> bytes:
    """Build a well-formed SMB2 NEGOTIATE response (MS-SMB2 2.2.5)."""
    body = bytearray()
    body += struct.pack("<H", 65)                        # StructureSize
    body += struct.pack("<H", security_mode)             # SecurityMode
    body += struct.pack("<H", dialect_revision)          # DialectRevision
    body += struct.pack("<H", negotiate_context_count)   # NegotiateContextCount
    body += server_guid                                  # ServerGUID (16)
    body += struct.pack("<I", capabilities)              # Capabilities
    body += struct.pack("<I", 1048576)                   # MaxTransactSize
    body += struct.pack("<I", 1048576)                   # MaxReadSize
    body += struct.pack("<I", 1048576)                   # MaxWriteSize
    body += b"\x00" * 8                                  # SystemTime
    body += b"\x00" * 8                                  # ServerStartTime
    body += b"\x00" * 4                                  # Buffer
    body += struct.pack("<I", negotiate_context_offset)  # NegotiateContextOffset
    assert len(body) == 64
    return _build_smb2_header() + bytes(body)


def test_parse_smb1_share_level_security_no_user_bit() -> None:
    """security_mode without SMB1_SECURITY_USER exercises the 340->343 arc."""
    parsed = _parse_smb_response(_build_smb1_response(0, 0x02, b"\x00" * 8))
    assert parsed["user_security"] is False
    assert parsed["challenge_response"] is True
    assert parsed["error"] is None


def test_parse_smb1_short_challenge_blob_skips_challenge() -> None:
    """A data blob shorter than 8 bytes exercises the 360->363 arc."""
    parsed = _parse_smb_response(_build_smb1_response(0, 0x01, b"\x00" * 4))
    assert parsed["challenge"] is None
    assert parsed["error"] is None


def test_build_banner_without_challenge_omits_marker() -> None:
    """A parsed response with no challenge exercises the 416->418 arc."""
    parsed: dict[str, Any] = {
        "protocol": "SMB1",
        "dialect": "NT LM 0.12",
        "security_mode": 0x01,
        "signing_required": False,
        "signing_enabled": False,
        "challenge_response": False,
        "challenge": None,
    }
    banner = _build_banner(parsed)
    assert banner is not None
    assert "challenge present" not in banner


def test_run_smb2_signing_disabled_skips_note() -> None:
    """Both signing bits clear exercises the 754->761 false arc in run_smb2."""

    def connector(host: str, port: int, request: bytes, timeout: float):
        return _build_smb2_negotiate_response(security_mode=0), None

    results = run_smb2("192.168.1.100", connector=connector)
    assert results["accessible"] is True
    assert results["signing_enabled"] is False
    assert results["signing_required"] is False
    assert not any("signing" in note for note in results["notes"])


def test_format_markdown_non_dict_negotiate_context_skips() -> None:
    """A non-dict entry in a counted context list exercises the 902->901 arc."""
    results: dict[str, Any] = {
        "target": "192.168.1.100",
        "host": "192.168.1.100",
        "port": 445,
        "accessible": False,
        "smb2": {
            "accessible": True,
            "dialect": "SMB 3.1.1",
            "dialect_revision": SMB2_DIALECT_311,
            "security_mode": 0,
            "signing_required": False,
            "signing_enabled": False,
            "server_guid": None,
            "capability_flags": [],
            "negotiate_context_count": 1,
            "negotiate_contexts": ["not-a-dict"],
            "banner": None,
            "notes": [],
        },
    }
    output = format_smb_report_markdown(results)
    assert "- **Negotiate Contexts:** 1" in output