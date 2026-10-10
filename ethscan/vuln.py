"""Vulnerability check module for ethscan.

Cross-references detected services/versions (from ``service`` banners) and
TLS/SSL data (from ``tls``/``ssl`` command output) against a small built-in
CVE/weakness database and reports matches.
"""

import json
import re
from typing import Dict, List, Optional, Tuple

from ethscan.service import run_service


DEFAULT_TIMEOUT = 3.0
DEFAULT_WORKERS = 50

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


def parse_banner(banner: str) -> Tuple[Optional[str], Optional[str]]:
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


def _version_tuple(version: str) -> Tuple[int, ...]:
    """Convert a version string into a comparable tuple of integers."""
    parts = re.findall(r"[0-9]+", str(version))
    return tuple(int(part) for part in parts) if parts else ()


def version_in_range(version: str, spec: Dict[str, object]) -> bool:
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


def _finding(entry: Dict[str, object], **extra: object) -> Dict[str, object]:
    """Build a finding dictionary from a database entry."""
    finding: Dict[str, object] = {
        "id": entry["id"],
        "kind": entry["kind"],
        "title": entry["title"],
        "severity": entry["severity"],
        "description": entry["description"],
    }
    finding.update(extra)
    return finding


def match_service_vulns(
    product: Optional[str],
    version: Optional[str],
    port: Optional[int] = None,
) -> List[Dict[str, object]]:
    """Match a detected product/version against the service CVE database.

    Args:
        product: Product name extracted from a banner (e.g. "OpenSSH").
        version: Product version string (e.g. "7.2p2").
        port: Port the banner was captured on.

    Returns:
        List of matching vulnerability findings.
    """
    findings: List[Dict[str, object]] = []
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
    supported_versions: List[str],
) -> List[Dict[str, object]]:
    """Match supported TLS/SSL protocol versions against the weakness database.

    Args:
        supported_versions: Protocol version names (e.g. ["SSLv3", "TLSv1_2"]).

    Returns:
        List of matching vulnerability findings.
    """
    findings: List[Dict[str, object]] = []
    for name in supported_versions:
        for entry in PROTOCOL_VULNS:
            if str(entry["protocol"]).lower() == str(name).lower():
                findings.append(_finding(entry, protocol=name))
    return findings


def match_cipher_vulns(
    supported_ciphers: List[str],
) -> List[Dict[str, object]]:
    """Match supported cipher suites against the weak-cipher database.

    Args:
        supported_ciphers: Cipher suite names (e.g. ["RC4-SHA", "AES128-SHA"]).

    Returns:
        List of matching vulnerability findings.
    """
    findings: List[Dict[str, object]] = []
    for cipher in supported_ciphers:
        for entry in CIPHER_VULNS:
            if entry["cipher_pattern"].search(str(cipher)):
                findings.append(_finding(entry, cipher=cipher))
    return findings


def match_certificate_vulns(cert_data: Optional[dict]) -> List[Dict[str, object]]:
    """Check parsed certificate data against the certificate weakness database.

    Args:
        cert_data: Parsed certificate dictionary as returned by the ``ssl``
            command (with ``key_size`` and ``signature_algorithm`` fields).

    Returns:
        List of matching vulnerability findings.
    """
    findings: List[Dict[str, object]] = []
    if not cert_data:
        return findings

    key_size = cert_data.get("key_size")
    signature = str(cert_data.get("signature_algorithm") or "").lower()

    for entry in CERTIFICATE_VULNS:
        check = entry["check"]
        if check == "key_size_below":
            if key_size is not None and key_size < entry["value"]:
                findings.append(_finding(entry, key_size=key_size))
        elif check == "signature_contains":
            if entry["value"] in signature:
                findings.append(
                    _finding(
                        entry,
                        signature_algorithm=cert_data.get("signature_algorithm"),
                    )
                )
    return findings


def match_tls_vulns(tls_data: dict) -> List[Dict[str, object]]:
    """Check ``tls`` command output for protocol and cipher weaknesses.

    Args:
        tls_data: Results dictionary from ``run_tls`` with
            ``supported_versions`` and ``supported_ciphers`` lists.

    Returns:
        List of matching vulnerability findings.
    """
    findings: List[Dict[str, object]] = []
    findings.extend(match_protocol_vulns(tls_data.get("supported_versions") or []))
    findings.extend(match_cipher_vulns(tls_data.get("supported_ciphers") or []))
    return findings


def match_ssl_vulns(ssl_data: dict) -> List[Dict[str, object]]:
    """Check ``ssl`` command output for certificate weaknesses.

    Args:
        ssl_data: Results dictionary from ``run_ssl`` with a ``cert`` key.

    Returns:
        List of matching vulnerability findings.
    """
    return match_certificate_vulns(ssl_data.get("cert") or {})


def run_vuln(
    target: str,
    ports: Optional[List[int]] = None,
    timeout: float = DEFAULT_TIMEOUT,
    max_workers: int = DEFAULT_WORKERS,
    services: Optional[dict] = None,
    tls: Optional[dict] = None,
    certificate: Optional[dict] = None,
    severity: Optional[str] = None,
) -> Dict[str, object]:
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

    Returns:
        Structured results with matched findings, counts, and notes.
    """
    host = _normalize_host(target)

    if services is None:
        services = run_service(
            host, ports=ports, timeout=timeout, max_workers=max_workers
        )

    findings: List[Dict[str, object]] = []
    services_checked = 0
    for entry in services.get("results") or []:
        banner = entry.get("banner") or ""
        product, version = parse_banner(banner)
        findings.extend(
            match_service_vulns(product, version, port=entry.get("port"))
        )
        services_checked += 1

    tls_checked = tls is not None
    if tls:
        findings.extend(match_tls_vulns(tls))

    certificate_checked = certificate is not None
    if certificate:
        findings.extend(match_ssl_vulns(certificate))

    if severity:
        findings = [f for f in findings if f["severity"] == severity]

    severity_counts: Dict[str, int] = {name: 0 for name in SEVERITIES}
    for finding in findings:
        level = str(finding["severity"])
        severity_counts[level] = severity_counts.get(level, 0) + 1

    notes: List[str] = []
    if services_checked == 0:
        notes.append("No service banners detected")
    if not findings:
        notes.append("No known vulnerabilities matched")

    return {
        "target": target,
        "host": host,
        "timeout": timeout,
        "ports": ports,
        "services_checked": services_checked,
        "tls_checked": tls_checked,
        "certificate_checked": certificate_checked,
        "severity_filter": severity,
        "findings": findings,
        "finding_count": len(findings),
        "severity_counts": severity_counts,
        "notes": notes,
    }


def format_vuln_report_json(data: Dict[str, object]) -> str:
    """Format vulnerability check results as JSON."""
    return json.dumps(data, indent=2, default=str)


def _finding_detail(finding: Dict[str, object]) -> str:
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


def format_vuln_report_markdown(data: Dict[str, object]) -> str:
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

    return "\n".join(lines)
