"""Password hash generation module for ethscan.

Generates cryptographic hashes for passwords using the stdlib ``hashlib``
module. Supports MD5, SHA-1, SHA-256, SHA-512, NTLM, and MD4 (when available
via OpenSSL). Fully offline and stdlib-only.
"""

import hashlib
import hmac
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


def _compute_peppered_hash(password: str, algorithm: str, pepper: str) -> str:
    """Compute an HMAC keyed hash of the password using the pepper as the key.

    Only algorithms backed by a direct hashlib name (md5, sha1, sha256,
    sha512, md4) can be used for HMAC. NTLM has no hashlib name and is
    therefore unsupported for peppered hashing.

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
    salt: Optional[str] = None,
    pepper: Optional[str] = None,
) -> str:
    """Compute a (optionally salted/peppered) hash for a single password.

    - ``salt`` is prepended to the password before hashing (a classic salted
      hash), e.g. ``hash(salt + password)``.
    - ``pepper`` is used as the HMAC key, with the password (or ``salt +
      password`` when both are supplied) as the message.
    - When both are supplied the salt is folded into the HMAC message and the
      pepper is the HMAC key: ``HMAC(pepper, salt + password, algorithm)``.
    - When neither is supplied this behaves identically to ``_compute_hash``.

    Args:
        password: Plaintext password.
        algorithm: Canonical algorithm key.
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
        return _compute_hash(salt + password, algorithm)
    if pepper:
        return _compute_peppered_hash(password, algorithm, pepper)
    return _compute_hash(password, algorithm)


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


def load_passwords_from_file(path: str) -> List[str]:
    """Load passwords from a file, one password per line.

    Args:
        path: Path to the password file.

    Returns:
        List of passwords (lines stripped, empty lines skipped).
    """
    with open(path, "r", encoding="utf-8") as handle:
        return [line.strip() for line in handle if line.strip()]


# ---------------------------------------------------------------------------
# Password check (compare plaintext against a known digest)
# ---------------------------------------------------------------------------

# Canonical digest lengths (hex) per algorithm, used to infer the algorithm
# from an unknown digest when ``--algorithm`` is not specified.
_DIGEST_LENGTHS: Dict[str, int] = {
    "md5": 32,
    "sha1": 40,
    "sha256": 64,
    "sha512": 128,
    "ntlm": 32,
    "md4": 32,
}


def _infer_algorithm(digest: str) -> Optional[str]:
    """Infer the algorithm from a hex digest's length.

    Args:
        digest: Hex digest string (case-insensitive).

    Returns:
        Canonical algorithm key, or ``None`` if no match.
    """
    if not digest:
        return None
    candidate = digest.strip().lower()
    # NTLM and MD4 share the 32-char length with MD5; prefer MD5 as the
    # most common guess but allow callers to disambiguate via --algorithm.
    matches = [name for name, length in _DIGEST_LENGTHS.items() if len(candidate) == length]
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]
    # Multiple matches (md5/ntlm/md4 all 32 chars): prefer md5.
    if "md5" in matches:
        return "md5"
    return matches[0]


def run_check(
    password: str,
    digest: str,
    algorithm: Optional[str] = None,
    salt: Optional[str] = None,
    pepper: Optional[str] = None,
) -> Dict[str, object]:
    """Compare a plaintext password against a known hash digest.

    Args:
        password: Plaintext password to check.
        digest: Expected hex digest to compare against.
        algorithm: Optional algorithm key (md5, sha1, sha256, sha512, ntlm,
            md4). When omitted, inferred from the digest length.
        salt: Optional salt prepended to the password before hashing (needed to
            verify a salted digest).
        pepper: Optional pepper used as the HMAC key (needed to verify a
            peppered digest).

    Returns:
        Structured result with ``password``, ``digest``, ``algorithm``,
        ``salt``, ``pepper``, ``computed``, ``match``, ``error`` fields.
    """
    error: Optional[str] = None
    chosen_algorithm: Optional[str] = None
    computed: Optional[str] = None
    match: Optional[bool] = None

    try:
        if algorithm:
            chosen_algorithm = _normalize_algorithm(algorithm)
        else:
            chosen_algorithm = _infer_algorithm(digest)

        if chosen_algorithm is None:
            error = (
                f"Could not infer algorithm from digest length {len(digest.strip())}; "
                "specify --algorithm explicitly."
            )
        else:
            computed = _compute_password_hash(
                password, chosen_algorithm, salt=salt, pepper=pepper
            )
            match = computed.lower() == digest.strip().lower()
    except ValueError as exc:
        error = str(exc)

    return {
        "password": password,
        "digest": digest,
        "algorithm": chosen_algorithm,
        "salt": bool(salt),
        "pepper": bool(pepper),
        "computed": computed,
        "match": match,
        "error": error,
    }


