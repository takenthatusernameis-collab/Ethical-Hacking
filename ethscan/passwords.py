"""Password strength auditing module for ethscan."""

import json
import math
from typing import Dict, List, Tuple

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


def evaluate_password(password: str) -> Dict[str, object]:
    """Evaluate a single password and return a structured report.

    Args:
        password: The password to evaluate.

    Returns:
        A dict with keys ``length``, ``entropy``, ``common``, ``patterns``,
        ``score`` (0-100) and ``verdict`` (one of ``strong``, ``fair``,
        ``weak``, ``very weak``).
    """
    length = len(password)
    entropy = estimate_entropy(password)
    common = is_common_password(password)
    patterns = has_repeated_patterns(password)

    # Start from a base score driven by entropy, then apply penalties.
    score = min(100.0, entropy * 2.5)
    if common:
        score = min(score, 20.0)
    if patterns:
        score = min(score, score - 15.0 if score > 15 else 0.0)
    if length < 8:
        score = min(score, 30.0)

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
        "score": round(score, 1),
        "verdict": verdict,
    }


def audit_passwords(passwords: List[str]) -> List[Tuple[str, Dict[str, object]]]:
    """Audit a list of passwords.

    Args:
        passwords: Passwords to evaluate.

    Returns:
        A list of ``(password, evaluation)`` tuples in the original order.
    """
    return [(pwd, evaluate_password(pwd)) for pwd in passwords]


def format_audit_report_json(
    passwords: List[str], results: List[Tuple[str, Dict[str, object]]]
) -> str:
    """Render password audit results as a JSON string."""
    report = {
        "passwords_audited": len(passwords),
        "results": [
            {
                "password": pwd,
                "length": eval_data["length"],
                "entropy": eval_data["entropy"],
                "common": eval_data["common"],
                "patterns": eval_data["patterns"],
                "score": eval_data["score"],
                "verdict": eval_data["verdict"],
            }
            for pwd, eval_data in results
        ],
    }
    return json.dumps(report, indent=2)


def format_audit_report_markdown(
    passwords: List[str], results: List[Tuple[str, Dict[str, object]]]
) -> str:
    """Render password audit results as a Markdown string."""
    lines = ["# Password Audit Report", ""]
    lines.append(f"- **Passwords Audited:** {len(passwords)}")
    lines.append("")

    if results:
        lines.append("| Password | Length | Entropy | Common | Patterns | Score | Verdict |")
        lines.append("|----------|--------|---------|--------|----------|-------|---------|")
        for pwd, eval_data in results:
            escaped_pwd = pwd.replace("|", "\\|")
            lines.append(
                f"| {escaped_pwd} | {eval_data['length']} | {eval_data['entropy']} | "
                f"{'Yes' if eval_data['common'] else 'No'} | "
                f"{'Yes' if eval_data['patterns'] else 'No'} | "
                f"{eval_data['score']} | {eval_data['verdict']} |"
            )
    else:
        lines.append("*No passwords provided for audit.*")
    lines.append("")

    return "\n".join(lines)