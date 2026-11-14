"""Permanent sweep test: a hostile SMB answer is reported, never raised.

Covers both public entry points that take a hostile transport answer:
``run_smb`` (SMB1 negotiate) and ``run_smb2`` (SMB2/SMB3 negotiate). Every
body a hostile server can send yields a result dict with an ``error`` key
and never raises; a connector that blows up is reported the same way.
"""
from __future__ import annotations

import csv
import io
import pytest
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
            if isinstance(flags, (list, tuple)):
                # A list/tuple is accepted; elements are stringified before join.
                expected = "|".join(str(x) for x in flags)
                assert rows[1][8] == expected
                # A well-formed string list is rendered verbatim in markdown too.
                if all(isinstance(x, str) for x in flags) and accessible:
                    assert ", ".join(flags) in md_out
            else:
                # A non-iterable scalar is normalized to an empty flag list.
                assert rows[1][8] == ""
                if accessible:
                    assert "**Security Flags:** none" in md_out


def test_security_flags_string_is_rendered() -> None:
    payload = {"accessible": True, "security_flags": ["user_security", "signing_enabled"]}
    csv_out = format_smb_report_csv(payload)
    md_out = format_smb_report_markdown(payload)
    assert "user_security|signing_enabled" in csv_out
    assert "user_security, signing_enabled" in md_out


# ---------------------------------------------------------------------------
# Hostile ``smb2`` shapes in the report formatters
# ---------------------------------------------------------------------------
# A hostile SMB answer (or a hand-crafted result dict) can carry an
# ``smb2`` value that is ``None``, a scalar, a list, or a dict with
# non-dict nested elements. The Markdown formatter must never raise;
# hostile shapes render without crashing.
SMB2_HOSTILE: tuple[object, ...] = (
    None,
    123,
    True,
    1.5,
    "string",
    [],
    [1, 2],
    {"a": 1},
    [None, {}],
    {"accessible": True, "dialect": "SMB 3.1.1", "capability_flags": ["encryption", 123], "negotiate_contexts": [{"type": 1}, "not a dict"], "notes": ["note1", 456]},
)


def test_smb2_hostile_shapes_do_not_raise() -> None:
    for smb2 in SMB2_HOSTILE:
        payload = {"accessible": True, "smb2": smb2}
        md_out = format_smb_report_markdown(payload)
        csv_out = format_smb_report_csv(payload)
        assert isinstance(md_out, str)
        assert isinstance(csv_out, str)


def test_smb2_scalar_capabilities_and_notes_do_not_raise() -> None:
    """Non-list ``capability_flags``/``notes`` normalize to empty lists."""
    smb2 = {
        "accessible": True,
        "dialect": "SMB 3.1.1",
        "capability_flags": "not-a-list",
        "notes": "not-a-list",
    }
    payload = {"accessible": True, "smb2": smb2}
    md_out = format_smb_report_markdown(payload)
    csv_out = format_smb_report_csv(payload)
    assert "- **Capabilities:** none" in md_out
    assert "- **Note:**" not in md_out
    assert isinstance(csv_out, str)


# ---------------------------------------------------------------------------
# Hostile ``raw_preview`` shapes in the report formatters
# ---------------------------------------------------------------------------
# A hostile SMB answer (or a hand-crafted result dict) can carry a
# ``raw_preview`` value that is ``None``, a scalar, bytes, or a non-string
# iterable. Both the Markdown and CSV formatters must never raise; hostile
# shapes render as a stringified preview.
RAW_PREVIEW_HOSTILE: tuple[object, ...] = (
    None,
    123,
    True,
    1.5,
    [],
    {},
    b"bytes",
    "valid string",
)


@pytest.mark.parametrize("raw", RAW_PREVIEW_HOSTILE)
def test_format_smb_report_markdown_hostile_raw_preview(raw: object) -> None:
    results = {"accessible": True, "raw_preview": raw}
    report = format_smb_report_markdown(results)
    assert isinstance(report, str)
    assert "# ethscan SMB Reconnaissance Report" in report


@pytest.mark.parametrize("raw", RAW_PREVIEW_HOSTILE)
def test_format_smb_report_csv_hostile_raw_preview(raw: object) -> None:
    results = {"accessible": True, "raw_preview": raw}
    report = format_smb_report_csv(results)
    assert isinstance(report, str)
    reader = list(csv.reader(io.StringIO(report)))
    assert reader[0][0] == "target"
    assert len(reader) == 2  # header + one data row
