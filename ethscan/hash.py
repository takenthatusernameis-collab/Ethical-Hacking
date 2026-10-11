"""Password hash generation module for ethscan.

Generates cryptographic hashes for passwords using the stdlib ``hashlib``
module. Supports MD5, SHA-1, SHA-256, SHA-512, NTLM, and MD4 (when available
via OpenSSL). Fully offline and stdlib-only.
"""

import hashlib
from typing import Dict, List, Optional

# Algorithms supported natively by hashlib on this platform.
# Maps canonical key -> hashlib algorithm name.
_HASHLIB_ALGORITHMS = {
    "md5": "md5",
    "sha1": "sha1",
    "sha256": "sha256",
    "sha512": "sha512",
}

# Alias map: input key -> canonical key.
_ALIASES = {
    "sha-1": "sha1",
    "sha-256": "sha256",
    "sha-512": "sha512",
}

# MD4 is only available when OpenSSL exposes it (some builds disable it).
MD4_AVAILABLE = False
try:
    hashlib.new("md4")
    MD4_AVAILABLE = True
    _HASHLIB_ALGORITHMS["md4"] = "md4"
except (ValueError, TypeError):
    MD4_AVAILABLE = False


def _normalize_algorithm(algorithm: str) -> str:
    """Normalize an algorithm name to a canonical lowercase key.

    Args:
        algorithm: Algorithm name (e.g. ``"SHA-256"``, ``"md5"``).

    Returns:
        Canonical lowercase key (e.g. ``"sha256"``).

    Raises:
        ValueError: If the algorithm is not supported.
    """
    key = algorithm.strip().lower().replace("_", "-")
    if key in _ALIASES:
        return _ALIASES[key]
    if key in _HASHLIB_ALGORITHMS:
        return key
    if key == "ntlm":
        return "ntlm"
    if key == "md4" and MD4_AVAILABLE:
        return "md4"
    raise ValueError(f"Unsupported algorithm: {algorithm}")


def _compute_md5(password: str) -> str:
    return hashlib.md5(password.encode("utf-8")).hexdigest()


def _compute_sha1(password: str) -> str:
    return hashlib.sha1(password.encode("utf-8")).hexdigest()


def _compute_sha256(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _compute_sha512(password: str) -> str:
    return hashlib.sha512(password.encode("utf-8")).hexdigest()


def _compute_md4(password: str) -> str:
    if not MD4_AVAILABLE:
        raise ValueError("MD4 is not available on this platform (OpenSSL build).")
    return hashlib.new("md4", password.encode("utf-8")).hexdigest()


def _compute_ntlm(password: str) -> str:
    """Compute the NTLM hash of a password.

    NTLM is the MD4 of the UTF-16LE-encoded password.
    """
    utf16 = password.encode("utf-16-le")
    return hashlib.new("md4", utf16).hexdigest()


def _compute_hash(password: str, algorithm: str) -> str:
    """Compute the hash for a password using the given canonical algorithm key."""
    if algorithm == "md5":
        return _compute_md5(password)
    if algorithm in ("sha1", "sha-1"):
        return _compute_sha1(password)
    if algorithm in ("sha256", "sha-256"):
        return _compute_sha256(password)
    if algorithm in ("sha512", "sha-512"):
        return _compute_sha512(password)
    if algorithm == "md4":
        return _compute_md4(password)
    if algorithm == "ntlm":
        return _compute_ntlm(password)
    raise ValueError(f"Unsupported algorithm: {algorithm}")


def _hashlib_name(algorithm: str) -> Optional[str]:
    """Return the hashlib algorithm name for a canonical key, or None."""
    return _HASHLIB_ALGORITHMS.get(algorithm)


def _supported_algorithms() -> List[str]:
    """Return the list of supported algorithm keys (sorted)."""
    algos = set(_HASHLIB_ALGORITHMS.keys()) | {"ntlm"}
    return sorted(algos)


def _normalize_passwords(passwords: List[str]) -> List[str]:
    """Strip whitespace and drop empty passwords."""
    return [pwd.strip() for pwd in passwords if pwd.strip()]


def run_hash(
    passwords: List[str],
    algorithm: str = "md5",
) -> Dict[str, object]:
    """Generate hashes for a list of passwords.

    Args:
        passwords: Passwords to hash.
        algorithm: Algorithm key (md5, sha1, sha256, sha512, ntlm, md4).

    Returns:
        Structured results with the algorithm, per-password hashes, and notes.
    """
    # Allow md4/ntlm even when MD4 is unavailable so callers get graceful
    # per-password errors instead of an exception from run_hash itself.
    key = algorithm.strip().lower().replace("_", "-")
    if key in _ALIASES:
        normalized = _ALIASES[key]
    elif key in _HASHLIB_ALGORITHMS:
        normalized = key
    elif key == "ntlm":
        normalized = "ntlm"
    elif key == "md4":
        normalized = "md4"
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    password_list = _normalize_passwords(passwords)

    results: List[Dict[str, object]] = []
    for pwd in password_list:
        try:
            digest = _compute_hash(pwd, normalized)
            error = None
        except ValueError as exc:
            digest = None
            error = str(exc)
        results.append(
            {
                "password": pwd,
                "algorithm": normalized,
                "hash": digest,
                "error": error,
            }
        )

    notes: List[str] = []
    if normalized == "md4" and not MD4_AVAILABLE:
        notes.append("MD4 is unavailable on this OpenSSL build; use another algorithm.")
    if normalized == "ntlm" and not MD4_AVAILABLE:
        notes.append("NTLM requires MD4, which is unavailable on this OpenSSL build.")

    return {
        "algorithm": normalized,
        "passwords_hashed": len(password_list),
        "results": results,
        "notes": notes,
    }


def format_hash_report_json(data: Dict[str, object]) -> str:
    """Format hash results as a JSON string."""
    import json

    return json.dumps(data, indent=2, default=str)


def _escape(value: str) -> str:
    """Escape pipe characters for Markdown output."""
    return value.replace("|", "\\|")


def format_hash_report_markdown(data: Dict[str, object]) -> str:
    """Format hash results as a Markdown string."""
    lines = ["# ethscan Password Hash Report", ""]
    lines.append(f"- **Algorithm:** {data['algorithm']}")
    lines.append(f"- **Passwords Hashed:** {data['passwords_hashed']}")
    lines.append("")

    results = data.get("results") or []
    if results:
        lines.append("| Password | Algorithm | Hash |")
        lines.append("|----------|-----------|------|")
        for entry in results:
            pwd = _escape(str(entry.get("password", "")))
            algo = _escape(str(entry.get("algorithm", "")))
            h = entry.get("hash")
            hash_str = "" if h is None else _escape(str(h))
            lines.append(f"| {pwd} | {algo} | {hash_str} |")
    else:
        lines.append("*No passwords provided for hashing.*")
    lines.append("")

    notes = data.get("notes") or []
    if notes:
        lines.append("## Notes")
        for note in notes:
            lines.append(f"- {note}")
        lines.append("")

    return "\n".join(lines)