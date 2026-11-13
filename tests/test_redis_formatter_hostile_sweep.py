"""Permanent sweep test: hostile Redis formatter inputs are rendered, never raised.

Covers ``format_redis_report_markdown`` and ``format_redis_report_csv``
against hostile ``info`` (non-dict scalars, hostile dicts with non-string
or nested values), ``config`` (non-dict values, hostile dicts with
non-string/nested values), and ``dangerous_findings`` (non-iterable
scalars, hostile lists). Every shape yields a string and never raises.
"""
from __future__ import annotations

from typing import Any, Callable

import pytest

from ethscan.redis import (
    format_redis_report_csv,
    format_redis_report_markdown,
)

REDIS_FORMATTERS: list[Callable[[dict[str, Any]], str]] = [
    format_redis_report_markdown,
    format_redis_report_csv,
]


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


NON_DICT_SCALARS: list[object] = [None, 1, 0, True, "config", ["not", "a", "dict"], 3.14]

HOSTILE_DICTS: list[dict[Any, object]] = [
    {"key": None},
    {"key": 1},
    {"key": ["nested", "list"]},
    {"key": {"nested": "dict"}},
    {1: "non-string-key"},
    {"normal": "value", "bad": None},
]

WELL_FORMED_INFO = {
    "redis_version": "7.0.0",
    "os": "Linux",
    "role": "master",
    "connected_clients": "5",
}

WELL_FORMED_CONFIG = {
    "bind": "127.0.0.1",
    "requirepass": "secret",
    "dir": "/var/lib/redis",
    "dbfilename": "dump.rdb",
}

NON_ITERABLE_FINDINGS: list[object] = [None, 1, 0, True, "finding", {"x": 1}, 3.14]

HOSTILE_FINDING_LISTS: list[list[object]] = [
    [None],
    [1],
    [None, 1],
    ["ok", None, 1, 2.5, {"nested": True}],
]


# ---------------------------------------------------------------------------
# Hostile ``info`` values (guarded by _as_dict; Markdown iterates specific
# keys, CSV accesses specific keys via .get()).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("formatter", REDIS_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("info", NON_DICT_SCALARS)
def test_redis_formatters_tolerate_non_dict_info(
    formatter: Callable[[dict[str, Any]], str], info: object
) -> None:
    output = formatter({"info": info})
    assert isinstance(output, str)
    # A non-dict info normalizes to {}, so no Server Info section.
    assert "## Server Info" not in output


@pytest.mark.parametrize("formatter", REDIS_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("info", HOSTILE_DICTS)
def test_redis_formatters_render_hostile_info_dicts(
    formatter: Callable[[dict[str, Any]], str], info: dict[str, object]
) -> None:
    output = formatter({"info": info})
    assert isinstance(output, str)
    # A dict info renders the Server Info header in Markdown; bad values
    # are stringified/escaped rather than crashing. CSV does not use sections.
    if "markdown" in formatter.__name__:
        assert "## Server Info" in output


@pytest.mark.parametrize("formatter", REDIS_FORMATTERS, ids=_formatter_id)
def test_redis_formatters_still_render_well_formed_info(
    formatter: Callable[[dict[str, Any]], str]
) -> None:
    output = formatter({"info": WELL_FORMED_INFO})
    assert isinstance(output, str)
    if "markdown" in formatter.__name__:
        assert "## Server Info" in output
        assert "7.0.0" in output
        assert "Linux" in output
        assert "master" in output
        assert "5" in output
    else:
        # CSV writes redis_version, os, role, connected_clients columns.
        assert "7.0.0" in output
        assert "Linux" in output
        assert "master" in output
        assert "5" in output


# ---------------------------------------------------------------------------
# Hostile ``config`` values (guarded by _as_dict; Markdown iterates specific
# keys, CSV accesses specific keys via .get()).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("formatter", REDIS_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("config", NON_DICT_SCALARS)
def test_redis_formatters_tolerate_non_dict_config(
    formatter: Callable[[dict[str, Any]], str], config: object
) -> None:
    output = formatter({"config": config})
    assert isinstance(output, str)
    # A non-dict config normalizes to {}; no Configuration section.
    assert "## Configuration (selected)" not in output


@pytest.mark.parametrize("formatter", REDIS_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("config", HOSTILE_DICTS)
def test_redis_formatters_render_hostile_config_dicts(
    formatter: Callable[[dict[str, Any]], str], config: dict[str, object]
) -> None:
    output = formatter({"config": config})
    assert isinstance(output, str)
    # Markdown iterates config and stringifies each value; CSV accesses
    # bind/requirepass via .get().
    if "markdown" in formatter.__name__:
        assert "## Configuration (selected)" in output


@pytest.mark.parametrize("formatter", REDIS_FORMATTERS, ids=_formatter_id)
def test_redis_formatters_still_render_well_formed_config(
    formatter: Callable[[dict[str, Any]], str]
) -> None:
    output = formatter({"config": WELL_FORMED_CONFIG})
    assert isinstance(output, str)
    if "markdown" in formatter.__name__:
        assert "## Configuration (selected)" in output
        assert "127.0.0.1" in output
        assert "secret" in output
        assert "/var/lib/redis" in output
        assert "dump.rdb" in output
    else:
        # CSV writes bind and requirepass_set columns.
        assert "127.0.0.1" in output
        assert "true" in output


# ---------------------------------------------------------------------------
# Hostile ``dangerous_findings`` values (iterated by both formatters;
# elements stringified).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("formatter", REDIS_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("findings", NON_ITERABLE_FINDINGS)
def test_redis_formatters_tolerate_non_iterable_findings(
    formatter: Callable[[dict[str, Any]], str], findings: object
) -> None:
    output = formatter({"dangerous_findings": findings})
    assert isinstance(output, str)
    # Non-iterable findings normalize to [], so "None detected" renders.
    if "markdown" in formatter.__name__:
        assert "## Dangerous Findings" in output
        assert "None detected" in output


@pytest.mark.parametrize("formatter", REDIS_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("findings", HOSTILE_FINDING_LISTS)
def test_redis_formatters_render_hostile_findings_lists(
    formatter: Callable[[dict[str, Any]], str], findings: list[object]
) -> None:
    output = formatter({"dangerous_findings": findings})
    assert isinstance(output, str)
    for item in findings:
        if item is None and "csv" in formatter.__name__:
            continue
        assert str(item) in output


@pytest.mark.parametrize("formatter", REDIS_FORMATTERS, ids=_formatter_id)
def test_redis_formatters_still_render_well_formed_findings(
    formatter: Callable[[dict[str, Any]], str]
) -> None:
    output = formatter({"dangerous_findings": ["first", "second"]})
    assert isinstance(output, str)
    assert "first" in output
    assert "second" in output