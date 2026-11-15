"""Branch-gap tests for ethscan.subtake.

Covers the remaining partial branches:
- ``resolve_a_records`` / ``resolve_aaaa_records``: an empty ``getaddrinfo``
  result set takes the loop's "zero iterations" exit (356->354, 393->391).
- ``run_subtake``: a result whose ``hostname`` is not a string is skipped so
  the ``as_completed`` loop continues (556->540).
- ``format_subtake_report_markdown``: a truthy non-list ``all_results`` skips
  the per-entry loop entirely (679->697).
"""

from __future__ import annotations

import socket
from typing import Any

from ethscan.subtake import (
    format_subtake_report_markdown,
    resolve_a_records,
    resolve_aaaa_records,
    run_subtake,
)


def _empty_getaddrinfo(host, port, *args, **kwargs):
    return []


def test_resolve_a_records_empty_results_covers_356_354(monkeypatch) -> None:
    # An empty resolver answer set means the for-body never runs: 356->354.
    monkeypatch.setattr("ethscan.subtake.socket.getaddrinfo", _empty_getaddrinfo)
    assert resolve_a_records("example.invalid", timeout=0.1) == []


def test_resolve_aaaa_records_empty_results_covers_393_391(monkeypatch) -> None:
    # A non-string address in a non-empty result set fails the isinstance guard
    # and the loop continues: the 393->391 arc.
    def weird(host, port, *args, **kwargs):
        return [
            (
                socket.AF_INET6,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                (999, 0, 0, 0),
            ),
        ]

    monkeypatch.setattr("ethscan.subtake.socket.getaddrinfo", weird)
    assert resolve_aaaa_records("example.invalid", timeout=0.1) == []


def test_resolve_a_records_non_string_addr_skipped(monkeypatch) -> None:
    # A non-string address is filtered out by the isinstance guard, so the
    # result list is empty even though the loop body ran.
    def weird(host, port, *args, **kwargs):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (123, 0)),
        ]

    monkeypatch.setattr("ethscan.subtake.socket.getaddrinfo", weird)
    assert resolve_a_records("example.invalid", timeout=0.1) == []


def test_run_subtake_non_string_hostname_skipped_covers_556_540(monkeypatch) -> None:
    # The probe returns a non-string hostname, so the isinstance guard fails and
    # the as_completed loop continues without appending (556->540).
    monkeypatch.setattr(
        "ethscan.subtake.resolve_cname", lambda *a, **kw: None
    )
    monkeypatch.setattr("ethscan.subtake.resolve_a_records", lambda *a, **kw: [])
    monkeypatch.setattr("ethscan.subtake.resolve_aaaa_records", lambda *a, **kw: [])

    class _NonStringResult:
        def get(self, key: str, default: Any = None) -> Any:
            if key == "hostname":
                return 12345  # non-string -> guard fails
            return default

    class _Future:
        def result(self):
            return _NonStringResult()

    class _Executor:
        def __init__(self, max_workers):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def submit(self, fn, label):
            return _Future()

    monkeypatch.setattr("ethscan.subtake.ThreadPoolExecutor", _Executor)
    monkeypatch.setattr(
        "ethscan.subtake.as_completed",
        lambda future_to_label: list(future_to_label),
    )

    results = run_subtake("example.com", subdomains=["www"], timeout=1.0)
    assert results["all_results"] == []


def test_format_markdown_non_list_all_results_covers_679_697() -> None:
    # A truthy non-list all_results skips the per-entry loop: 679->697.
    data = {
        "target": "t",
        "domain": "d",
        "subdomains_tested": 1,
        "vulnerable_count": 0,
        "vulnerable": [],
        "all_results": "not-a-list",
    }
    out = format_subtake_report_markdown(data)
    assert "## All Results" in out
    # Column header row is still emitted; no data rows follow.
    assert "| Subdomain | Hostname |" in out
    lines = [
        ln
        for ln in out.splitlines()
        if ln.startswith("| ") and "---" not in ln and "Subdomain" not in ln
    ]
    assert lines == []