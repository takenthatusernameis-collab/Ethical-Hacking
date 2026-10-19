"""Vulnerability check module for ethscan.

Cross-references detected services/versions (from ``service`` banners) and
TLS/SSL data (from ``tls``/``ssl`` command output) against a small built-in
CVE/weakness database and reports matches.
"""
from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import re

from ethscan.service import run_service

DEFAULT_TIMEOUT = 3.0
DEFAULT_WORKERS = 50
DEFAULT_RECURSIVE_DEPTH = 2

SEVERITIES = ("critical", "high", "medium", "low")

BANNER_SIGNATURES = [
    (
        re.compile(
            r"OpenSSH[_-]([0-9]+(?:\.[0-9]+)*(?:p[0-9]+)?)", re.IGNORECASE
        ),
        "OpenSSH",
    ),
    (
        re.compile(r"ProFTPD\s+([0-9]+(?:\.[0-9]+)+)", re.IGNORECASE),
        "ProFTPD",
    ),
    (
        re.compile(r"vsFTPd\s+([0-9]+(?:\.[0-9]+)*)", re.IGNORECASE),
        "vsftpd",
    ),
    (
        re.compile(r"Pure-FTPd\s+([0-9]+(?:\.[0-9]+)+)", re.IGNORECASE),
        "Pure-FTPd",
    ),
    (
        re.compile(r"FileZilla\s+Server\s+([0-9]+(?:\.[0-9]+)*)", re.IGNORECASE),
        "FileZilla",
    ),
    (
        re.compile(r"Dovecot\s+([0-9]+(?:\.[0-9]+)*)", re.IGNORECASE),
        "Dovecot",
    ),
    (
        re.compile(r"Postfix\s+([0-9]+(?:\.[0-9]+)*)", re.IGNORECASE),
        "Postfix",
    ),
    (
        re.compile(r"Exim\s+([0-9]+(?:\.[0-9]+)*)", re.IGNORECASE),
        "Exim",
    ),
]

SERVICE_VULNS = [
    {
        "kind": "service",
        "id": "CVE-2016-6210",
        "product": "OpenSSH",
        "version_min": "5.4",
        "min_inclusive": True,
        "version_max": "7.3",
        "max_inclusive": False,
        "title": "OpenSSH user enumeration via authentication timing",
        "severity": "medium",
        "description": (
            "OpenSSH before 7.3 allows remote attackers to enumerate valid "
            "usernames via timing differences when handling malformed packets."
        ),
    },
    {
        "kind": "service",
        "id": "CVE-2018-15473",
        "product": "OpenSSH",
        "version_max": "7.7",
        "max_inclusive": False,
        "title": "OpenSSH user enumeration via malformed userauth request",
        "severity": "medium",
        "description": (
            "OpenSSH before 7.7 allows remote attackers to enumerate valid "
            "usernames via a malformed SSH2_MSG_USERAUTH_REQUEST packet."
        ),
    },
    {
        "kind": "service",
        "id": "CVE-2016-0777",
        "product": "OpenSSH",
        "version_min": "5.4",
        "min_inclusive": True,
        "version_max": "7.2",
        "max_inclusive": False,
        "title": "OpenSSH roaming information disclosure",
        "severity": "medium",
        "description": (
            "OpenSSH 5.4 through 7.2 allows local users to obtain sensitive "
            "information from client memory via the roaming feature."
        ),
    },
    {
        "kind": "service",
        "id": "CVE-2016-0778",
        "product": "OpenSSH",
        "version_min": "5.4",
        "min_inclusive": True,
        "version_max": "7.2",
        "max_inclusive": False,
        "title": "OpenSSH roaming buffer overflow",
        "severity": "high",
        "description": (
            "OpenSSH 5.4 through 7.2 allows remote servers to trigger a "
            "buffer overflow in the client roaming implementation."
        ),
    },
    {
        "kind": "service",
        "id": "CVE-2015-3306",
        "product": "ProFTPD",
        "version_min": "1.3.0",
        "min_inclusive": True,
        "version_max": "1.3.5",
        "max_inclusive": True,
        "title": "ProFTPD mod_copy arbitrary file read/write",
        "severity": "critical",
        "description": (
            "ProFTPD 1.3.0 through 1.3.5 with mod_copy enabled allows "
            "remote attackers to read or write arbitrary files via SITE "
            "CPFR/CPTO commands."
        ),
    },
    {
        "kind": "service",
        "id": "VSFTPD-2.3.4-BACKDOOR",
        "product": "vsftpd",
        "version_min": "2.3.4",
        "min_inclusive": True,
        "version_max": "2.3.4",
        "max_inclusive": True,
        "title": "vsftpd 2.3.4 backdoor command execution",
        "severity": "critical",
        "description": (
            "The malicious vsftpd 2.3.4 release embeds a backdoor that "
            "provides an interactive shell on TCP port 6200 after a crafted "
            "login attempt."
        ),
    },
]

