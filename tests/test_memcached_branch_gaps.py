"""Focused branch-coverage tests for ethscan.memcached.

Closes reachable partial branches identified in branch-coverage analysis of
ethscan/memcached.py.

Covered in this file (reachable):
- 53->64: bracketed host with no closing "]" (e.g. "[incomplete")
- 60->64: unbracketed host:port with non-digit rest (e.g. "host:abc")
- 144->133: STAT line (space) with no value parts (e.g. "STAT \r\n")
- 151->133: STAT line (tab) with no value parts (e.g. "STAT\t\r\n")
- 357->365: primary stats present but empty (no key in primary_keys),
  while other (non-primary) stats are present.
"""
from ethscan.memcached import (
    _normalize_target,
    _parse_stats_response,
    format_memcached_report_markdown,
)


# --- _normalize_target reachable branch gaps (53->64, 60->64) ---


def test_normalize_target_bracketed_host_no_close() -> None:
    # "[incomplete" starts with "[" but has no "]" so close <= 0; the
    # inner block is skipped and the arc 53->64 is taken.
    host, port = _normalize_target("[incomplete")
    assert host == "[incomplete"
    assert port == 11211


def test_normalize_target_unbracketed_host_nondigit_port() -> None:
    # "host:abc" takes the unbracketed host:port branch but rest "abc" is
    # not digits, so the arc 60->64 is taken.
    host, port = _normalize_target("host:abc")
    assert host == "host:abc"
    assert port == 11211


# --- _parse_stats_response reachable branch gaps (144->133, 151->133) ---


def test_parse_stats_response_stat_space_no_value() -> None:
    # "STAT \r\n" -> body == "" -> parts == [] -> len(parts) != 2 and
    # len(parts) != 1, so the elif is skipped and the arc 144->133 is taken.
    assert _parse_stats_response(b"STAT \r\nEND\r\n") == {}


def test_parse_stats_response_stat_tab_no_value() -> None:
    # "STAT\t\r\n" -> body == "" -> parts == [] -> same skip for the tab
    # branch, taking the arc 151->133.
    assert _parse_stats_response(b"STAT\t\r\nEND\r\n") == {}


# --- format_memcached_report_markdown reachable branch gap (357->365) ---


def test_format_memcached_report_markdown_empty_shown_with_others() -> None:
    # Stats present but none of the primary_keys appear, so `shown` is
    # empty (357->365) while `others` is non-empty.
    data = {
        "target": "t",
        "host": "h",
        "port": 11211,
        "accessible": False,
        "version": None,
        "stats": {"custom_key": "1"},
        "findings": [],
        "error": None,
    }
    out = format_memcached_report_markdown(data)
    assert "### Other Stats" in out
    assert "custom_key" in out
    assert "| Stat |" not in out.split("### Other Stats")[0]