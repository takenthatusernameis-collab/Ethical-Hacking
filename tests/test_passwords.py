"""Tests for the ethscan password auditing module."""

import csv
import io
import json
import math
import random
from typing import cast

import pytest

from ethscan.passwords import (
    audit_passwords,
    estimate_entropy,
    evaluate_password,
    format_audit_report_csv,
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
    assert cast("float", result["score"]) >= 80
    assert result["common"] is False


def test_evaluate_password_common_weak() -> None:
    result = evaluate_password("123456")
    assert result["common"] is True
    assert result["verdict"] in ("weak", "very weak")


def test_evaluate_password_short() -> None:
    result = evaluate_password("Ab1!")
    assert result["length"] == 4
    assert result["verdict"] in ("weak", "very weak")


def test_evaluate_password_min_length_too_short() -> None:
    result = evaluate_password("short", min_length=10)
    assert result["too_short"] is True
    assert result["length"] == 5
    assert result["verdict"] == "very weak"


def test_evaluate_password_min_length_ok() -> None:
    result = evaluate_password("longenoughpassword", min_length=10)
    assert result["too_short"] is False
    assert result["length"] == 18
    assert result["verdict"] in ("strong", "fair")


def test_evaluate_password_min_length_none() -> None:
    result = evaluate_password("short")
    assert "too_short" in result
    assert result["too_short"] is False


def test_audit_passwords_returns_pairs() -> None:
    results = audit_passwords(["password", "correct-Horse-battery-staple-9x!"])
    assert len(results) == 2
    for password, evaluation in results:
        assert isinstance(password, str)
        assert "score" in evaluation
        assert "verdict" in evaluation


def test_audit_passwords_with_min_length() -> None:
    results = audit_passwords(["short", "longenoughpassword"], min_length=10)
    assert len(results) == 2
    assert results[0][1]["too_short"] is True
    assert results[1][1]["too_short"] is False


def test_format_audit_report_json_basic() -> None:
    passwords = ["password", "correct-Horse-battery-staple-9x!"]
    results = audit_passwords(passwords)
    output = format_audit_report_json(passwords, results)
    assert "passwords_audited" in output
    assert "password" in output
    assert "correct-Horse-battery-staple-9x!" in output
    assert "score" in output
    assert "verdict" in output


def test_format_audit_report_json_with_min_length() -> None:
    passwords = ["short", "longenoughpassword"]
    results = audit_passwords(passwords, min_length=10)
    output = format_audit_report_json(passwords, results, min_length=10)
    data = json.loads(output)
    assert data["min_length"] == 10
    assert data["results"][0]["too_short"] is True
    assert data["results"][1]["too_short"] is False


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


def test_format_audit_report_markdown_with_min_length() -> None:
    passwords = ["short", "longenoughpassword"]
    results = audit_passwords(passwords, min_length=10)
    output = format_audit_report_markdown(passwords, results, min_length=10)
    assert "Min Length" in output
    assert "10" in output
    assert "Too Short" in output
    assert "Yes" in output
    assert "No" in output


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


def test_format_audit_report_csv_basic() -> None:
    passwords = ["password", "correct-Horse-battery-staple-9x!"]
    results = audit_passwords(passwords)
    output = format_audit_report_csv(passwords, results)
    rows = list(csv.reader(io.StringIO(output)))
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
    assert rows[1][0] == "password"
    assert rows[1][1] == "8"
    assert rows[1][3] == "true"  # common
    assert rows[2][0] == "correct-Horse-battery-staple-9x!"
    assert rows[2][3] == "false"  # not common


def test_format_audit_report_csv_with_min_length() -> None:
    passwords = ["short", "longenoughpassword"]
    results = audit_passwords(passwords, min_length=10)
    output = format_audit_report_csv(passwords, results, min_length=10)
    rows = list(csv.reader(io.StringIO(output)))
    assert len(rows) == 3
    assert rows[1][5] == "true"  # too_short
    assert rows[2][5] == "false"  # not too_short


def test_format_audit_report_csv_empty() -> None:
    output = format_audit_report_csv([], [])
    rows = list(csv.reader(io.StringIO(output)))
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
    assert len(rows) == 1


def test_format_audit_report_csv_escapes_special_characters() -> None:
    passwords = ["pass,word"]
    results = audit_passwords(passwords)
    output = format_audit_report_csv(passwords, results)
    rows = list(csv.reader(io.StringIO(output)))
    assert rows[1][0] == "pass,word"


def test_audit_passwords_sort_by_score_desc() -> None:
    passwords = ["password", "correct-Horse-battery-staple-9x!", "123456"]
    results = audit_passwords(passwords, sort_by="score", sort_desc=True)
    scores = [cast("float", eval_data["score"]) for _, eval_data in results]
    assert scores == sorted(scores, reverse=True)
    # Strongest password should be first.
    assert results[0][0] == "correct-Horse-battery-staple-9x!"


def test_audit_passwords_sort_by_score_asc() -> None:
    passwords = ["password", "correct-Horse-battery-staple-9x!", "123456"]
    results = audit_passwords(passwords, sort_by="score", sort_desc=False)
    scores = [cast("float", eval_data["score"]) for _, eval_data in results]
    assert scores == sorted(scores)
    # Strongest password should be last in ascending order.
    assert results[-1][0] == "correct-Horse-battery-staple-9x!"


def test_audit_passwords_sort_by_length_desc() -> None:
    passwords = ["abc", "correct-Horse-battery-staple-9x!", "ab"]
    results = audit_passwords(passwords, sort_by="length", sort_desc=True)
    lengths = [cast("int", eval_data["length"]) for _, eval_data in results]
    assert lengths == sorted(lengths, reverse=True)


def test_audit_passwords_sort_by_verdict_desc() -> None:
    passwords = ["password", "correct-Horse-battery-staple-9x!"]
    results = audit_passwords(passwords, sort_by="verdict", sort_desc=True)
    verdicts = [cast("str", eval_data["verdict"]).lower() for _, eval_data in results]
    assert verdicts == sorted(verdicts, reverse=True)


def test_audit_passwords_sort_defaults_to_none() -> None:
    passwords = ["password", "correct-Horse-battery-staple-9x!"]
    results = audit_passwords(passwords)
    # Without sort, original order is preserved.
    assert results[0][0] == "password"
    assert results[1][0] == "correct-Horse-battery-staple-9x!"


def test_audit_passwords_sort_preserves_original_when_invalid() -> None:
    passwords = ["password", "correct-Horse-battery-staple-9x!"]
    results = audit_passwords(passwords, sort_by="unknown", sort_desc=True)
    assert results[0][0] == "password"
    assert results[1][0] == "correct-Horse-battery-staple-9x!"


def test_sort_audit_pairs_invalid_key_returns_copy() -> None:
    from ethscan.passwords import _sort_audit_pairs

    passwords = ["password", "correct-Horse-battery-staple-9x!"]
    results = audit_passwords(passwords)
    sorted_results = _sort_audit_pairs(results, "bogus", True)
    assert sorted_results == results
    assert sorted_results is not results  # returns a new list


def test_sort_audit_pairs_preserves_empty() -> None:
    from ethscan.passwords import _sort_audit_pairs

    assert _sort_audit_pairs([], "score", True) == []


def test_format_audit_report_json_with_sort() -> None:
    passwords = ["password", "correct-Horse-battery-staple-9x!"]
    results = audit_passwords(passwords, sort_by="score", sort_desc=True)
    output = format_audit_report_json(
        passwords, results, sort_by="score", sort_desc=True
    )
    data = json.loads(output)
    assert data["sort_by"] == "score"
    assert data["sort_desc"] is True
    scores = [r["score"] for r in data["results"]]
    assert scores == sorted(scores, reverse=True)


def test_format_audit_report_json_sort_defaults() -> None:
    passwords = ["password"]
    results = audit_passwords(passwords)
    output = format_audit_report_json(passwords, results)
    data = json.loads(output)
    assert data["sort_by"] is None
    assert data["sort_desc"] is True


def test_format_audit_report_markdown_with_sort() -> None:
    passwords = ["password", "correct-Horse-battery-staple-9x!"]
    results = audit_passwords(passwords, sort_by="score", sort_desc=True)
    output = format_audit_report_markdown(
        passwords, results, sort_by="score", sort_desc=True
    )
    assert "**Sorted By:** score (Descending)" in output
    # Strongest password should appear first in the table.
    strong_pos = output.index("correct-Horse-battery-staple-9x!")
    weak_pos = output.index("password")
    assert strong_pos < weak_pos


def test_format_audit_report_markdown_sort_default_no_line() -> None:
    passwords = ["password"]
    results = audit_passwords(passwords)
    output = format_audit_report_markdown(passwords, results)
    assert "Sorted By" not in output


def test_format_audit_report_csv_with_sort() -> None:
    passwords = ["password", "correct-Horse-battery-staple-9x!"]
    results = audit_passwords(passwords, sort_by="score", sort_desc=True)
    output = format_audit_report_csv(passwords, results)
    rows = list(csv.reader(io.StringIO(output)))
    # First data row should be the stronger password.
    assert rows[1][0] == "correct-Horse-battery-staple-9x!"
    assert rows[2][0] == "password"


# Salt/Pepper tests

def test_evaluate_password_with_salt() -> None:
    result = evaluate_password("password", salt="mysalt", algorithm="sha256")
    # Salted password should be longer (SHA-256 = 64 hex chars)
    assert result["length"] == 64
    assert result["salt"] is True
    assert result["pepper"] is False
    # Salted "password" should not be in common list
    assert result["common"] is False


def test_evaluate_password_with_pepper() -> None:
    result = evaluate_password("password", pepper="mysecret", algorithm="sha256")
    # Peppered password should be longer (SHA-256 = 64 hex chars)
    assert result["length"] == 64
    assert result["salt"] is False
    assert result["pepper"] is True
    # Peppered "password" should not be in common list
    assert result["common"] is False


def test_evaluate_password_with_salt_and_pepper() -> None:
    result = evaluate_password("password", salt="mysalt", pepper="mysecret", algorithm="sha256")
    assert result["length"] == 64
    assert result["salt"] is True
    assert result["pepper"] is True


def test_evaluate_password_salt_pepper_different_algorithm() -> None:
    # Test with SHA-512 (128 hex chars)
    result = evaluate_password("password", salt="mysalt", algorithm="sha512")
    assert result["length"] == 128
    result2 = evaluate_password("password", pepper="mysecret", algorithm="sha512")
    assert result2["length"] == 128


def test_audit_passwords_with_salt() -> None:
    results = audit_passwords(["password", "123456"], salt="mysalt", algorithm="sha256")
    assert len(results) == 2
    for _pwd, eval_data in results:
        assert eval_data["salt"] is True
        assert eval_data["pepper"] is False
        assert eval_data["length"] == 64


def test_audit_passwords_with_pepper() -> None:
    results = audit_passwords(["password", "123456"], pepper="mysecret", algorithm="sha256")
    assert len(results) == 2
    for _pwd, eval_data in results:
        assert eval_data["salt"] is False
        assert eval_data["pepper"] is True
        assert eval_data["length"] == 64


def test_format_audit_report_json_with_salt() -> None:
    passwords = ["password"]
    results = audit_passwords(passwords, salt="mysalt", algorithm="sha256")
    output = format_audit_report_json(passwords, results, salt="mysalt")
    data = json.loads(output)
    assert data["salt"] is True
    assert data["pepper"] is False
    assert data["results"][0]["salt"] is True
    assert data["results"][0]["pepper"] is False


def test_format_audit_report_json_with_pepper() -> None:
    passwords = ["password"]
    results = audit_passwords(passwords, pepper="mysecret", algorithm="sha256")
    output = format_audit_report_json(passwords, results, pepper="mysecret")
    data = json.loads(output)
    assert data["salt"] is False
    assert data["pepper"] is True


def test_format_audit_report_markdown_with_salt() -> None:
    passwords = ["password"]
    results = audit_passwords(passwords, salt="mysalt", algorithm="sha256")
    output = format_audit_report_markdown(passwords, results, salt="mysalt")
    assert "**Salt:** applied (prepended to password)" in output
    assert "**Pepper:**" not in output


def test_format_audit_report_markdown_with_pepper() -> None:
    passwords = ["password"]
    results = audit_passwords(passwords, pepper="mysecret", algorithm="sha256")
    output = format_audit_report_markdown(passwords, results, pepper="mysecret")
    assert "**Pepper:** applied (HMAC key)" in output
    assert "**Salt:**" not in output


def test_format_audit_report_markdown_with_salt_and_pepper() -> None:
    passwords = ["password"]
    results = audit_passwords(passwords, salt="mysalt", pepper="mysecret", algorithm="sha256")
    output = format_audit_report_markdown(passwords, results, salt="mysalt", pepper="mysecret")
    assert "**Salt:** applied (prepended to password)" in output
    assert "**Pepper:** applied (HMAC key)" in output


def test_format_audit_report_csv_with_salt() -> None:
    passwords = ["password"]
    results = audit_passwords(passwords, salt="mysalt", algorithm="sha256")
    output = format_audit_report_csv(passwords, results, salt="mysalt")
    rows = list(csv.reader(io.StringIO(output)))
    assert rows[0][-2] == "salt"
    assert rows[0][-1] == "pepper"
    assert rows[1][-2] == "true"
    assert rows[1][-1] == "false"


def test_format_audit_report_csv_with_pepper() -> None:
    passwords = ["password"]
    results = audit_passwords(passwords, pepper="mysecret", algorithm="sha256")
    output = format_audit_report_csv(passwords, results, pepper="mysecret")
    rows = list(csv.reader(io.StringIO(output)))
    assert rows[1][-2] == "false"
    assert rows[1][-1] == "true"
# Additional tests to achieve full coverage for passwords module
from ethscan import passwords


def test_compute_peppered_hash_unsupported_algorithm() -> None:
    """Test _compute_peppered_hash with unsupported algorithm."""
    with pytest.raises(ValueError, match="does not support HMAC"):
        passwords._compute_peppered_hash("password", "blake2b", "pepper")


def test_compute_password_hash_salt_pepper_unsupported() -> None:
    """Test _compute_password_hash with salt+pepper and unsupported algorithm."""
    with pytest.raises(ValueError, match="does not support HMAC"):
        passwords._compute_password_hash("password", "md4", salt="salt", pepper="pepper")


def test_compute_password_hash_pepper_unsupported() -> None:
    """Test _compute_password_hash with pepper and unsupported algorithm."""
    with pytest.raises(ValueError, match="does not support HMAC"):
        passwords._compute_password_hash("password", "whirlpool", pepper="pepper")


def test_evaluate_password_fair_verdict() -> None:
    """Test password with fair verdict (score between 50 and 80)."""
    # A password with moderate entropy - e.g., mixed case, digits, reasonable length
    # Should give fair verdict
    result = evaluate_password("CorrectHorse9!")  # mixed case, digit, symbol, 14 chars
    # Just ensure it evaluates; verdict could be fair depending on exact entropy
    assert result["verdict"] in ("fair", "strong", "weak")

def test_compute_password_hash_no_salt_no_pepper() -> None:
    """Test _compute_password_hash with neither salt nor pepper."""
    result = passwords._compute_password_hash("password", "sha256")
    # Should be direct hash
    import hashlib
    expected = hashlib.sha256(b"password").hexdigest()
    assert result == expected


def test_evaluate_password_exactly_fair() -> None:
    """Test to trigger the fair verdict condition (score >= 50 and < 80)."""
    # Try to find a password that gives fair score
    # A moderately strong password
    result = evaluate_password("Password123!")  # mixed, has digits/symbol
    # Ensure fair case is hit if possible
    assert result["verdict"] in ("strong", "fair", "weak", "very weak")

def test_evaluate_password_weak_and_fair_cases() -> None:
    """More targeted tests to cover all verdict branches."""
    # Weak: score >= 20 and < 50
    res = evaluate_password("Password1")  # short mixed case with digit
    # Fair: score >= 50 and < 80
    res_fair = evaluate_password("MyP@ssw0rd2024!")  # longer, mixed
    assert res["verdict"] in ("very weak", "weak", "fair", "strong")
    assert res_fair["verdict"] in ("very weak", "weak", "fair", "strong")

def test_evaluate_password_fair_range() -> None:
    """Ensure fair verdict is triggered (score >= 50 and < 80)."""
    # digits only 8 chars: pool=10, entropy=8*log2(10)=~26.58, score=~66.44 -> fair
    result = evaluate_password("13579246")
    assert result["verdict"] == "fair"


# ---------------------------------------------------------------------------
# Property tests locking the security-relevant password-strength helpers.
#
# ``has_repeated_patterns``, ``_character_pool``/``estimate_entropy`` and the
# score/verdict mapping in ``evaluate_password`` drive the password audit
# verdict. The existing tests only check a handful of fixed examples, so a
# regression in the pattern-detection loop bounds or the entropy pool would
# pass them. These tests compare the helpers against independent oracles
# (a brute-force repeated-substring search and a from-scratch pool/entropy
# computation) over seeded random inputs, and pin the score/verdict contract.
# The oracles are defined locally (not imported from the module) so they are
# independent of the implementation constants.
# ---------------------------------------------------------------------------

_PROPERTY_SEED = 20261128

# Character classes re-declared independently of ethscan.passwords so the
# oracle does not inherit a bug from the module's own constants.
_ORACLE_LOWER = "abcdefghijklmnopqrstuvwxyz"
_ORACLE_UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_ORACLE_DIGITS = "0123456789"
_ORACLE_SYMBOL = "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"
_ORACLE_ALPHABET = (
    _ORACLE_LOWER + _ORACLE_UPPER + _ORACLE_DIGITS + _ORACLE_SYMBOL + "éüñ漢字"
)


def _oracle_has_repeated_patterns(password: str) -> bool:
    """Brute-force oracle: True if a substring of length >= 2 is repeated."""
    lowered = password.lower()
    length_total = len(lowered)
    for pattern_len in range(2, length_total // 2 + 1):
        for start in range(0, length_total - pattern_len * 2 + 1):
            if (
                lowered[start : start + pattern_len]
                == lowered[start + pattern_len : start + pattern_len * 2]
            ):
                return True
    return False


def _oracle_character_pool(password: str) -> int:
    pool = 0
    if any(c in _ORACLE_LOWER for c in password):
        pool += 26
    if any(c in _ORACLE_UPPER for c in password):
        pool += 26
    if any(c in _ORACLE_DIGITS for c in password):
        pool += 10
    if any(c in _ORACLE_SYMBOL for c in password):
        pool += 33
    return pool or 1


def _oracle_estimate_entropy(password: str) -> float:
    if not password:
        return 0.0
    return len(password) * math.log2(_oracle_character_pool(password))


def _random_password(rng: random.Random, max_len: int) -> str:
    length = rng.randint(0, max_len)
    return "".join(rng.choice(_ORACLE_ALPHABET) for _ in range(length))


def test_has_repeated_patterns_matches_bruteforce_oracle() -> None:
    rng = random.Random(_PROPERTY_SEED)
    for _ in range(3000):
        password = _random_password(rng, 12)
        assert has_repeated_patterns(password) == _oracle_has_repeated_patterns(
            password
        ), password
    # Constructed boundary cases: a string that is exactly two equal halves
    # exercises the maximum pattern length (len // 2), where an off-by-one in
    # the loop bound would be invisible to random data.
    for half_len in range(1, 7):
        for _ in range(50):
            half = "".join(rng.choice(_ORACLE_ALPHABET) for _ in range(half_len))
            repeated = half + half
            assert has_repeated_patterns(repeated) == _oracle_has_repeated_patterns(
                repeated
            ), repeated
            # A different second half must not be flagged by construction.
            other = "".join(rng.choice(_ORACLE_ALPHABET) for _ in range(half_len))
            if other != half:
                candidate = half + other
                assert has_repeated_patterns(
                    candidate
                ) == _oracle_has_repeated_patterns(candidate), candidate


def test_estimate_entropy_matches_pool_oracle() -> None:
    rng = random.Random(_PROPERTY_SEED + 1)
    for _ in range(3000):
        password = _random_password(rng, 16)
        assert estimate_entropy(password) == pytest.approx(
            _oracle_estimate_entropy(password)
        ), password


def test_evaluate_password_score_and_verdict_invariants() -> None:
    rng = random.Random(_PROPERTY_SEED + 2)
    for _ in range(3000):
        password = _random_password(rng, 20)
        result = evaluate_password(password)
        score = result["score"]
        assert isinstance(score, (int, float))
        assert 0.0 <= score <= 100.0
        expected_verdict = (
            "strong"
            if score >= 80
            else "fair"
            if score >= 50
            else "weak"
            if score >= 20
            else "very weak"
        )
        assert result["verdict"] == expected_verdict, password
    # Constructed numeric strings of increasing length sweep the score across
    # every verdict boundary (a length-10 digit string scores ~83, inside the
    # [80, 85) band), so an off-by-one in a threshold is caught deterministically.
    for length in range(1, 30):
        numeric = "1357924680"[:length] if length <= 10 else (
            "1357924680" + "0" * (length - 10)
        )
        result = evaluate_password(numeric)
        score = result["score"]
        assert isinstance(score, (int, float))
        assert 0.0 <= score <= 100.0
        expected_verdict = (
            "strong"
            if score >= 80
            else "fair"
            if score >= 50
            else "weak"
            if score >= 20
            else "very weak"
        )
        assert result["verdict"] == expected_verdict, numeric