PROTOCOL_VULNS = [
    {
        "kind": "protocol",
        "id": "CVE-2014-3566",
        "protocol": "SSLv3",
        "title": "SSLv3 is vulnerable to POODLE",
        "severity": "high",
        "description": (
            "SSLv3 supports CBC-mode ciphers that allow a man-in-the-middle "
            "attacker to decrypt portions of secure connections (POODLE)."
        ),
    },
    {
        "kind": "protocol",
        "id": "CVE-2011-3389",
        "protocol": "TLSv1",
        "title": "TLS 1.0 is vulnerable to BEAST",
        "severity": "medium",
        "description": (
            "TLS 1.0 uses predictable IVs for CBC-mode cipher suites, "
            "enabling the BEAST attack against secure connections."
        ),
    },
    {
        "kind": "protocol",
        "id": "DEPRECATED-TLS1.1",
        "protocol": "TLSv1_1",
        "title": "TLS 1.1 is deprecated",
        "severity": "low",
        "description": (
            "TLS 1.1 is deprecated by RFC 8996 and lacks support for modern "
            "authenticated encryption cipher suites."
        ),
    },
]

CIPHER_VULNS = [
    {
        "kind": "cipher",
        "id": "CVE-2013-2566",
        "cipher_pattern": re.compile(r"RC4", re.IGNORECASE),
        "title": "RC4 cipher suites are cryptographically weak",
        "severity": "high",
        "description": (
            "RC4 cipher suites are vulnerable to multiple bias attacks "
            "(CVE-2013-2566, CVE-2014-8730) and must not be used."
        ),
    },
    {
        "kind": "cipher",
        "id": "CVE-2016-2183",
        "cipher_pattern": re.compile(r"DES", re.IGNORECASE),
        "title": "64-bit block ciphers (DES/3DES) are vulnerable to Sweet32",
        "severity": "medium",
        "description": (
            "DES and 3DES use 64-bit block sizes, making them vulnerable to "
            "the Sweet32 birthday attack (CVE-2016-2183)."
        ),
    },
    {
        "kind": "cipher",
        "id": "NULL-CIPHER",
        "cipher_pattern": re.compile(r"NULL", re.IGNORECASE),
        "title": "NULL cipher provides no encryption",
        "severity": "critical",
        "description": (
            "NULL cipher suites transmit traffic without any encryption."
        ),
    },
    {
        "kind": "cipher",
        "id": "CVE-2015-0204",
        "cipher_pattern": re.compile(r"\bEXP", re.IGNORECASE),
        "title": "Export-grade ciphers are weak (FREAK)",
        "severity": "high",
        "description": (
            "Export-grade (EXP*) cipher suites are vulnerable to the FREAK "
            "attack (CVE-2015-0204) due to deliberately weakened parameters."
        ),
    },
]

CERTIFICATE_VULNS = [
    {
        "kind": "certificate",
        "id": "WEAK-RSA-KEY",
        "check": "key_size_below",
        "value": 2048,
        "title": "RSA key size below 2048 bits",
        "severity": "medium",
        "description": (
            "Certificates using RSA keys below 2048 bits are considered "
            "weak and should be re-issued with larger keys."
        ),
    },
    {
        "kind": "certificate",
        "id": "MD5-SIGNATURE",
        "check": "signature_contains",
        "value": "md5",
        "title": "Certificate signed with MD5",
        "severity": "high",
        "description": (
            "MD5 certificate signatures are collision-prone and must not be "
            "trusted."
        ),
    },
    {
        "kind": "certificate",
        "id": "SHA1-SIGNATURE",
        "check": "signature_contains",
        "value": "sha1",
        "title": "Certificate signed with SHA-1",
        "severity": "medium",
        "description": (
            "SHA-1 certificate signatures are deprecated and collision-prone."
        ),
    },
]

