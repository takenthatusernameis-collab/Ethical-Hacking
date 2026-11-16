"""Focused branch-coverage tests for ethscan.whois.

Closes reachable partial branches identified in branch-coverage analysis of
ethscan/whois.py.

Covered in this file (reachable):
- 367->369: a recursive hop whose parsed fields contain no registrar.
- 376->357: a recursive hop with no referral_server (loop-back edge).
"""
from __future__ import annotations

from ethscan.whois import format_whois_report_markdown


def test_recursive_hop_without_registrar_or_referral() -> None:
    # A hop with no registrar takes 367->369; a hop with no referral_server
    # takes 376->357 (the loop-back edge to the next iteration).
    data = {
        "target": "example.com",
        "server": "whois.iana.org",
        "port": 43,
        "recursive": True,
        "recursive_hops": [
            {
                "depth": 1,
                "server": "whois.registrar.net",
                "port": 43,
                "parsed": {},
                "referral_server": None,
            }
        ],
    }
    out = format_whois_report_markdown(data)
    assert "## Recursive WHOIS Queries" in out
    assert "- **Depth 1:** whois.registrar.net:43" in out
    assert "  - Registrar:" not in out
    assert "  - Referral Server:" not in out


def test_recursive_hop_with_registrar_but_no_referral() -> None:
    # Isolates 376->357: a hop that does have a registrar still falls through
    # when it carries no referral_server.
    data = {
        "recursive": True,
        "recursive_hops": [
            {
                "depth": 2,
                "server": "whois.registrar.net",
                "parsed": {"registrar": "Example Registrar"},
            }
        ],
    }
    out = format_whois_report_markdown(data)
    assert "  - Registrar: Example Registrar" in out
    assert "  - Referral Server:" not in out