def run_hash(
    passwords: List[str],
    algorithm: str = "md5",
    salt: Optional[str] = None,
    pepper: Optional[str] = None,
) -> Dict[str, object]:
    """Generate hashes for a list of passwords.

    Args:
        passwords: Passwords to hash.
        algorithm: Algorithm key (md5, sha1, sha256, sha512, ntlm, md4).
        salt: Optional salt prepended to each password before hashing.
        pepper: Optional pepper used as the HMAC key (with ``salt +
            password`` as the message when salt is also supplied).

    Returns:
        Structured results with the algorithm, salt/pepper indicators,
        per-password hashes, and notes.
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
            digest = _compute_password_hash(
                pwd, normalized, salt=salt, pepper=pepper
            )
            error = None
        except ValueError as exc:
            digest = None
            error = str(exc)
        results.append(
            {
                "password": pwd,
                "algorithm": normalized,
                "salt": bool(salt),
                "pepper": bool(pepper),
                "hash": digest,
                "error": error,
            }
        )

    notes: List[str] = []
    if salt:
        notes.append("Salt applied: prepended to each password before hashing.")
    if pepper:
        notes.append(
            "Pepper applied: used as the HMAC key over the password (or "
            "salt+password when salt is also supplied)."
        )
    if normalized == "md4" and not MD4_AVAILABLE:
        notes.append("MD4 is unavailable on this OpenSSL build; use another algorithm.")
    if normalized == "ntlm" and not MD4_AVAILABLE:
        notes.append("NTLM requires MD4, which is unavailable on this OpenSSL build.")

    return {
        "algorithm": normalized,
        "salt": bool(salt),
        "pepper": bool(pepper),
        "passwords_hashed": len(password_list),
        "results": results,
        "notes": notes,
    }


def format_hash_report_json(data: Dict[str, object]) -> str:
    """Format hash results as a JSON string."""
    import json

    return json.dumps(data, indent=2, default=str)


def format_check_report_json(data: Dict[str, object]) -> str:
    """Format a password check result as a JSON string."""
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
    if data.get("salt"):
        lines.append("- **Salt:** applied (prepended to password)")
    if data.get("pepper"):
        lines.append("- **Pepper:** applied (HMAC key)")
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


def format_check_report_markdown(data: Dict[str, object]) -> str:
    """Format a password check result as a Markdown string."""
    lines = ["# ethscan Password Check Report", ""]
    lines.append(f"- **Password:** `{_escape(str(data.get('password', '')))}`")
    lines.append(f"- **Digest:** `{_escape(str(data.get('digest', '')))}`")
    algorithm = data.get("algorithm")
    if algorithm:
        lines.append(f"- **Algorithm:** {algorithm}")
    if data.get("salt"):
        lines.append("- **Salt:** applied (prepended to password)")
    if data.get("pepper"):
        lines.append("- **Pepper:** applied (HMAC key)")
    computed = data.get("computed")
    if computed is not None:
        lines.append(f"- **Computed:** `{_escape(str(computed))}`")
    match = data.get("match")
    if match is True:
        lines.append("- **Result:** MATCH")
    elif match is False:
        lines.append("- **Result:** MISMATCH")
    else:
        lines.append("- **Result:** UNKNOWN")
    error = data.get("error")
    if error:
        lines.append("")
        lines.append("## Error")
        lines.append(f"```\n{error}\n```")
    lines.append("")
    return "\n".join(lines)