VULN_DB = SERVICE_VULNS + PROTOCOL_VULNS + CIPHER_VULNS + CERTIFICATE_VULNS

# Algorithms supported for HMAC (peppered hashing), mirroring passwords.py.
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


def _compute_peppered_hash(text: str, algorithm: str, pepper: str) -> str:
    """Compute an HMAC keyed hash of ``text`` using the pepper as the key.

    Only algorithms backed by a direct hashlib name (md5, sha1, sha256,
    sha512) can be used for HMAC.

    Args:
        text: Plaintext input (the HMAC message).
        algorithm: Canonical algorithm key.
        pepper: Secret pepper value (the HMAC key).

    Returns:
        Hex digest of ``HMAC(pepper, text, algorithm)``.

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
        text.encode("utf-8"),
        name,
    ).hexdigest()


def _compute_password_hash(
    text: str,
    algorithm: str,
    salt: str | None = None,
    pepper: str | None = None,
) -> str:
    """Compute a (optionally salted/peppered) hash for a text input.

    - ``salt`` is prepended to the text before hashing (a classic salted
      hash), e.g. ``hash(salt + text)``.
    - ``pepper`` is used as the HMAC key, with the text (or ``salt +
      text`` when both are supplied) as the message.
    - When both are supplied the salt is folded into the HMAC message and the
      pepper is the HMAC key: ``HMAC(pepper, salt + text, algorithm)``.
    - When neither ``salt`` nor ``pepper`` is supplied this behaves identically
      to a standard hash.

    Args:
        text: Plaintext input.
        algorithm: Canonical algorithm key (md5, sha1, sha256, sha512).
        salt: Optional salt string prepended to the input.
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
            (salt + text).encode("utf-8"),
            name,
        ).hexdigest()
    if salt:
        return hashlib.new(algorithm, (salt + text).encode("utf-8")).hexdigest()
    if pepper:
        return _compute_peppered_hash(text, algorithm, pepper)
    return hashlib.new(algorithm, text.encode("utf-8")).hexdigest()


def _apply_salt_pepper_to_banner(
    banner: str,
    salt: str | None,
    pepper: str | None,
    algorithm: str,
) -> str:
    """Apply a salt/pepper transformation to a service banner before matching.

    This mirrors the salted/peppered evaluation pattern used by the ``audit``
    and ``hash`` commands: the salt is prepended to the banner and/or the
    pepper is used as an HMAC key, so that vulnerability signatures can be
    cross-referenced against salted/peppered banner representations.

    Args:
        banner: Raw service banner text.
        salt: Optional salt prepended to the banner.
        pepper: Optional pepper used as the HMAC key.
        algorithm: Hash algorithm to use for salted/peppered evaluation.

    Returns:
        The (possibly transformed) banner string.
    """
    if not salt and not pepper:
        return banner
    try:
        return _compute_password_hash(banner, algorithm, salt=salt, pepper=pepper)
    except ValueError:
        return banner


def _transform_banner(
    banner: str,
    algorithm: str,
    salt: str | None = None,
    pepper: str | None = None,
) -> str:
    """Apply an optional salt/pepper transformation to a banner before matching.

    - ``salt`` is prepended to the banner before hashing: ``hash(salt + banner)``.
    - ``pepper`` is used as the HMAC key, with the banner (or ``salt + banner``
      when both are supplied) as the message.
    - When both are supplied the salt is folded into the HMAC message and the
      pepper is the HMAC key: ``HMAC(pepper, salt + banner, algorithm)``.
    - When neither is supplied the banner is returned unchanged.

    Args:
        banner: Raw service banner text.
        algorithm: Canonical algorithm key (md5, sha1, sha256, sha512).
        salt: Optional salt string prepended to the banner.
        pepper: Optional pepper string used as the HMAC key.

    Returns:
        Transformed banner string suitable for signature matching.

    Raises:
        ValueError: If the algorithm is unsupported or does not support HMAC
            when a pepper is supplied.
    """
    if not banner:
        return banner
    if salt and pepper:
        name = _hashlib_name(algorithm)
        if name is None:
            raise ValueError(
                f"Algorithm '{algorithm}' does not support HMAC (peppered hashing)."
            )
        return hmac.new(
            pepper.encode("utf-8"),
            (salt + banner).encode("utf-8"),
            name,
        ).hexdigest()
    if salt:
        return hashlib.new(algorithm, (salt + banner).encode("utf-8")).hexdigest()
    if pepper:
        return _compute_peppered_hash(banner, algorithm, pepper)
    return banner



