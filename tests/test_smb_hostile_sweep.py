"""Permanent sweep test: a hostile SMB answer is reported, never raised.

Covers both public entry points that take a hostile transport answer:
``run_smb`` (SMB1 negotiate) and ``run_smb2`` (SMB2/SMB3 negotiate). Every
body a hostile server can send yields a result dict with an ``error`` key
and never raises; a connector that blows up is reported the same way.
"""
from __future__ import annotations

import io
from typing import Callable

from ethscan import smb
from ethscan.smb import format_smb_report_csv, format_smb_report_markdown

TARGET = "127.0.0.1"

#: Bodies a hostile SMB server can send: empty, non-SMB text, truncated
#: headers, an SMB1 frame with nothing after the magic, an SMB2 frame with
#: nothing after the magic, and the full byte range.
HOSTILE_BODIES: tuple[bytes, ...] = (
    b"",
    b"not smb at all",
    b"\x00" * 9,
    b"\xffSMB\x72",
    b"\xfeSMB",
    bytes(range(256)),
    b"\x00\xff\xfe\xfd",
)


def _connector_for(body: bytes) -> Callable[..., tuple[bytes | None, str | None]]:
    def connector(host: str, port: int, request: bytes, timeout: float):
        return body, None

    return connector


def test_hostile_answer_is_reported_not_raised() -> None:
    for body in HOSTILE_BODIES:
        for runner in (smb.run_smb, smb.run_smb2):
            results = runner(TARGET, connector=_connector_for(body))
            assert isinstance(results, dict)
            assert "error" in results


def test_transport_failure_is_reported_not_raised() -> None:
    def connector(host: str, port: int, request: bytes, timeout: float):
        raise OSError("connection refused")

    for runner in (smb.run_smb, smb.run_smb2):
        results = runner(TARGET, connector=connector)
        assert isinstance(results, dict)
        assert results.get("error")


# ---------------------------------------------------------------------------
# Hostile ``security_flags`` shapes in the report formatters
# ---------------------------------------------------------------------------
# A hostile SMB answer (or a hand-crafted result dict) can carry a
# ``security_flags`` value that is ``None``, a scalar, or a list with
# non-string elements. Both the Markdown and CSV formatters join that
# field and would otherwise raise ``TypeError``. They must never raise;
# hostile shapes render as an empty flag list.

SECURITY_FLAG_HOSTILE: tuple[object, ...] = (
    None,
    1,
    0,
    True,
    3.14,
    "user_security",
    [None, 1, 2.5],
    ["user_security", None, "signing_enabled"],
)


def test_security_flags_hostile_shapes_do_not_raise() -> None:
    for flags in SECURITY_FLAG_HOSTILE:
        for accessible in (True, False):
            payload = {"accessible": accessible, "security_flags": flags}
            csv_out = format_smb_report_csv(payload)
            md_out = format_smb_report_markdown(payload)
            assert isinstance(csv_out, str)
            assert isinstance(md_out, str)
            rows = list(csv.reader(io.StringIO(csv_out)))
            # security_flags is column index 8 in the header row.
            assert rows[1][8] == ""
            # A well-formed string list is still rendered verbatim.
            if isinstance(flags, list) and all(isinstance(x, str) for x in flags):
                assert "|".join(flags) in csv_out
                assert ", ".join(flags) in md_out
            elif accessible:
                assert "**Security Flags:** none" in md_out


def test_security_flags_string_is_rendered() -> None:
    payload = {"accessible": True, "security_flags": ["user_security", "signing_enabled"]}
    csv_out = format_smb_report_csv(payload)
    md_out = format_smb_report_markdown(payload)
    assert "user_security|signing_enabled" in csv_out
    assert "user_security, signing_enabled" in md_out
