"""Hostile-shape sweep for passwords report formatters."""

from __future__ import annotations

import csv
import io
import json

from ethscan import passwords

HOSTILE_TOP_LEVEL = (None, [], "x", 123, 1.5, True, b"bytes")

GOOD_RESULT = (
    "pwd",
    {
        "length": 3,
        "entropy": 1.0,
        "common": False,
        "patterns": False,
        "too_short": False,
        "score": 10.0,
        "verdict": "weak",
        "salt": False,
        "pepper": False,
    },
)


def test_passwords_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        for fn in (
            passwords.format_audit_report_json,
            passwords.format_audit_report_markdown,
            passwords.format_audit_report_csv,
        ):
            out = fn(bad, [])
            assert isinstance(out, str)
            out = fn([], bad)
            assert isinstance(out, str)
    md = passwords.format_audit_report_markdown([], [])
    assert "# Password Audit Report" in md


def test_passwords_formatters_hostile_nested_results_never_raise() -> None:
    cases = [
        {"results": None},
        {"results": "notalist"},
        {"results": [(1, "notdict")]},
        {"results": [("pwd", None)]},
        {"results": [("pwd", {})]},
        {"results": [("pwd", {"length": 5})]},
        {"results": [("pwd", GOOD_RESULT[1]), "notapair", (1, 2, 3)]},
        {"results": [("pwd|pipe", GOOD_RESULT[1])]},
        {"passwords": None, "results": [GOOD_RESULT]},
        {"passwords": "single", "results": [GOOD_RESULT]},
        {"passwords": 123, "results": [GOOD_RESULT]},
    ]
    for data in cases:
        passwords_arg = data.get("passwords", [])
        results_arg = data.get("results", [])
        json.loads(passwords.format_audit_report_json(passwords_arg, results_arg))
        md = passwords.format_audit_report_markdown(passwords_arg, results_arg)
        csv_text = passwords.format_audit_report_csv(passwords_arg, results_arg)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)


def test_passwords_formatters_valid_output_unchanged() -> None:
    passwords_list = ["password", "correct-Horse-battery-staple-9x!"]
    results = passwords.audit_passwords(passwords_list)
    md = passwords.format_audit_report_markdown(passwords_list, results)
    csv_text = passwords.format_audit_report_csv(passwords_list, results)
    assert "# Password Audit Report" in md
    assert "correct-Horse-battery-staple-9x!" in md
    rows = list(csv.reader(io.StringIO(csv_text)))
    assert rows[0] == [
        "password",
        "length",
        "entropy",
        "common",
        "patterns",
        "too_short",
        "score",
        "verdict",
        "salt",
        "pepper",
    ]
    assert len(rows) == 3
