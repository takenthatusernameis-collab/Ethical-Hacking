"""Hostile-shape sweep for s3 report formatters."""

from __future__ import annotations

import json

from ethscan import s3

HOSTILE_TOP_LEVEL = (None, [], "x", 123, 1.5, True, b"bytes")


def test_s3_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        json.loads(s3.format_s3_report_json(bad))
        md = s3.format_s3_report_markdown(bad)
        csv_text = s3.format_s3_report_csv(bad)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan S3 Bucket Enumeration Report" in md


def test_s3_formatters_hostile_nested_shapes_never_raise() -> None:
    cases = [
        {"results": "x", "regions_checked": "x", "public_buckets": "x"},
        {"results": [None, "x", {"bucket": 1, "url": [2]}]},
        {"notes": "x", "public_buckets": [None, {}]},
    ]
    for data in cases:
        json.loads(s3.format_s3_report_json(data))
        md = s3.format_s3_report_markdown(data)
        csv_text = s3.format_s3_report_csv(data)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan S3 Bucket Enumeration Report" in md
