"""Password strength auditing module for ethscan."""
from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import math
from typing import Any

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


# Algorithms supported for HMAC (peppered hashing).
# Maps canonical key -> hashlib algorithm name.
_HASHLIB_ALGORITHMS = {
    "md5": "md5",
    "sha1": "sha1",
    "sha256": "sha256",
    "sha512": "sha512",
}


def _hashlib_name(algorithm: str) -> str | None:
    """Return the hashlib algorithm name for a canonical key, or None."""
    return _HASHLIB_ALGORITHMS.get(algorithm)


def _compute_peppered_hash(password: str, algorithm: str, pepper: str) -> str:
    """Compute an HMAC keyed hash of the password using the pepper as the key.

    Only algorithms backed by a direct hashlib name (md5, sha1, sha256,
    sha512) can be used for HMAC.

    Args:
        password: Plaintext password (the HMAC message).
        algorithm: Canonical algorithm key.
        pepper: Secret pepper value (the HMAC key).

    Returns:
        Hex digest of ``HMAC(pepper, password, algorithm)``.

    Raises:
        ValueError: If the algorithm cannot be expressed as a hashlib name.
    """
    name = _hashlib_name(algorithm)
    if name is None:
        raise ValueError(
            f"Algorithm '{algorithm}' does not support HMAC (peppered hashing)."
        )
    return hmac.new(
        pepper.encode("utf-8"),
        password.encode("utf-8"),
        name,
    ).hexdigest()


def _compute_password_hash(
    password: str,
    algorithm: str,
    salt: str | None = None,
    pepper: str | None = None,
) -> str:
    """Compute a (optionally salted/peppered) hash for a password.

    - ``salt`` is prepended to the password before hashing (a classic salted
      hash), e.g. ``hash(salt + password)``.
    - ``pepper`` is used as the HMAC key, with the password (or ``salt +
      password`` when both are supplied) as the message.
    - When both are supplied the salt is folded into the HMAC message and the
      pepper is the HMAC key: ``HMAC(pepper, salt + password, algorithm)``.
    - When neither ``salt`` nor ``pepper`` is supplied this behaves identically
      to a standard hash.

    Args:
        password: Plaintext password.
        algorithm: Canonical algorithm key (md5, sha1, sha256, sha512).
        salt: Optional salt string prepended to the password.
        pepper: Optional pepper string used as the HMAC key.

    Returns:
        Hex digest string.

    Raises:
        ValueError: If the algorithm is unsupported or does not support HMAC
            when a pepper is supplied.
    """
    if salt and pepper:
        name = _hashlib_name(algorithm)
        if name is None:
            raise ValueError(
                f"Algorithm '{algorithm}' does not support HMAC (peppered hashing)."
            )
        return hmac.new(
            pepper.encode("utf-8"),
            (salt + password).encode("utf-8"),
            name,
        ).hexdigest()
    if salt:
        return hashlib.new(algorithm, (salt + password).encode("utf-8")).hexdigest()
    if pepper:
        return _compute_peppered_hash(password, algorithm, pepper)
    return hashlib.new(algorithm, password.encode("utf-8")).hexdigest()


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


def evaluate_password(
    password: str,
    min_length: int | None = None,
    salt: str | None = None,
    pepper: str | None = None,
    algorithm: str = "sha256",
) -> dict[str, object]:
    """Evaluate a single password and return a structured report.

    Args:
        password: The password to evaluate.
        min_length: Optional minimum length threshold. Passwords shorter than
            this will be flagged as too short.
        salt: Optional salt prepended to the password before evaluation.
        pepper: Optional pepper used as HMAC key for peppered evaluation.
        algorithm: Hash algorithm to use for salted/peppered evaluation
            (default: sha256).

    Returns:
        A dict with keys ``length``, ``entropy``, ``common``, ``patterns``,
        ``score`` (0-100), ``verdict`` (one of ``strong``, ``fair``,
        ``weak``, ``very weak``), ``too_short`` (bool), ``salt`` (bool),
        ``pepper`` (bool).
    """
    # Apply salt/pepper transformation if provided
    eval_password = password
    if salt and pepper:
        eval_password = _compute_password_hash(password, algorithm, salt=salt, pepper=pepper)
    elif salt:
        eval_password = _compute_password_hash(password, algorithm, salt=salt)
    elif pepper:
        eval_password = _compute_password_hash(password, algorithm, pepper=pepper)

    length = len(eval_password)
    entropy = estimate_entropy(eval_password)
    common = is_common_password(eval_password)
    patterns = has_repeated_patterns(eval_password)
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
        "salt": bool(salt),
        "pepper": bool(pepper),
    }