_SEVERITY_RANK: dict[str, int] = {
    name: idx for idx, name in enumerate(reversed(SEVERITIES))
}


def _severity_rank(level: str | None) -> int | None:
    """Return the numeric rank for a severity label, or None if unknown.

    Higher rank means higher severity: critical=3, high=2, medium=1, low=0.
    """
    if not level:
        return None
    return _SEVERITY_RANK.get(str(level).lower())


def _normalize_host(target: str) -> str:
    """Extract a bare hostname from a target that may be a URL or host.

    Args:
        target: Bare host (e.g. example.com) or URL (e.g. https://example.com/path).

    Returns:
        Lowercased hostname without scheme, path, or port.
    """
    normalized = target.strip()
    if "://" not in normalized:
        normalized = "https://" + normalized
    from urllib.parse import urlparse

    parsed = urlparse(normalized)
    return (parsed.hostname or parsed.netloc or "").lower()


def _extract_hosts_from_banner(banner: str) -> list[str]:
    """Extract potential hostnames and IP addresses from a service banner.

    Args:
        banner: Raw service banner text.

    Returns:
        List of unique hostnames/IPs found in the banner.
    """
    import re

    hosts: list[str] = []
    seen: set = set()

    # Pattern for hostnames (including subdomains)
    hostname_pattern = re.compile(
        r"\b([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+)\b"
    )

    for match in hostname_pattern.finditer(banner):
        host = match.group(1).lower()
        if host not in seen and not host.startswith("www.") and len(host) > 3:
            seen.add(host)
            hosts.append(host)

    return hosts


def parse_banner(banner: str) -> tuple[str | None, str | None]:
    """Extract the product name and version from a service banner.

    Args:
        banner: Raw service banner text (e.g. "SSH-2.0-OpenSSH_7.2p2").

    Returns:
        Tuple of (product, version), either of which may be None when the
        banner does not match any known signature.
    """
    for pattern, product in BANNER_SIGNATURES:
        match = pattern.search(banner)
        if match:
            return product, match.group(1)
    return None, None


def _version_tuple(version: str) -> tuple[int, ...]:
    """Convert a version string into a comparable tuple of integers."""
    parts = re.findall(r"[0-9]+", str(version))
    return tuple(int(part) for part in parts) if parts else ()


def version_in_range(version: str, spec: dict[str, object]) -> bool:
    """Check whether a version string falls within a range specification.

    Args:
        version: Version string (e.g. "7.2p2").
        spec: Range spec with optional ``version_min``/``version_max`` and
            ``min_inclusive``/``max_inclusive`` flags (inclusive by default).

    Returns:
        True when the version matches the range, False otherwise.
    """
    parsed = _version_tuple(version)
    if not parsed:
        return False

    if "version_min" in spec:
        minimum = _version_tuple(str(spec["version_min"]))
        if spec.get("min_inclusive", True):
            if parsed < minimum:
                return False
        elif parsed <= minimum:
            return False

    if "version_max" in spec:
        maximum = _version_tuple(str(spec["version_max"]))
        if spec.get("max_inclusive", True):
            if parsed > maximum:
                return False
        elif parsed >= maximum:
            return False

    return True


def _finding(entry: dict[str, object], **extra: object) -> dict[str, object]:
    """Build a finding dictionary from a database entry."""
    finding: dict[str, object] = {
        "id": entry["id"],
        "kind": entry["kind"],
        "title": entry["title"],
        "severity": entry["severity"],
        "description": entry["description"],
    }
    finding.update(extra)
    return finding


def match_service_vulns(
    product: str | None,
    version: str | None,
    port: int | None = None,
) -> list[dict[str, object]]:
    """Match a detected product/version against the service CVE database.

    Args:
        product: Product name extracted from a banner (e.g. "OpenSSH").
        version: Product version string (e.g. "7.2p2").
        port: Port the banner was captured on.

    Returns:
        List of matching vulnerability findings.
    """
    findings: list[dict[str, object]] = []
    if not product or not version:
        return findings
    for entry in SERVICE_VULNS:
        if str(entry["product"]).lower() != str(product).lower():
            continue
        if version_in_range(version, entry):
            findings.append(
                _finding(entry, product=product, version=version, port=port)
            )
    return findings


