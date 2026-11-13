"""Hostile-shape sweep for osdetect report formatters."""

from __future__ import annotations

import json
from typing import Any, cast

from ethscan import osdetect

HOSTILE_TOP_LEVEL: tuple[object, ...] = (None, [], "x", 123, 1.5, True, b"bytes")


def test_osdetect_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        bad_any: Any = bad
        json.loads(osdetect.format_osdetect_report_json(cast(Any, bad_any)))
        md = osdetect.format_osdetect_report_markdown(cast(Any, bad_any))
        csv_text = osdetect.format_osdetect_report_csv(cast(Any, bad_any))
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan OS Detection Report" in md


def test_osdetect_formatters_hostile_nested_shapes_never_raise() -> None:
    cases: list[dict[str, object]] = [
        {"target": "x", "host": "x", "ports_probed": 1, "probes": None},
        {"target": "x", "host": "x", "ports_probed": 1, "probes": "notalist"},
        {
            "target": "x",
            "host": "x",
            "ports_probed": 1,
            "probes": [None, 5, "str", [], {}, {"port": 1}, {"port": "p"}],
        },
        {
            "target": "x",
            "host": "x",
            "ports_probed": 1,
            "probes": [{"port": "p"}],
            "inferred_os": None,
        },
        {"target": "x", "host": "x", "ports_probed": 1, "inferred_os": "linux"},
        {"target": "x", "host": "x", "ports_probed": 1, "inferred_os": [1, None, "Linux"]},
        {"target": "x", "host": "x", "ports_probed": 1, "notes": "x"},
        {"target": "x", "host": "x", "ports_probed": 1, "notes": [None, 5, {}]},
        {"target": "x", "host": "x", "ports_probed": 1, "notes": 1},
        {"target": "x", "host": "x", "ports_probed": 1, "notes": None},
        {"target": "x", "host": "x", "ports_probed": 1, "probe_findings": "x"},
    ]
    for data in cases:
        json.loads(osdetect.format_osdetect_report_json(data))
        md = osdetect.format_osdetect_report_markdown(data)
        csv_text = osdetect.format_osdetect_report_csv(data)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan OS Detection Report" in md
        # inferred_os as a string must not be char-split in CSV
        if data.get("inferred_os") == "linux":
            assert "inferred_os,,,l," not in csv_text
        if isinstance(data.get("inferred_os"), list) and 1 in cast(list[object], data["inferred_os"]):
            assert "Linux" in md or "1" in md