VALID_SORT_KEYS = ("score", "verdict", "length")


def _sort_audit_pairs(
    results: list[tuple[str, dict[str, object]]],
    sort_by: str | None,
    sort_desc: bool,
) -> list[tuple[str, dict[str, object]]]:
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

    def sort_key(item: tuple[str, dict[str, object]]) -> Any:
        _, eval_data = item
        value = eval_data.get(sort_by)
        if sort_by == "verdict":
            # Verdicts are strings; sort alphabetically (case-insensitive).
            return str(value).lower()
        return value

    return sorted(results, key=sort_key, reverse=sort_desc)


def audit_passwords(
    passwords: list[str],
    min_length: int | None = None,
    sort_by: str | None = None,
    sort_desc: bool = True,
    salt: str | None = None,
    pepper: str | None = None,
    algorithm: str = "sha256",
) -> list[tuple[str, dict[str, object]]]:
    """Audit a list of passwords.

    Args:
        passwords: Passwords to evaluate.
        min_length: Optional minimum length threshold.
        sort_by: Optional sort field ('score', 'verdict', or 'length'); None
            keeps the original order.
        sort_desc: When True (default), sort descending.
        salt: Optional salt prepended to each password before evaluation.
        pepper: Optional pepper used as HMAC key for peppered evaluation.
        algorithm: Hash algorithm to use for salted/peppered evaluation
            (default: sha256).

    Returns:
        A list of ``(password, evaluation)`` tuples, sorted when ``sort_by`` is
        provided.
    """
    results = [
        (pwd, evaluate_password(pwd, min_length=min_length, salt=salt, pepper=pepper, algorithm=algorithm))
        for pwd in passwords
    ]
    return _sort_audit_pairs(results, sort_by, sort_desc)


def format_audit_report_json(
    passwords: list[str],
    results: list[tuple[str, dict[str, object]]],
    min_length: int | None = None,
    sort_by: str | None = None,
    sort_desc: bool = True,
    salt: str | None = None,
    pepper: str | None = None,
) -> str:
    """Render password audit results as a JSON string."""
    report = {
        "passwords_audited": len(passwords),
        "min_length": min_length,
        "salt": bool(salt),
        "pepper": bool(pepper),
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
                "salt": eval_data.get("salt", False),
                "pepper": eval_data.get("pepper", False),
            }
            for pwd, eval_data in results
        ],
    }
    return json.dumps(report, indent=2)


def format_audit_report_markdown(
    passwords: list[str],
    results: list[tuple[str, dict[str, object]]],
    min_length: int | None = None,
    sort_by: str | None = None,
    sort_desc: bool = True,
    salt: str | None = None,
    pepper: str | None = None,
) -> str:
    """Render password audit results as a Markdown string."""
    lines = ["# Password Audit Report", ""]
    lines.append(f"- **Passwords Audited:** {len(passwords)}")
    if min_length is not None:
        lines.append(f"- **Min Length:** {min_length}")
    if salt:
        lines.append("- **Salt:** applied (prepended to password)")
    if pepper:
        lines.append("- **Pepper:** applied (HMAC key)")
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
    passwords: list[str],
    results: list[tuple[str, dict[str, object]]],
    min_length: int | None = None,
    salt: str | None = None,
    pepper: str | None = None,
) -> str:
    """Render password audit results as a CSV string.

    Columns: password,length,entropy,common,patterns,too_short,score,verdict,salt,pepper
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
            "salt",
            "pepper",
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
                "true" if eval_data.get("salt", False) else "false",
                "true" if eval_data.get("pepper", False) else "false",
            ]
        )
    return output.getvalue().rstrip("\r\n")