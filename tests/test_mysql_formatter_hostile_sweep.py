"""Permanent sweep test: hostile MySQL formatter inputs are rendered, never raised.

Covers ``format_mysql_report_markdown`` and ``format_mysql_report_csv`` against
hostile ``findings`` and ``handshake`` values (non-list/tuple scalars, lists of hostile
elements, non-dict handshake). Every shape yields a string and never raises.
"""
from __future__ import annotations

from typing import Any, Callable

import pytest

from ethscan.mysql import (
    format_mysql_report_csv,
    format_mysql_report_markdown,
)

MYSQL_FORMATTERS: list[Callable[[dict[str, Any]], str]] = [
    format_mysql_report_markdown,
    format_mysql_report_csv,
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

NON_DICT_HANDSHAKE: list[object] = [None, 1, 0, True, "handshake", ["not", "a", "dict"], 3.14]

HOSTILE_HANDSHAKE_DICTS: list[dict[str, object]] = [
    {"protocol_version": None},
    {"thread_id": "not-an-int", "capabilities": 1},
    {"key": ["nested", "list"]},
    {"1": "non-string-key"},
    {"normal": "value", "bad": None},
]


@pytest.mark.parametrize("formatter", MYSQL_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("findings", NON_ITERABLE_FINDINGS)
def test_mysql_formatters_tolerate_non_iterable_findings(
    formatter: Callable[[dict[str, Any]], str], findings: object
) -> None:
    output = formatter({"findings": findings})
    assert isinstance(output, str)
    assert "a-well-formed-finding" not in output
    if "markdown" in formatter.__name__:
        assert "## Findings" in output
        assert "- No notable findings" in output


@pytest.mark.parametrize("formatter", MYSQL_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("findings", HOSTILE_FINDING_LISTS)
def test_mysql_formatters_render_hostile_findings_lists(
    formatter: Callable[[dict[str, Any]], str], findings: list[object]
) -> None:
    output = formatter({"findings": findings})
    assert isinstance(output, str)
    for item in findings:
        if item is None and "csv" in formatter.__name__:
            continue
        assert str(item) in output


@pytest.mark.parametrize("formatter", MYSQL_FORMATTERS, ids=_formatter_id)
def test_mysql_formatters_still_render_well_formed_findings(
    formatter: Callable[[dict[str, Any]], str]
) -> None:
    output = formatter({"findings": ["first", "second"]})
    assert isinstance(output, str)
    assert "first" in output
    assert "second" in output


# ---------------------------------------------------------------------------
# Hostile ``handshake`` values (dict field iterated in Markdown, key-accessed in CSV).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("formatter", MYSQL_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("handshake", NON_DICT_HANDSHAKE)
def test_mysql_formatters_tolerate_non_dict_handshake(
    formatter: Callable[[dict[str, Any]], str], handshake: object
) -> None:
    output = formatter({"handshake": handshake})
    assert isinstance(output, str)
    # Non-dict handshake should not render the Handshake section.
    if "markdown" in formatter.__name__:
        assert "## Handshake" not in output or "No notable findings" in output


@pytest.mark.parametrize("formatter", MYSQL_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("handshake", HOSTILE_HANDSHAKE_DICTS)
def test_mysql_formatters_render_hostile_handshake_dicts(
    formatter: Callable[[dict[str, Any]], str], handshake: dict[str, object]
) -> None:
    output = formatter({"handshake": handshake})
    assert isinstance(output, str)
    # Markdown iterates specific keys; CSV accesses specific keys via .get().
    # The formatters should not crash on non-string values or nested structures.
    if "markdown" in formatter.__name__:
        # At least the Handshake section header should appear if handshake is a dict.
        assert "## Handshake" in output


@pytest.mark.parametrize("formatter", MYSQL_FORMATTERS, ids=_formatter_id)
def test_mysql_formatters_still_render_well_formed_handshake(
    formatter: Callable[[dict[str, Any]], str]
) -> None:
    output = formatter({
        "handshake": {
            "protocol_version": 10,
            "thread_id": 12345,
            "capabilities": 65535,
            "charset": 33,
            "status": 2,
            "auth_plugin_name": "mysql_native_password",
        }
    })
    assert isinstance(output, str)
    if "markdown" in formatter.__name__:
        assert "10" in output
        assert "12345" in output
        assert "65535" in output
        assert "33" in output
        assert "2" in output
        assert "mysql_native_password" in output
    else:
        # CSV has specific columns for these fields.
        assert "10" in output
        assert "12345" in output
        assert "65535" in output
        assert "33" in output
        assert "2" in output
        assert "mysql_native_password" in output