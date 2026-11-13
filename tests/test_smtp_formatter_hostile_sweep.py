"""Permanent sweep test: hostile SMTP formatter inputs are rendered, never raised.

Covers ``format_smtp_report_markdown`` and ``format_smtp_report_csv`` against
hostile ``findings``, ``capabilities``, and ``users`` values
(non-list/tuple scalars, lists of hostile elements).
Every shape yields a string and never raises.
"""
from __future__ import annotations

from typing import Any, Callable

import pytest

from ethscan.smtp import (
    format_smtp_report_csv,
    format_smtp_report_markdown,
)

SMTP_FORMATTERS: list[Callable[[dict[str, Any]], str]] = [
    format_smtp_report_markdown,
    format_smtp_report_csv,
]


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


NON_ITERABLE_FINDINGS: list[object] = [None, 1, 0, True, "finding", {"x": 1}, 3.14]

HOSTILE_FINDING_LISTS: list[list[object]] = [
    [None],
    [1],
    [None, 1],
    ["ok", None, 1, 2.5, {"nested": True}],
]

NON_ITERABLE_CAPABILITIES: list[object] = [None, 1, 0, True, "finding", {"x": 1}, 3.14]

HOSTILE_CAPABILITIES_LISTS: list[list[object]] = [
    [None],
    [1],
    [None, 1],
    ["AUTH", None, "STARTTLS", 2.5, {"nested": True}],
]

NON_ITERABLE_USERS: list[object] = [None, 1, 0, True, "user", {"x": 1}, 3.14]

HOSTILE_USERS_LISTS: list[list[object]] = [
    [None],
    [1],
    [None, 1],
    ["user1", None, 1, 2.5, {"nested": True}],
    [{"user": "valid", "found": True, "code": 250, "description": "ok"}],
]


@pytest.mark.parametrize("formatter", SMTP_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("findings", NON_ITERABLE_FINDINGS)
def test_smtp_formatters_tolerate_non_iterable_findings(
    formatter: Callable[[dict[str, Any]], str], findings: object
) -> None:
    output = formatter({"findings": findings})
    assert isinstance(output, str)
    assert "a-well-formed-finding" not in output


@pytest.mark.parametrize("formatter", SMTP_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("findings", HOSTILE_FINDING_LISTS)
def test_smtp_formatters_render_hostile_findings_lists(
    formatter: Callable[[dict[str, Any]], str], findings: list[object]
) -> None:
    output = formatter({"findings": findings})
    assert isinstance(output, str)
    for item in findings:
        if item is None and "csv" in formatter.__name__:
            continue
        assert str(item) in output


@pytest.mark.parametrize("formatter", SMTP_FORMATTERS, ids=_formatter_id)
def test_smtp_formatters_still_render_well_formed_findings(
    formatter: Callable[[dict[str, Any]], str]
) -> None:
    output = formatter({"findings": ["first", "second"]})
    assert isinstance(output, str)
    assert "first" in output
    assert "second" in output


# ---------------------------------------------------------------------------
# Hostile ``capabilities`` values.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("formatter", SMTP_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("capabilities", NON_ITERABLE_CAPABILITIES)
def test_smtp_formatters_tolerate_non_iterable_capabilities(
    formatter: Callable[[dict[str, Any]], str], capabilities: object
) -> None:
    output = formatter({"capabilities": capabilities})
    assert isinstance(output, str)
    # Non-iterable capabilities should not render the capabilities list.
    # The markdown formatter always shows STARTTLS Advertised (from data),
    # but not the Capabilities list. The CSV formatter doesn't show capabilities.
    assert "Capabilities:" not in output


@pytest.mark.parametrize("formatter", SMTP_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("capabilities", HOSTILE_CAPABILITIES_LISTS)
def test_smtp_formatters_render_hostile_capabilities_lists(
    formatter: Callable[[dict[str, Any]], str], capabilities: list[object]
) -> None:
    output = formatter({"capabilities": capabilities})
    assert isinstance(output, str)
    # Only the markdown formatter renders capabilities (as a joined string).
    # The CSV formatter does not render capabilities at all.
    if "markdown" in formatter.__name__:
        for item in capabilities:
            assert str(item) in output


@pytest.mark.parametrize("formatter", SMTP_FORMATTERS, ids=_formatter_id)
def test_smtp_formatters_still_render_well_formed_capabilities(
    formatter: Callable[[dict[str, Any]], str]
) -> None:
    output = formatter({"capabilities": ["AUTH", "STARTTLS", "SIZE"]})
    assert isinstance(output, str)
    if "markdown" in formatter.__name__:
        assert "AUTH" in output
        assert "STARTTLS" in output
        assert "SIZE" in output


# ---------------------------------------------------------------------------
# Hostile ``users`` values.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("formatter", SMTP_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("users", NON_ITERABLE_USERS)
def test_smtp_formatters_tolerate_non_iterable_users(
    formatter: Callable[[dict[str, Any]], str], users: object
) -> None:
    output = formatter({"users": users})
    assert isinstance(output, str)
    # Non-iterable users normalize to empty list. Markdown renders the section
    # header but with empty table; CSV renders empty row.
    # The key assertion: no crash, and no user content rendered.
    assert "valid" not in output


@pytest.mark.parametrize("formatter", SMTP_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("users", HOSTILE_USERS_LISTS)
def test_smtp_formatters_render_hostile_users_lists(
    formatter: Callable[[dict[str, Any]], str], users: list[object]
) -> None:
    output = formatter({"users": users})
    assert isinstance(output, str)
    # Only dict elements with expected keys should render content.
    if any(isinstance(u, dict) and u.get("user") == "valid" for u in users):
        assert "valid" in output


@pytest.mark.parametrize("formatter", SMTP_FORMATTERS, ids=_formatter_id)
def test_smtp_formatters_still_render_well_formed_users(
    formatter: Callable[[dict[str, Any]], str]
) -> None:
    output = formatter({
        "users": [
            {"user": "alice", "found": True, "code": 250, "description": "user known"},
            {"user": "bob", "found": False, "code": 550, "description": "no such user"},
        ]
    })
    assert isinstance(output, str)
    assert "alice" in output
    assert "bob" in output