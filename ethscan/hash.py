"""Password hash generation module for ethscan.

Generates password hashes using common algorithms (MD5, SHA-1, SHA-256,
SHA-512, NTLM) for password-audit workflows. Stdlib only.
"""

import hashlib
import json
import struct
from typing import Dict, List, Optional


ALGORITHMS = {
    "md5": "MD5",
    "sha1": "SHA-1",
    "sha256": "SHA-256",
    "sha512": "SHA-512",
    "ntlm": "NTLM",
}

DEFAULT_ALGORITHMS = ["md5", "sha1", "sha256", "sha512", "ntlm"]


# MD4 implementation (stdlib doesn't guarantee MD4 availability)
# Based on RFC 1320
def _md4(data: bytes) -> bytes:
    """Compute MD4 hash of data."""
    # Initial hash values
    a = 0x67452301
    b = 0xEFCDAB89
    c = 0x98BADCFE
    d = 0x10325476

    # Pre-processing: padding
    original_len = len(data)
    data += b"\x80"
    while (len(data) % 64) != 56:
        data += b"\x00"
    data += struct.pack("<Q", original_len * 8)

    # Process each 512-bit chunk
    for i in range(0, len(data), 64):
        chunk = data[i : i + 64]
        X = struct.unpack("<16I", chunk)

        AA, BB, CC, DD = a, b, c, d

        # Round 1
        def F(x, y, z):
            return (x & y) | (~x & z)

        def rotl(x, n):
            return ((x << n) & 0xFFFFFFFF) | (x >> (32 - n))

        # Round 1 operations
        def R1(a, b, c, d, k, s):
            return rotl((a + F(b, c, d) + X[k]) & 0xFFFFFFFF, s)

        a = R1(a, b, c, d, 0, 3)
        d = R1(d, a, b, c, 1, 7)
        c = R1(c, d, a, b, 2, 11)
        b = R1(b, c, d, a, 3, 19)
        a = R1(a, b, c, d, 4, 3)
        d = R1(d, a, b, c, 5, 7)
        c = R1(c, d, a, b, 6, 11)
        b = R1(b, c, d, a, 7, 19)
        a = R1(a, b, c, d, 8, 3)
        d = R1(d, a, b, c, 9, 7)
        c = R1(c, d, a, b, 10, 11)
        b = R1(b, c, d, a, 11, 19)
        a = R1(a, b, c, d, 12, 3)
        d = R1(d, a, b, c, 13, 7)
        c = R1(c, d, a, b, 14, 11)
        b = R1(b, c, d, a, 15, 19)

        # Round 2
        def G(x, y, z):
            return (x & y) | (x & z) | (y & z)

        def R2(a, b, c, d, k, s):
            return rotl((a + G(b, c, d) + X[k] + 0x5A827999) & 0xFFFFFFFF, s)

        a = R2(a, b, c, d, 0, 3)
        d = R2(d, a, b, c, 4, 5)
        c = R2(c, d, a, b, 8, 9)
        b = R2(b, c, d, a, 12, 13)
        a = R2(a, b, c, d, 1, 3)
        d = R2(d, a, b, c, 5, 5)
        c = R2(c, d, a, b, 9, 9)
        b = R2(b, c, d, a, 13, 13)
        a = R2(a, b, c, d, 2, 3)
        d = R2(d, a, b, c, 6, 5)
        c = R2(c, d, a, b, 10, 9)
        b = R2(b, c, d, a, 14, 13)
        a = R2(a, b, c, d, 3, 3)
        d = R2(d, a, b, c, 7, 5)
        c = R2(c, d, a, b, 11, 9)
        b = R2(b, c, d, a, 15, 13)

        # Round 3
        def H(x, y, z):
            return x ^ y ^ z

        def R3(a, b, c, d, k, s):
            return rotl((a + H(b, c, d) + X[k] + 0x6ED9EBA1) & 0xFFFFFFFF, s)

        a = R3(a, b, c, d, 0, 3)
        d = R3(d, a, b, c, 8, 9)
        c = R3(c, d, a, b, 4, 11)
        b = R3(b, c, d, a, 12, 15)
        a = R3(a, b, c, d, 2, 3)
        d = R3(d, a, b, c, 10, 9)
        c = R3(c, d, a, b, 6, 11)
        b = R3(b, c, d, a, 14, 15)
        a = R3(a, b, c, d, 1, 3)
        d = R3(d, a, b, c, 9, 9)
        c = R3(c, d, a, b, 5, 11)
        b = R3(b, c, d, a, 13, 15)
        a = R3(a, b, c, d, 3, 3)
        d = R3(d, a, b, c, 11, 9)
        c = R3(c, d, a, b, 7, 11)
        b = R3(b, c, d, a, 15, 15)

        a = (a + AA) & 0xFFFFFFFF
        b = (b + BB) & 0xFFFFFFFF
        c = (c + CC) & 0xFFFFFFFF
        d = (d + DD) & 0xFFFFFFFF

    return struct.pack("<4I", a, b, c, d)


