"""Password strength auditing module for ethscan."""

import csv
import io
import json
import math
from typing import Any, Dict, List, Optional, Tuple

# Common passwords sourced from well-known weak-password lists (offline).
COMMON_PASSWORDS = {
    "password", "123456", "123456789", "12345678", "12345", "1234",
    "111111", "1234567", "qwerty", "abc123", "password1", "admin",
    "letmein", "welcome", "monkey", "dragon", "master", "login",
    "princess", "football", "shadow", "sunshine", "trustno1", "iloveyou",
    "batman", "access", "hello", "freedom", "whatever", "qazwsx",
    "jordan", "hunter", "buster", "soccer", "harley", "ranger",
    "george", "pepper", "killer", "samuel", "charlie", "michael",
    "thomas", "jessica", "ashley", "andrew", "maggie", "superman",
    "1q2w3e4r", "qwerty123", "123123", "000000", "654321", "666666",
}

# Character classes used to estimate entropy.
LOWER = "abcdefghijklmnopqrstuvwxyz"
UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
DIGITS = "0123456789"
SYMBOL = "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"


def _character_pool(password: str) -> int:
    """Return the size of the character pool used by ``password``."""
    pool = 0
    if any(c in LOWER for c in password):
        pool += 26
    if any(c in UPPER for c in password):
        pool += 26
    if any(c in DIGITS for c in password):
        pool += 10
    if any(c in SYMBOL for c in password):
        pool += 33
    # Fallback: every printable ASCII character counts as one slot.
    return pool or 1


def estimate_entropy(password: str) -> float:
    """Estimate the password's entropy in bits.

    Uses the standard ``pool_size ** length`` formula. This is a heuristic,
    not a guarantee of real-world strength.
    """
    if not password:
        return 0.0
    pool = _character_pool(password)
    return len(password) * math.log2(pool)


def is_common_password(password: str) -> bool:
    """Return ``True`` if ``password`` appears in the common-password list."""
    return password.lower() in COMMON_PASSWORDS


def has_repeated_patterns(password: str) -> bool:
    """Return ``True`` if the password contains obvious repeated sequences."""
    lowered = password.lower()
    max_pattern = len(lowered) // 2
    for length in range(2, max_pattern + 1):
        for start in range(len(lowered) - length * 2 + 1):
            pattern = lowered[start : start + length]
            if lowered[start + length : start + length * 2] == pattern:
                return True
    return False


def evaluate_password(password: str, min_length: Optional[int] = None) -> Dict[str, object]:
    """Evaluate a single password and return a structured report.

    Args:
        password: The password to evaluate.
        min_length: Optional minimum length threshold. Passwords shorter than
            this will be flagged as too short.

    Returns:
        A dict with keys ``length``, ``entropy``, ``common``, ``patterns``,
        ``score`` (0-100), ``verdict`` (one of ``strong``, ``fair``,
        ``weak``, ``very weak``), and ``too_short`` (bool).
    """
    length = len(password)
    entropy = estimate_entropy(password)
    common = is_common_password(password)
    patterns = has_repeated_patterns(password)
    too_short = min_length is not None and length < min_length

    # Start from a base score driven by entropy, then apply penalties.
    score = min(100.0, entropy * 2.5)
    if common:
        score = min(score, 20.0)
    if patterns:
        score = min(score, score - 15.0 if score > 15 else 0.0)
    if length < 8:
        score = min(score, 30.0)
    if too_short:
        score = min(score, 10.0)

    if score >= 80:
        verdict = "strong"
    elif score >= 50:
        verdict = "fair"
    elif score >= 20:
        verdict = "weak"
    else:
        verdict = "very weak"

    return {
        "length": length,
        "entropy": round(entropy, 2),
        "common": common,
        "patterns": patterns,
        "too_short": too_short,
        "score": round(score, 1),
        "verdict": verdict,
    }


VALID_SORT_KEYS = ("score", "verdict", "length")


def _sort_audit_pairs(
    results: List[Tuple[str, Dict[str, object]]],
    sort_by: Optional[str],
    sort_desc: bool,
) -> List[Tuple[str, Dict[str, object]]]:
    """Return a sorted copy of the audit result pairs.

    Args:
        results: List of ``(password, evaluation)`` tuples.
        sort_by: Field to sort by ('score', 'verdict', or 'length'); None keeps order.
        sort_desc: When True, sort descending.

    Returns:
        A new list sorted in place-safe order. Invalid sort keys preserve the
        original order.
    """
    if sort_by not in VALID_SORT_KEYS:
        return list(results)

    def sort_key(item: Tuple[str, Dict[str, object]]) -> Any:
        _, eval_data = item
        value = eval_data.get(sort_by)
        if sort_by == "verdict":
            # Verdicts are strings; sort alphabetically (case-insensitive).
            return str(value).lower()
        return value

    return sorted(results, key=sort_key, reverse=sort_desc)


