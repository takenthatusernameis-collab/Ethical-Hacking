"""Hostile-shape sweep for report formatters."""

from __future__ import annotations

import json
from typing import Any, cast

import pytest

from ethscan import report

HOSTILE_TOP_LEVEL: tuple[object, ...] = (None, [], "x", 123, 1.5, True, b"bytes")

# Non-iterable scalars are the gap the string-based nested cases miss: a string
# is iterable (so ``{"scan": {"details": "x"}}`` does not crash), but an int /
# float / bool nested in ``scan``/``audit`` is not, and iterating it raises
# ``TypeError`` unless the formatters coerce the field to a list first.
NON_ITERABLE_NESTED: tuple[object, ...] = (1, 1.5, True)


def test_report_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        bad_any: Any = bad
        md = report.format_report_markdown(cast(Any, bad_any))
        csv_text = report.format_report_csv(cast(Any, bad_any))
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "# ethscan Report" in md
    for bad in (None, [], "x", 123, 1.5, True):
        json.loads(report.format_report_json(cast(Any, bad)))


def test_report_formatters_hostile_nested_shapes_never_raise() -> None:
    cases: list[dict[str, object]] = [
        {"scan": None},
        {"audit": None},
        {"scan": "x"},
        {"audit": "x"},
        {"scan": {"details": "x"}},
        {"audit": {"results": "x"}},
        {"scan": {"target": "t", "open_ports": [80], "details": [None, {"open": True}]}},
        {"audit": {"passwords_audited": 1, "results": [None, {"password": "p"}]}},
        {"scan": {"ports_scanned": "many"}, "audit": {"results": [{}]}},
    ]
    for data in cases:
        json.loads(report.format_report_json(data))
        md = report.format_report_markdown(data)
        csv_text = report.format_report_csv(data)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)


@pytest.mark.parametrize("bad", NON_ITERABLE_NESTED)
@pytest.mark.parametrize(
    ("section", "field"),
    [
        ("scan", "details"),
        ("scan", "open_ports"),
        ("audit", "results"),
    ],
)
def test_report_formatters_survive_non_iterable_nested_field(
    section: str, field: str, bad: object
) -> None:
    """A non-iterable scalar in a nested list field must not crash the formatters.

    Regression for ``{"scan": {"details": 1}}`` (and the ``open_ports`` /
    ``results`` siblings), which raised ``TypeError: 'int' object is not
    iterable`` in the Markdown and CSV formatters before the ``_as_list`` guard.
    """
    hostile = {section: {field: bad}}
    json.loads(report.format_report_json(hostile))
    md = report.format_report_markdown(hostile)
    csv_text = report.format_report_csv(hostile)
    assert isinstance(md, str)
    assert isinstance(csv_text, str)
    assert "# ethscan Report" in md