def match_protocol_vulns(
    supported_versions: list[str],
) -> list[dict[str, object]]:
    """Match supported TLS/SSL protocol versions against the weakness database.

    Args:
        supported_versions: Protocol version names (e.g. ["SSLv3", "TLSv1_2"]).

    Returns:
        List of matching vulnerability findings.
    """
    findings: list[dict[str, object]] = []
    for name in supported_versions:
        for entry in PROTOCOL_VULNS:
            if str(entry["protocol"]).lower() == str(name).lower():
                findings.append(_finding(entry, protocol=name))
    return findings


def match_cipher_vulns(
    supported_ciphers: list[str],
) -> list[dict[str, object]]:
    """Match supported cipher suites against the weak-cipher database.

    Args:
        supported_ciphers: Cipher suite names (e.g. ["RC4-SHA", "AES128-SHA"]).

    Returns:
        List of matching vulnerability findings.
    """
    findings: list[dict[str, object]] = []
    for cipher in supported_ciphers:
        for entry in CIPHER_VULNS:
            if entry["cipher_pattern"].search(str(cipher)):
                findings.append(_finding(entry, cipher=cipher))
    return findings


def match_certificate_vulns(cert_data: dict | None) -> list[dict[str, object]]:
    """Check parsed certificate data against the certificate weakness database.

    Args:
        cert_data: Parsed certificate dictionary as returned by the ``ssl``
            command (with ``key_size`` and ``signature_algorithm`` fields).

    Returns:
        List of matching vulnerability findings.
    """
    findings: list[dict[str, object]] = []
    if not cert_data:
        return findings

    key_size = cert_data.get("key_size")
    signature = str(cert_data.get("signature_algorithm") or "").lower()

    for entry in CERTIFICATE_VULNS:
        check = entry["check"]
        if check == "key_size_below":
            if key_size is not None and key_size < entry["value"]:
                findings.append(_finding(entry, key_size=key_size))
        elif check == "signature_contains" and entry["value"] in signature:
            findings.append(
                _finding(
                    entry,
                    signature_algorithm=cert_data.get("signature_algorithm"),
                )
            )
    return findings


def match_tls_vulns(tls_data: dict) -> list[dict[str, object]]:
    """Check ``tls`` command output for protocol and cipher weaknesses.

    Args:
        tls_data: Results dictionary from ``run_tls`` with
            ``supported_versions`` and ``supported_ciphers`` lists.

    Returns:
        List of matching vulnerability findings.
    """
    findings: list[dict[str, object]] = []
    findings.extend(match_protocol_vulns(tls_data.get("supported_versions") or []))
    findings.extend(match_cipher_vulns(tls_data.get("supported_ciphers") or []))
    return findings


def match_ssl_vulns(ssl_data: dict) -> list[dict[str, object]]:
    """Check ``ssl`` command output for certificate weaknesses.

    Args:
        ssl_data: Results dictionary from ``run_ssl`` with a ``cert`` key.

    Returns:
        List of matching vulnerability findings.
    """
    return match_certificate_vulns(ssl_data.get("cert") or {})


