"""Permanent sweep test: hostile NTP formatter inputs are rendered, never raised.

Covers the two public formatters ``format_ntp_report_markdown`` and
``format_ntp_report_csv`` against hostile ``findings`` and ``peers`` values
(non-list/tuple scalars, lists of non-dict peer elements, etc.). Every shape
yields a string and never raises.
"""
from __future__ import annotations

from typing import Any, Callable

import pytest

from ethscan.ntp import (
    format_ntp_report_csv,
    format_ntp_report_markdown,
)

NTP_FORMATTERS: list[tuple[Callable[[dict[str, Any]], str], str]] = [
    (format_ntp_report_markdown, "findings"),
    (format_ntp_report_csv, "findings"),
]


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


NON_ITERABLE_FINDINGS: list[object] = [1, 0, "finding", {"x": 1}, None, True, 3.14]

HOSTILE_FINDING_LISTS: list[list[object]] = [
    [None],
    [1],
    [None, 1],
    ["ok", None, 1, 2.5, ["nested"]],
]


@pytest.mark.parametrize(
    ("formatter", "key"),
    NTP_FORMATTERS,
    ids=_formatter_id,
)
@pytest.mark.parametrize("findings", NON_ITERABLE_FINDINGS)
def test_ntp_formatters_tolerate_non_iterable_findings(
    formatter: Callable[[dict[str, Any]], str], key: str, findings: object
) -> None:
    output = formatter({key: findings})
    assert isinstance(output, str)
    # A non-iterable findings field is treated as empty, not rendered as content.
    assert "first" not in output
    assert "second" not in output
    if "markdown" in formatter.__name__:
        # NTP's markdown always renders a Findings section; an empty findings
        # field renders the "no notable findings" placeholder, not content.
        assert "- No notable findings" in output


@pytest.mark.parametrize(
    ("formatter", "key"),
    NTP_FORMATTERS,
    ids=_formatter_id,
)
@pytest.mark.parametrize("findings", HOSTILE_FINDING_LISTS)
def test_ntp_formatters_render_hostile_findings_lists(
    formatter: Callable[[dict[str, Any]], str], key: str, findings: list[object]
) -> None:
    output = formatter({key: findings})
    assert isinstance(output, str)
    # Every element is rendered, stringified, rather than dropped or crashing.
    for item in findings:
        if item is None and "csv" in formatter.__name__:
            continue
        assert str(item) in output


@pytest.mark.parametrize(
    ("formatter", "key"),
    NTP_FORMATTERS,
    ids=_formatter_id,
)
def test_ntp_formatters_still_render_well_formed_findings(
    formatter: Callable[[dict[str, Any]], str], key: str
) -> None:
    output = formatter({key: ["first", "second"]})
    assert isinstance(output, str)
    assert "first" in output
    assert "second" in output


# ---------------------------------------------------------------------------
# Hostile ``peers`` values (nested inside ``monlist_response``).
# ---------------------------------------------------------------------------

HOSTILE_PEERS: list[object] = [
    None,
    1,
    True,
    "str",
    {},
    [None],
    [1],
    [None, 1],
    [{"address": "1.2.3.4"}],
    [{"address": "1.2.3.4"}, None, 1, {"bad": "peer"}],
]


@pytest.mark.parametrize("peers", HOSTILE_PEERS)
def test_ntp_markdown_tolerates_hostile_peers(peers: object) -> None:
    output = format_ntp_report_markdown({"monlist_response": {"peers": peers}})
    assert isinstance(output, str)


@pytest.mark.parametrize("peers", HOSTILE_PEERS)
def test_ntp_csv_tolerates_hostile_peers(peers: object) -> None:
    output = format_ntp_report_csv({"monlist_response": {"peers": peers}})
    assert isinstance(output, str)


def test_ntp_markdown_renders_well_formed_peers() -> None:
    output = format_ntp_report_markdown(
        {"monlist_response": {"peers": [{"address": "1.2.3.4", "port": 123, "mode": 3, "version": 4}]}}
    )
    assert "1.2.3.4:123" in output


def test_ntp_csv_renders_well_formed_peers() -> None:
    output = format_ntp_report_csv(
        {"monlist_response": {"peers": [{"address": "1.2.3.4", "port": 123, "mode": 3, "version": 4}]}}
    )
    assert "1.2.3.4" in output