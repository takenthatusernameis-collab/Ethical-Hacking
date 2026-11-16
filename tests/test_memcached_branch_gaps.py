"""Focused branch-coverage tests for ethscan.memcached.

Closes reachable partial branches identified in branch-coverage analysis of
ethscan/memcached.py.

Covered in this file (reachable):
- 53->64: bracketed host with no closing "]" (e.g. "[incomplete")
- 60->64: unbracketed host:port with non-digit rest (e.g. "host:abc")
- 357->365: primary stats present but empty (no key in primary_keys),
  while other (non-primary) stats are present.

Unreachable (defensive) branches - static invariants prevent coverage:
- 144->133: STAT line (space) with no value parts. The `line.strip()` call
  removes trailing whitespace, so `line.startswith("STAT ")` can only be True
  when a non-whitespace key follows, making `body.split(None, 1)` non-empty.
- 151->133: STAT line (tab) with no value parts. Same invariant as above;
  `strip()` removes trailing tabs/spaces.
"""
from ethscan.memcached import (
    _normalize_target,
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


# --- _parse_stats_response UNREACHABLE branch gaps (144->133, 151->133) ---
#
# These branches are statically unreachable due to the `line.strip()` call at
# line 134. After stripping, `line.startswith("STAT ")` is only True when a
# non-whitespace key follows, so `body.split(None, 1)` always returns at
# least one part. The `elif len(parts) == 1:` branches (144->145, 151->152)
# are reachable (key without value), but the false branches (144->133,
# 151->133) require `parts == []`, which is impossible post-strip.
#
# No test can cover 144->133 or 151->133; they are documented here for
# classification completeness.


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