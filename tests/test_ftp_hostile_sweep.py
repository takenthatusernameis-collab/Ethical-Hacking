"""Permanent sweep test: a hostile FTP answer is reported, never raised."""
from __future__ import annotations

from typing import Any, Callable

import pytest

from ethscan import ftp
from ethscan.ftp import (
    format_ftp_report_csv,
    format_ftp_report_markdown,
)


TARGET = "127.0.0.1"

HOSTILE_BODIES: tuple[object, ...] = (
    "",
    "not ftp at all",
    "\x00" * 9,
    "hello world",
    "220 \x00\xff",
)


def _factory_for(body: object) -> Callable[[], object]:
    class _Client:
        def connect(self, host, port, timeout=30):
            return None

        def getwelcome(self):
            if isinstance(body, BaseException):
                raise body
            return body

        def login(self, user=None, passwd=None):
            return None

        def close(self):
            return None

    def factory():
        return _Client()

    return factory


def test_hostile_answer_is_reported_not_raised() -> None:
    for body in HOSTILE_BODIES:
        results = ftp.run_ftp(TARGET, check_anonymous=False, connector=_factory_for(body))
        assert isinstance(results, dict)
        assert "error" in results


def test_transport_failure_is_reported_not_raised() -> None:
    def factory():
        raise OSError("connection refused")

    results = ftp.run_ftp(TARGET, connector=factory)
    assert isinstance(results, dict)
    assert results.get("error")


def test_unnamed_transport_failure_is_reported_not_raised() -> None:
    def factory():
        raise RuntimeError("boom")

    results = ftp.run_ftp(TARGET, connector=factory)
    assert isinstance(results, dict)
    assert results.get("error")


# ---------------------------------------------------------------------------
# Formatter sweep: hostile ``findings`` values are rendered, never raised.
# ---------------------------------------------------------------------------

FTP_FORMATTERS: list[tuple[Callable[[dict[str, Any]], str], str]] = [
    (format_ftp_report_markdown, "findings"),
    (format_ftp_report_csv, "findings"),
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
    FTP_FORMATTERS,
    ids=_formatter_id,
)
@pytest.mark.parametrize("findings", NON_ITERABLE_FINDINGS)
def test_ftp_formatters_tolerate_non_iterable_findings(
    formatter: Callable[[dict[str, Any]], str], key: str, findings: object
) -> None:
    output = formatter({key: findings})
    assert isinstance(output, str)
    # A non-iterable findings field is treated as empty, not rendered as content.
    assert "first" not in output
    assert "second" not in output
    if "markdown" in formatter.__name__:
        assert "## Findings" not in output


@pytest.mark.parametrize(
    ("formatter", "key"),
    FTP_FORMATTERS,
    ids=_formatter_id,
)
@pytest.mark.parametrize("findings", HOSTILE_FINDING_LISTS)
def test_ftp_formatters_render_hostile_findings_lists(
    formatter: Callable[[dict[str, Any]], str], key: str, findings: list[object]
) -> None:
    output = formatter({key: findings})
    assert isinstance(output, str)
    # Every element is rendered, stringified, rather than dropped or crashing.
    # (CSV writes ``None`` as an empty cell; Markdown renders it as "None".)
    for item in findings:
        if item is None and "csv" in formatter.__name__:
            continue
        assert str(item) in output


@pytest.mark.parametrize(
    ("formatter", "key"),
    FTP_FORMATTERS,
    ids=_formatter_id,
)
def test_ftp_formatters_still_render_well_formed_findings(
    formatter: Callable[[dict[str, Any]], str], key: str
) -> None:
    output = formatter({key: ["first", "second"]})
    assert isinstance(output, str)
    assert "first" in output
    assert "second" in output