def run_vuln(
    target: str,
    ports: list[int] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    max_workers: int = DEFAULT_WORKERS,
    services: dict | None = None,
    tls: dict | None = None,
    certificate: dict | None = None,
    severity: str | None = None,
    min_severity: str | None = None,
    recursive: bool = False,
    max_depth: int = DEFAULT_RECURSIVE_DEPTH,
    salt: str | None = None,
    pepper: str | None = None,
    algorithm: str = "sha256",
) -> dict[str, object]:
    """Check a target for known service, protocol, and certificate vulnerabilities.

    Args:
        target: Hostname or URL (e.g. example.com or https://example.com).
        ports: Ports for live service detection. If None, uses the default set.
        timeout: Connection timeout in seconds.
        max_workers: Maximum number of concurrent workers for service detection.
        services: Pre-computed ``service`` command results. If None, service
            detection is run against the target.
        tls: Pre-computed ``tls`` command results used to check protocol and
            cipher weaknesses.
        certificate: Pre-computed ``ssl`` command results used to check
            certificate weaknesses.
        severity: Restrict findings to a single severity level
            (critical/high/medium/low). If None, all severities are reported.
        min_severity: Drop findings below this severity threshold
            (critical/high/medium/low). If None, no lower bound is applied.
        recursive: Enable recursive scanning of hosts discovered in service banners.
        max_depth: Maximum recursion depth for recursive scanning (default: 2).
        salt: Optional salt prepended to each banner before matching, allowing
            salted vulnerability signature cross-referencing.
        pepper: Optional pepper used as the HMAC key for peppered banner
            matching (requires a hashlib-backed algorithm).
        algorithm: Hash algorithm to use for salted/peppered banner matching
            (default: sha256).

    Returns:
        Structured results with matched findings, counts, and notes.
    """
    host = _normalize_host(target)

    all_findings: list[dict[str, object]] = []
    all_notes: list[str] = []
    recursive_hosts_scanned: list[str] = []
    recursive_findings: list[dict[str, object]] = []
    scanned_hosts: set = set()
    scanned_hosts.add(host)

    # Track initial scan results for summary
    initial_scan_results: dict[str, object] = {}

    def _scan_host(
        current_host: str,
        depth: int,
        current_ports: list[int] | None = None,
        current_services: dict | None = None,
        current_tls: dict | None = None,
        current_certificate: dict | None = None,
    ) -> dict[str, object]:
        """Scan a single host and return its results including banners."""
        # Use provided data only for the initial host; for recursive hosts, run live detection
        if depth == 0:
            svc_data = current_services
            tls_data = current_tls
            cert_data = current_certificate
        else:
            svc_data = None
            tls_data = None
            cert_data = None

        if svc_data is None:
            svc_data = run_service(
                current_host, ports=current_ports, timeout=timeout, max_workers=max_workers
            )

        findings: list[dict[str, object]] = []
        services_checked = 0
        banners: list[str] = []
        for entry in svc_data.get("results") or []:
            banner = entry.get("banner") or ""
            if banner:
                banners.append(banner)
            # Apply salt/pepper transformation to the banner before matching,
            # mirroring the salted/peppered evaluation pattern used by the
            # ``audit`` and ``hash`` commands.
            match_banner = _apply_salt_pepper_to_banner(
                banner, salt, pepper, algorithm
            )
            product, version = parse_banner(match_banner)
            findings.extend(
                match_service_vulns(product, version, port=entry.get("port"))
            )
            services_checked += 1

        tls_checked = tls_data is not None
        if tls_data:
            findings.extend(match_tls_vulns(tls_data))

        certificate_checked = cert_data is not None
        if cert_data:
            findings.extend(match_ssl_vulns(cert_data))

        if severity:
            findings = [f for f in findings if f["severity"] == severity]

        if min_severity:
            min_rank = _severity_rank(min_severity)
            if min_rank is not None:
                findings = [
                    f for f in findings
                    if _severity_rank(f.get("severity")) is not None
                    and _severity_rank(f.get("severity")) >= min_rank
                ]

        severity_counts: dict[str, int] = {name: 0 for name in SEVERITIES}
        for finding in findings:
            level = str(finding["severity"])
            severity_counts[level] = severity_counts.get(level, 0) + 1

        notes: list[str] = []
        if services_checked == 0:
            notes.append("No service banners detected")
        if not findings:
            notes.append("No known vulnerabilities matched")

        return {
            "host": current_host,
            "findings": findings,
            "finding_count": len(findings),
            "severity_counts": severity_counts,
            "services_checked": services_checked,
            "tls_checked": tls_checked,
            "certificate_checked": certificate_checked,
            "notes": notes,
            "banners": banners,
        }

    def _recursive_scan(current_host: str, depth: int) -> dict[str, object]:
        """Recursively scan a host and hosts discovered in its banners. Returns the scan result for current_host."""
        if depth > max_depth:
            return {}

        # Scan the current host
        result = _scan_host(current_host, depth, ports, services, tls, certificate)
        all_findings.extend(result["findings"])
        all_notes.extend(result["notes"])

        if depth == 0:
            # Track initial host results
            initial_scan_results["services_checked"] = result["services_checked"]
            initial_scan_results["tls_checked"] = result["tls_checked"]
            initial_scan_results["certificate_checked"] = result["certificate_checked"]

        # Extract hosts from banners for next recursion level
        if depth < max_depth:
            discovered_hosts: list[str] = []
            for banner in result.get("banners", []):
                discovered_hosts.extend(_extract_hosts_from_banner(banner))

            for discovered_host in discovered_hosts:
                normalized_discovered = _normalize_host(discovered_host)
                if normalized_discovered and normalized_discovered not in scanned_hosts:
                    scanned_hosts.add(normalized_discovered)
                    recursive_hosts_scanned.append(normalized_discovered)
                    # Recursively scan the discovered host and get its results
                    recursive_result = _recursive_scan(normalized_discovered, depth + 1)
                    if recursive_result:
                        recursive_findings.append({
                            "host": normalized_discovered,
                            "depth": depth + 1,
                            "findings": recursive_result.get("findings", []),
                            "finding_count": recursive_result.get("finding_count", 0),
                            "severity_counts": recursive_result.get("severity_counts", {}),
                            "services_checked": recursive_result.get("services_checked", 0),
                        })

        return result

    # Start recursive scanning
    if recursive:
        _recursive_scan(host, 0)
    else:
        # Non-recursive: just scan the initial host
        initial_result = _scan_host(host, 0, ports, services, tls, certificate)
        all_findings.extend(initial_result["findings"])
        all_notes.extend(initial_result["notes"])
        initial_scan_results["services_checked"] = initial_result["services_checked"]
        initial_scan_results["tls_checked"] = initial_result["tls_checked"]
        initial_scan_results["certificate_checked"] = initial_result["certificate_checked"]

    severity_counts: dict[str, int] = {name: 0 for name in SEVERITIES}
    for finding in all_findings:
        level = str(finding["severity"])
        severity_counts[level] = severity_counts.get(level, 0) + 1

    return {
        "target": target,
        "host": host,
        "timeout": timeout,
        "ports": ports,
        "services_checked": initial_scan_results.get("services_checked", 0),
        "tls_checked": initial_scan_results.get("tls_checked", False),
        "certificate_checked": initial_scan_results.get("certificate_checked", False),
        "severity_filter": severity,
        "min_severity_filter": min_severity,
        "findings": all_findings,
        "finding_count": len(all_findings),
        "severity_counts": severity_counts,
        "notes": all_notes,
        "recursive": recursive,
        "max_depth": max_depth if recursive else 0,
        "recursive_hosts_scanned": recursive_hosts_scanned,
        "recursive_findings": recursive_findings,
        "salt": bool(salt),
        "pepper": bool(pepper),
        "algorithm": algorithm,
    }


