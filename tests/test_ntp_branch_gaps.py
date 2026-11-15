"""Focused branch-coverage tests for ethscan.ntp.

Closes reachable partial branches and missing statements identified in
branch-coverage analysis of ethscan/ntp.py.

Covered in this file (reachable):
- 63->74: bracketed host with non-digit port suffix (e.g. "[::1]:abc")
- 68->74: unbracketed host with non-digit port suffix (e.g. "host:abc")
- 424: _normalize_peers with non-list/tuple input
- 436: format_ntp_report_markdown with non-dict input
- 473->499: monlist error present without extra/more note
- 540: format_ntp_report_csv with non-dict input

Unreachable / defensive arcs (evidence, not testable by input):
- 61->74: reached only when host starts with "[" and contains "]:" but
  bracket_end <= 0. find("]:") returns -1 if absent (excluded by the
  "]:\" in host guard) or >=1 when present (a string starting with "["
  cannot have "]" at index 0). Therefore bracket_end > 0 is always true
  inside that branch.
- 245->243: _parse_monlist_response slices peer_data as
  data[12:12+count*8] after len(data) >= 12+count*8, so peer_data is
  exactly count*8 bytes and range(0, len, 8) always yields 8-byte
  chunks; the len(chunk)!=8 guard never triggers.
- 393->400: _build_monlist_request() always returns a constant 12-byte
  packet, so req_len is always > 0.
"""
from __future__ import annotations

from ethscan.ntp import (
    _normalize_peers,
    _normalize_target,
    format_ntp_report_csv,
    format_ntp_report_markdown,
)


# --- _normalize_target reachable branch gaps (63->74, 68->74) ---


def test_normalize_target_bracketed_host_nondigit_port() -> None:
    # "[::1]:abc" has bracket_end > 0 but port_part "abc" is not all
    # digits, so the port-assignment arc 63->74 is taken.
    host, port = _normalize_target("[::1]:abc")
    assert host == "[::1]:abc"
    assert port == 123


def test_normalize_target_unbracketed_host_nondigit_port() -> None:
    # "host:abc" takes the unbracketed host:port branch but rest "abc"
    # is not digits, so 68->74.
    host, port = _normalize_target("host:abc")
    assert host == "host:abc"
    assert port == 123


# --- Formatter / normalizer hostile-input gaps (424, 436, 473->499, 540) ---


def test_normalize_peers_non_list_returns_empty() -> None:
    assert _normalize_peers(None) == []
    assert _normalize_peers("bad") == []
    assert _normalize_peers({"a": 1}) == []
    assert _normalize_peers(42) == []


def test_format_ntp_report_markdown_non_dict_input() -> None:
    # 436: non-dict data coerced to empty dict
    out = format_ntp_report_markdown(None)  # type: ignore[arg-type]
    assert "# ethscan NTP Report" in out


def test_format_ntp_report_markdown_monlist_error_without_extra() -> None:
    # 473->499: monlist error present but extra/more condition is false.
    data = {
        "target": "t",
        "host": "h",
        "port": 123,
        "time_response": None,
        "monlist_response": {"error": "monlist request failed"},
        "is_reflector": False,
        "amplification_factor": None,
        "findings": [],
        "error": None,
    }
    out = format_ntp_report_markdown(data)
    assert "**Error:** monlist request failed" in out
    assert "**Note:**" not in out


def test_format_ntp_report_csv_non_dict_input() -> None:
    # 540: non-dict data coerced to empty dict
    out = format_ntp_report_csv(None)  # type: ignore[arg-type]
    assert "record_type" in out.splitlines()[0]
