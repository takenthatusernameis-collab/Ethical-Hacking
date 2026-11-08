"""Hostile-shape sweep for ssh report formatters.

The ``run_ssh`` transport sweep (``test_ssh_hostile_sweep.py``) covers a
hostile server answer through the connector seam. This sweep covers the
formatters themselves: a result dict that is not the well-formed shape the
module produces -- hostile top-level shapes and nested shapes where
``host_key`` and ``findings`` are not the dicts/lists the formatters index
into -- must render to a string and never raise.
"""

from __future__ import annotations

import json
from typing import Any, cast

from ethscan.ssh import (
    format_ssh_report_csv,
    format_ssh_report_json,
    format_ssh_report_markdown,
)

HOSTILE_TOP_LEVEL: tuple[object, ...] = (None, [], "x", 123, 1.5, True, b"bytes")


def test_ssh_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        bad_any: Any = bad
        json.loads(format_ssh_report_json(cast(Any, bad_any)))
        md = format_ssh_report_markdown(cast(Any, bad_any))
        csv_text = format_ssh_report_csv(cast(Any, bad_any))
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan SSH Security Assessment Report" in md


def test_ssh_formatters_hostile_nested_shapes_never_raise() -> None:
    cases = [
        {"target": "x", "host": "x", "port": 1, "timeout": 1.0, "error": "boom"},
        {"target": "x", "host": "x", "port": 1, "error": ""},
        {"target": "x", "host": "x", "port": 1, "host_key": "x", "findings": "x"},
        {"target": "x", "host": "x", "port": 1, "host_key": None, "findings": [None, 5, {}]},
        {"target": "x", "host": "x", "port": 1, "host_key": {"key_type": 123}, "findings": [{"severity": "x"}]},
        {"target": "x", "host": "x", "port": 1, "kex_algorithms": "x", "findings": []},
        {"target": "x", "host": "x", "port": 1, "host_key": {"key_type": "ssh-ed25519", "fingerprint": "aa:bb", "key_bits": 256}, "findings": [{"type": "weak_kex", "algorithm": "x", "severity": "high", "description": "d"}]},
        {"target": "x", "host": "x", "port": 1, "host_key": [], "findings": "notalist"},
        {"target": "x", "host": "x", "port": 1, "findings": [{"severity": "high"}, {"type": "x", "description": 123}]},
    ]
    for data in cases:
        json.loads(format_ssh_report_json(data))
        md = format_ssh_report_markdown(data)
        csv_text = format_ssh_report_csv(data)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan SSH Security Assessment Report" in md
        # A hostile host_key must not render a Host Key section from a
        # non-dict value. The findings section is only rendered when there
        # is no top-level error (the formatter returns early on error).
        if not isinstance(data.get("host_key"), dict):
            assert "## Host Key\n" not in md
        if not data.get("error") and not isinstance(data.get("findings"), (list, tuple)):
            assert "## Security Findings" in md