def audit_passwords(
    passwords: List[str],
    min_length: Optional[int] = None,
    sort_by: Optional[str] = None,
    sort_desc: bool = True,
) -> List[Tuple[str, Dict[str, object]]]:
    """Audit a list of passwords.

    Args:
        passwords: Passwords to evaluate.
        min_length: Optional minimum length threshold.
        sort_by: Optional sort field ('score', 'verdict', or 'length'); None
            keeps the original order.
        sort_desc: When True (default), sort descending.

    Returns:
        A list of ``(password, evaluation)`` tuples, sorted when ``sort_by`` is
        provided.
    """
    results = [(pwd, evaluate_password(pwd, min_length=min_length)) for pwd in passwords]
    return _sort_audit_pairs(results, sort_by, sort_desc)


def format_audit_report_json(
    passwords: List[str],
    results: List[Tuple[str, Dict[str, object]]],
    min_length: Optional[int] = None,
    sort_by: Optional[str] = None,
    sort_desc: bool = True,
) -> str:
    """Render password audit results as a JSON string."""
    report = {
        "passwords_audited": len(passwords),
        "min_length": min_length,
        "sort_by": sort_by,
        "sort_desc": sort_desc,
        "results": [
            {
                "password": pwd,
                "length": eval_data["length"],
                "entropy": eval_data["entropy"],
                "common": eval_data["common"],
                "patterns": eval_data["patterns"],
                "too_short": eval_data.get("too_short", False),
                "score": eval_data["score"],
                "verdict": eval_data["verdict"],
            }
            for pwd, eval_data in results
        ],
    }
    return json.dumps(report, indent=2)


def format_audit_report_markdown(
    passwords: List[str],
    results: List[Tuple[str, Dict[str, object]]],
    min_length: Optional[int] = None,
    sort_by: Optional[str] = None,
    sort_desc: bool = True,
) -> str:
    """Render password audit results as a Markdown string."""
    lines = ["# Password Audit Report", ""]
    lines.append(f"- **Passwords Audited:** {len(passwords)}")
    if min_length is not None:
        lines.append(f"- **Min Length:** {min_length}")
    if sort_by:
        direction = "Descending" if sort_desc else "Ascending"
        lines.append(f"- **Sorted By:** {sort_by} ({direction})")
    lines.append("")

    if results:
        lines.append("| Password | Length | Entropy | Common | Patterns | Too Short | Score | Verdict |")
        lines.append("|----------|--------|---------|--------|----------|-----------|-------|---------|")
        for pwd, eval_data in results:
            escaped_pwd = pwd.replace("|", "\\|")
            too_short = "Yes" if eval_data.get("too_short", False) else "No"
            lines.append(
                f"| {escaped_pwd} | {eval_data['length']} | {eval_data['entropy']} | "
                f"{'Yes' if eval_data['common'] else 'No'} | "
                f"{'Yes' if eval_data['patterns'] else 'No'} | "
                f"{too_short} | "
                f"{eval_data['score']} | {eval_data['verdict']} |"
            )
    else:
        lines.append("*No passwords provided for audit.*")
    lines.append("")

    return "\n".join(lines)


def format_audit_report_csv(
    passwords: List[str],
    results: List[Tuple[str, Dict[str, object]]],
    min_length: Optional[int] = None,
) -> str:
    """Render password audit results as a CSV string.

    Columns: password,length,entropy,common,patterns,too_short,score,verdict
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "password",
            "length",
            "entropy",
            "common",
            "patterns",
            "too_short",
            "score",
            "verdict",
        ]
    )
    for pwd, eval_data in results:
        writer.writerow(
            [
                pwd,
                eval_data["length"],
                eval_data["entropy"],
                "true" if eval_data["common"] else "false",
                "true" if eval_data["patterns"] else "false",
                "true" if eval_data.get("too_short", False) else "false",
                eval_data["score"],
                eval_data["verdict"],
            ]
        )
    return output.getvalue().rstrip("\r\n")