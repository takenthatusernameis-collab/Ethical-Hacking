"""Permanent sweep tests: hostile findings shapes never crash report formatters.

The CSV formatters join their findings list into a single cell. A findings
list that carries a non-string element (a ``None`` from a failed probe, an
``int``, a nested list) made ``"; ".join(findings)`` raise ``TypeError`` --
while the Markdown formatters, which use f-strings, rendered the same value
without complaint. The CSV formatters now stringify every element, so a
hostile findings list is rendered instead of raising a traceback.

A non-iterable findings field (e.g. ``{"findings": 1}``) must likewise be
coerced to an empty list in both Markdown and CSV formatters rather than
raising ``TypeError`` on iteration.
"""
from __future__ import annotations

from typing import Any, Callable

import pytest

from ethscan import memcached, mongodb, mssql, mysql, postgresql, redis

#: (formatter, findings key) for every formatter that renders findings.
FINDINGS_FORMATTERS: list[tuple[Callable[[dict[str, Any]], str], str]] = [
    (memcached.format_memcached_report_markdown, "findings"),
    (memcached.format_memcached_report_csv, "findings"),
    (mongodb.format_mongodb_report_markdown, "findings"),
    (mongodb.format_mongodb_report_csv, "findings"),
    (mssql.format_mssql_report_markdown, "findings"),
    (mssql.format_mssql_report_csv, "findings"),
    (mysql.format_mysql_report_markdown, "findings"),
    (mysql.format_mysql_report_csv, "findings"),
    (postgresql.format_postgresql_report_markdown, "findings"),
    (postgresql.format_postgresql_report_csv, "findings"),
    (redis.format_redis_report_markdown, "dangerous_findings"),
    (redis.format_redis_report_csv, "dangerous_findings"),
]

#: (CSV formatter, findings key) for formatters that join findings.
CSV_FINDINGS_FORMATTERS: list[tuple[Callable[[dict[str, Any]], str], str]] = [
    (memcached.format_memcached_report_csv, "findings"),
    (mongodb.format_mongodb_report_csv, "findings"),
    (mssql.format_mssql_report_csv, "findings"),
    (mysql.format_mysql_report_csv, "findings"),
    (postgresql.format_postgresql_report_csv, "findings"),
    (redis.format_redis_report_csv, "dangerous_findings"),
]

HOSTILE_FINDINGS = [
    [None],
    [1],
    [None, 1],
    ["ok", None, 1, 2.5, ["nested"]],
]


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


@pytest.mark.parametrize(
    ("formatter", "key"),
    CSV_FINDINGS_FORMATTERS,
    ids=_formatter_id,
)
@pytest.mark.parametrize("findings", HOSTILE_FINDINGS)
def test_csv_findings_hostile_values_do_not_raise(
    formatter: Callable[[dict[str, Any]], str], key: str, findings: list[object]
) -> None:
    output = formatter({key: findings})
    assert isinstance(output, str)
    # Every element is rendered, stringified, rather than dropped or crashing.
    for item in findings:
        assert str(item) in output


@pytest.mark.parametrize(
    ("formatter", "key"),
    CSV_FINDINGS_FORMATTERS,
    ids=_formatter_id,
)
def test_csv_findings_strings_are_still_joined(
    formatter: Callable[[dict[str, Any]], str], key: str
) -> None:
    output = formatter({key: ["first", "second"]})
    assert "first; second" in output


@pytest.mark.parametrize(
    ("formatter", "key"),
    FINDINGS_FORMATTERS,
    ids=_formatter_id,
)
@pytest.mark.parametrize("findings", [1, 0, "finding", {"x": 1}, None, True, 3.14])
def test_findings_non_iterable_values_do_not_raise(
    formatter: Callable[[dict[str, Any]], str], key: str, findings: object
) -> None:
    output = formatter({key: findings})
    assert isinstance(output, str)
    # A non-iterable findings field is treated as empty, not rendered as content.
    assert "first" not in output
    assert "second" not in output
    # Markdown formatters should report no findings; CSV should produce an empty cell.
    if "markdown" in formatter.__name__:
        assert (
            "No notable findings" in output or "None detected" in output
        )