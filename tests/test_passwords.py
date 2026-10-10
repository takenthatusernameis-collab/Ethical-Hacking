"""Tests for the ethscan password auditing module."""

import pytest

from ethscan.passwords import (
    audit_passwords,
    evaluate_password,
    estimate_entropy,
    format_audit_report_json,
    format_audit_report_markdown,
    has_repeated_patterns,
    is_common_password,
)


def test_estimate_entropy_empty() -> None:
    assert estimate_entropy("") == 0.0


def test_estimate_entropy_simple() -> None:
    # Lowercase only => pool 26 => log2(26) bits per char.
    assert estimate_entropy("abc") == pytest.approx(3 * 4.7004, abs=0.01)


def test_is_common_password_true() -> None:
    assert is_common_password("password") is True
    assert is_common_password("PASSWORD") is True


def test_is_common_password_false() -> None:
    assert is_common_password("correct-horse-battery-staple-9x!") is False


def test_has_repeated_patterns_true() -> None:
    assert has_repeated_patterns("abcabc") is True
    assert has_repeated_patterns("aaaa") is True


def test_has_repeated_patterns_false() -> None:
    assert has_repeated_patterns("abcdefgh") is False


def test_evaluate_password_strong() -> None:
    result = evaluate_password("correct-Horse-battery-staple-9x!")
    assert result["verdict"] == "strong"
    assert result["score"] >= 80
    assert result["common"] is False


def test_evaluate_password_common_weak() -> None:
    result = evaluate_password("123456")
    assert result["common"] is True
    assert result["verdict"] in ("weak", "very weak")


def test_evaluate_password_short() -> None:
    result = evaluate_password("Ab1!")
    assert result["length"] == 4
    assert result["verdict"] in ("weak", "very weak")


def test_audit_passwords_returns_pairs() -> None:
    results = audit_passwords(["password", "correct-Horse-battery-staple-9x!"])
    assert len(results) == 2
    for password, evaluation in results:
        assert isinstance(password, str)
        assert "score" in evaluation
        assert "verdict" in evaluation


def test_format_audit_report_json_basic() -> None:
    passwords = ["password", "correct-Horse-battery-staple-9x!"]
    results = audit_passwords(passwords)
    output = format_audit_report_json(passwords, results)
    assert "passwords_audited" in output
    assert "password" in output
    assert "correct-Horse-battery-staple-9x!" in output
    assert "score" in output
    assert "verdict" in output


def test_format_audit_report_json_empty() -> None:
    output = format_audit_report_json([], [])
    assert "passwords_audited" in output
    assert '"results": []' in output


def test_format_audit_report_markdown_basic() -> None:
    passwords = ["password", "correct-Horse-battery-staple-9x!"]
    results = audit_passwords(passwords)
    output = format_audit_report_markdown(passwords, results)
    assert "Password Audit Report" in output
    assert "Passwords Audited" in output
    assert "password" in output
    assert "correct-Horse-battery-staple-9x!" in output
    assert "Score" in output
    assert "Verdict" in output


def test_format_audit_report_markdown_empty() -> None:
    output = format_audit_report_markdown([], [])
    assert "Password Audit Report" in output
    assert "Passwords Audited" in output
    assert "No passwords provided for audit" in output


def test_format_audit_report_markdown_pipe_escape() -> None:
    passwords = ["pass|word"]
    results = audit_passwords(passwords)
    output = format_audit_report_markdown(passwords, results)
    assert "pass\\|word" in output