def _compute_hash(password: str, algorithm: str) -> str:
    """Compute a hash for the given password using the specified algorithm.

    Args:
        password: The password to hash.
        algorithm: One of 'md5', 'sha1', 'sha256', 'sha512', 'ntlm'.

    Returns:
        Hex-encoded hash string.
    """
    if algorithm == "ntlm":
        # NTLM is MD4 of the UTF-16LE encoded password
        return _md4(password.encode("utf-16le")).hex()

    return hashlib.new(algorithm, password.encode("utf-8")).hexdigest()


def run_hash(
    passwords: List[str],
    algorithms: Optional[List[str]] = None,
) -> Dict[str, object]:
    """Generate password hashes for the given passwords and algorithms.

    Args:
        passwords: List of passwords to hash.
        algorithms: List of algorithm names (default: all supported).

    Returns:
        Dictionary with 'passwords' count, 'algorithms' used, and 'results'
        list of per-password hash dictionaries.
    """
    if algorithms is None:
        algorithms = DEFAULT_ALGORITHMS[:]
    else:
        # Validate algorithms
        for alg in algorithms:
            if alg.lower() not in ALGORITHMS:
                raise ValueError(f"Unsupported algorithm: {alg}")

    results = []
    for pwd in passwords:
        pwd_hashes = {"password": pwd, "hashes": {}}
        for alg in algorithms:
            normalized = alg.lower()
            hash_value = _compute_hash(pwd, normalized)
            pwd_hashes["hashes"][ALGORITHMS[normalized]] = hash_value
        results.append(pwd_hashes)

    return {
        "passwords_hashed": len(passwords),
        "algorithms": [ALGORITHMS[a.lower()] for a in algorithms],
        "results": results,
    }


def format_hash_report_json(results: Dict[str, object]) -> str:
    """Render hash generation results as a JSON string."""
    return json.dumps(results, indent=2)


def format_hash_report_markdown(results: Dict[str, object]) -> str:
    """Render hash generation results as a Markdown string."""
    lines = ["# Password Hash Report", ""]
    lines.append(f"- **Passwords Hashed:** {results['passwords_hashed']}")
    lines.append(f"- **Algorithms:** {', '.join(results['algorithms'])}")
    lines.append("")

    if results["results"]:
        # Build header
        algo_names = results["algorithms"]
        header = "| Password | " + " | ".join(algo_names) + " |"
        separator = "|----------|" + "|".join(["----------"] * len(algo_names)) + "|"
        lines.append(header)
        lines.append(separator)

        for entry in results["results"]:
            pwd = entry["password"].replace("|", "\\|")
            hashes = entry["hashes"]
            row = "| " + pwd + " | " + " | ".join(hashes.get(a, "") for a in algo_names) + " |"
            lines.append(row)
    else:
        lines.append("*No passwords provided.*")

    lines.append("")
    return "\n".join(lines)