def format_vuln_report_json(data: dict[str, object]) -> str:
    """Format vulnerability check results as JSON."""
    return json.dumps(data, indent=2, default=str)


def format_vuln_report_csv(data: dict[str, object]) -> str:
    """Format vulnerability check results as CSV.

    Emits a header row followed by one row per finding with columns:
    id, type, severity, product, version, port, title, description.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "type",
            "severity",
            "product",
            "version",
            "port",
            "title",
            "description",
        ]
    )
    for finding in data.get("findings") or []:
        writer.writerow(
            [
                finding.get("id", ""),
                finding.get("kind", ""),
                finding.get("severity", ""),
                finding.get("product") or "",
                finding.get("version") or "",
                finding.get("port") or "",
                finding.get("title", ""),
                finding.get("description", ""),
            ]
        )
    return output.getvalue().rstrip("\r\n")


def _finding_detail(finding: dict[str, object]) -> str:
    """Render the per-finding details line for Markdown output."""
    kind = str(finding.get("kind", ""))
    if kind == "service":
        product = str(finding.get("product") or "Unknown")
        version = str(finding.get("version") or "")
        detail = f"{product} {version}".strip()
        port = finding.get("port")
        if port is not None:
            detail = f"{detail} (port {port})"
        return detail
    if kind == "protocol":
        return str(finding.get("protocol") or "")
    if kind == "cipher":
        return str(finding.get("cipher") or "")
    if kind == "certificate":
        key_size = finding.get("key_size")
        if key_size is not None:
            return f"key size {key_size} bits"
        signature = finding.get("signature_algorithm")
        if signature:
            return f"signature algorithm {signature}"
        return ""
    return ""


def _escape(value: str) -> str:
    """Escape pipe characters for Markdown output."""
    return value.replace("|", "\\|")


def format_vuln_report_markdown(data: dict[str, object]) -> str:
    """Format vulnerability check results as Markdown."""
    lines = ["# ethscan Vulnerability Report", ""]
    lines.append(f"- **Target:** {data['target']}")
    lines.append(f"- **Host:** {data['host']}")
    lines.append(f"- **Services Checked:** {data.get('services_checked', 0)}")
    lines.append(
        f"- **TLS Checked:** {'Yes' if data.get('tls_checked') else 'No'}"
    )
    lines.append(
        f"- **Certificate Checked:** "
        f"{'Yes' if data.get('certificate_checked') else 'No'}"
    )
    lines.append(f"- **Findings:** {data.get('finding_count', 0)}")
    if data.get("severity_filter"):
        lines.append(f"- **Severity Filter:** {data['severity_filter']}")
    if data.get("min_severity_filter"):
        lines.append(f"- **Min Severity:** {data['min_severity_filter']}")
    if data.get("salt"):
        lines.append("- **Salt:** applied (prepended to banner)")
    if data.get("pepper"):
        lines.append("- **Pepper:** applied (HMAC key)")
    lines.append(f"- **Algorithm:** {data.get('algorithm', 'sha256')}")
    if data.get("recursive"):
        lines.append("- **Recursive:** Yes")
        lines.append(f"- **Max Depth:** {data.get('max_depth', 0)}")
        lines.append(f"- **Recursive Hosts Scanned:** {len(data.get('recursive_hosts_scanned', []))}")
    lines.append("")

    severity_counts = data.get("severity_counts") or {}
    lines.append("## Severity Summary")
    for name in SEVERITIES:
        lines.append(f"- **{name.capitalize()}:** {severity_counts.get(name, 0)}")
    lines.append("")

    findings = data.get("findings") or []
    lines.append("## Findings")
    if findings:
        for finding in findings:
            lines.append(
                f"### {finding['id']} ({str(finding['severity']).upper()})"
            )
            lines.append(f"- **Type:** {finding['kind']}")
            detail = _escape(_finding_detail(finding))
            if detail:
                lines.append(f"- **Details:** {detail}")
            lines.append(f"- **Title:** {_escape(str(finding['title']))}")
            lines.append(
                f"- **Description:** {_escape(str(finding['description']))}"
            )
            lines.append("")
    else:
        lines.append("*No known vulnerabilities matched.*")
        lines.append("")

    notes = data.get("notes") or []
    if notes:
        lines.append("## Notes")
        for note in notes:
            lines.append(f"- {note}")
        lines.append("")

    if data.get("recursive"):
        recursive_hosts = data.get("recursive_hosts_scanned") or []
        recursive_findings = data.get("recursive_findings") or []
        if recursive_hosts or recursive_findings:
            lines.append("## Recursive Scan Results")
            if recursive_hosts:
                lines.append("### Hosts Scanned")
                lines.append("| Host | Depth | Findings |")
                lines.append("|------|-------|----------|")
                for rf in recursive_findings:
                    lines.append(
                        f"| {rf['host']} | {rf['depth']} | {rf['finding_count']} |"
                    )
                lines.append("")
            if recursive_findings:
                lines.append("### Recursive Findings")
                for rf in recursive_findings:
                    lines.append(f"#### Host: {rf['host']} (Depth {rf['depth']})")
                    lines.append(f"- **Services Checked:** {rf['services_checked']}")
                    lines.append(f"- **Findings:** {rf['finding_count']}")
                    rf_severity = rf.get("severity_counts") or {}
                    for name in SEVERITIES:
                        lines.append(f"- **{name.capitalize()}:** {rf_severity.get(name, 0)}")
                    rf_findings = rf.get("findings") or []
                    if rf_findings:
                        for finding in rf_findings:
                            lines.append(
                                f"  - {finding['id']} ({str(finding['severity']).upper()}): "
                                f"{_escape(_finding_detail(finding))}"
                            )
                    else:
                        lines.append("  *No vulnerabilities found.*")
                    lines.append("")

    return "\n".join(lines)
