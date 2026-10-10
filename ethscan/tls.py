"""TLS protocol/cipher enumeration module for ethscan."""

import json
import socket
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Union


DEFAULT_PORT = 443
DEFAULT_TIMEOUT = 5.0
DEFAULT_WORKERS = 10
ERROR_MAX_LENGTH = 200

TLS_VERSIONS = [
    ssl.TLSVersion.TLSv1,
    ssl.TLSVersion.TLSv1_1,
    ssl.TLSVersion.TLSv1_2,
    ssl.TLSVersion.TLSv1_3,
]

VERSION_ALIASES = {
    "ssl3": ssl.TLSVersion.SSLv3,
    "tls1": ssl.TLSVersion.TLSv1,
    "tls1.0": ssl.TLSVersion.TLSv1,
    "tlsv1": ssl.TLSVersion.TLSv1,
    "tls1_1": ssl.TLSVersion.TLSv1_1,
    "tls1.1": ssl.TLSVersion.TLSv1_1,
    "tlsv1_1": ssl.TLSVersion.TLSv1_1,
    "tlsv1.1": ssl.TLSVersion.TLSv1_1,
    "tls1_2": ssl.TLSVersion.TLSv1_2,
    "tls1.2": ssl.TLSVersion.TLSv1_2,
    "tlsv1_2": ssl.TLSVersion.TLSv1_2,
    "tlsv1.2": ssl.TLSVersion.TLSv1_2,
    "tls1_3": ssl.TLSVersion.TLSv1_3,
    "tls1.3": ssl.TLSVersion.TLSv1_3,
    "tlsv1_3": ssl.TLSVersion.TLSv1_3,
    "tlsv1.3": ssl.TLSVersion.TLSv1_3,
}

OBSOLETE_VERSIONS = {"SSLv3", "TLSv1", "TLSv1_1"}

COMMON_CIPHERS = [
    "AES128-SHA",
    "AES256-SHA",
    "AES128-SHA256",
    "AES256-SHA256",
    "AES128-GCM-SHA256",
    "AES256-GCM-SHA384",
    "ECDHE-RSA-AES128-SHA",
    "ECDHE-RSA-AES256-SHA",
    "ECDHE-RSA-AES128-SHA256",
    "ECDHE-RSA-AES256-SHA384",
    "ECDHE-RSA-AES128-GCM-SHA256",
    "ECDHE-RSA-AES256-GCM-SHA384",
    "ECDHE-ECDSA-AES128-GCM-SHA256",
    "ECDHE-ECDSA-AES256-GCM-SHA384",
    "DHE-RSA-AES128-GCM-SHA256",
    "DHE-RSA-AES256-GCM-SHA384",
]

VersionSpec = Union[str, ssl.TLSVersion]


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


def _version_name(version: VersionSpec) -> str:
    """Return the canonical name of a TLS version spec."""
    if isinstance(version, ssl.TLSVersion):
        return version.name
    return str(version)


def _resolve_version(spec: VersionSpec) -> ssl.TLSVersion:
    """Resolve a TLS version spec to an ``ssl.TLSVersion`` member.

    Args:
        spec: An ``ssl.TLSVersion`` member or a string alias
            (e.g. "TLSv1_2", "tls1.2", "TLSv1").

    Returns:
        The corresponding ``ssl.TLSVersion`` member.

    Raises:
        ValueError: If the spec does not name a known TLS version.
    """
    if isinstance(spec, ssl.TLSVersion):
        return spec
    key = str(spec).strip().lower()
    if key in VERSION_ALIASES:
        return VERSION_ALIASES[key]
    raise ValueError(f"unknown TLS version: {spec!r}")


def _resolve_versions(specs: List[VersionSpec]) -> List[ssl.TLSVersion]:
    """Resolve a list of TLS version specs, raising for unknown names.

    Raises:
        ValueError: If any spec does not name a known TLS version.
    """
    resolved: List[ssl.TLSVersion] = []
    unknown: List[str] = []
    for spec in specs:
        try:
            resolved.append(_resolve_version(spec))
        except ValueError:
            unknown.append(str(spec))
    if unknown:
        valid = ", ".join(version.name for version in TLS_VERSIONS)
        raise ValueError(
            f"Unknown TLS versions: {', '.join(unknown)}. Valid versions: {valid}"
        )
    return resolved


def _build_context(
    version: Optional[ssl.TLSVersion] = None,
    cipher: Optional[str] = None,
) -> ssl.SSLContext:
    """Build an SSL context pinned to an optional version and/or cipher.

    Args:
        version: TLS version to pin (min and max), or None for any.
        cipher: OpenSSL cipher string to restrict to, or None for defaults.

    Returns:
        An SSL context with certificate verification disabled.
    """
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    if version is not None:
        context.minimum_version = version
        context.maximum_version = version
    if cipher is not None:
        context.set_ciphers(cipher)
    return context


def _probe(host: str, port: int, context: ssl.SSLContext, timeout: float):
    """Perform a TLS handshake with the given context.

    Args:
        host: Target hostname or IP address.
        port: Target port.
        context: SSL context to use for the handshake.
        timeout: Connection and handshake timeout in seconds.

    Returns:
        Tuple of (negotiated_cipher_name, negotiated_protocol), either of
        which may be None when the server does not report them.

    Raises:
        ssl.SSLError: When the handshake fails.
        OSError: When the connection cannot be established.
    """
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        with context.wrap_socket(sock, server_hostname=host) as ssock:
            cipher = ssock.cipher()
            if cipher:
                return cipher[0], cipher[1]
            return None, None


def _truncate(message: str, limit: int = ERROR_MAX_LENGTH) -> str:
    """Truncate an error message to a bounded length."""
    if len(message) <= limit:
        return message
    return message[: limit - 3] + "..."


def probe_version(
    host: str,
    port: int,
    version: VersionSpec,
    timeout: float = DEFAULT_TIMEOUT,
) -> Dict[str, object]:
    """Test whether a single TLS protocol version is supported.

    Args:
        host: Target hostname or IP address.
        port: Target port.
        version: TLS version to test (string alias or ``ssl.TLSVersion``).
        timeout: Connection timeout in seconds.

    Returns:
        Result dict with version name, supported flag, negotiated
        cipher/protocol, and any error encountered.
    """
    entry: Dict[str, object] = {
        "version": _version_name(version),
        "supported": False,
        "error": None,
        "negotiated_cipher": None,
        "negotiated_protocol": None,
    }
    try:
        resolved = _resolve_version(version)
        context = _build_context(version=resolved)
        cipher_name, protocol = _probe(host, port, context, timeout)
        entry["supported"] = True
        entry["negotiated_cipher"] = cipher_name
        entry["negotiated_protocol"] = protocol
    except ValueError as exc:
        entry["error"] = str(exc)
    except ssl.SSLError as exc:
        entry["error"] = _truncate(str(exc))
    except (OSError, socket.error) as exc:
        entry["error"] = _truncate(str(exc))
    return entry


def probe_cipher(
    host: str,
    port: int,
    cipher: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> Dict[str, object]:
    """Test whether a single cipher suite is supported.

    Args:
        host: Target hostname or IP address.
        port: Target port.
        cipher: OpenSSL cipher suite name (e.g. "AES128-GCM-SHA256").
        timeout: Connection timeout in seconds.

    Returns:
        Result dict with cipher name, supported flag, negotiated
        protocol version, and any error encountered.
    """
    entry: Dict[str, object] = {
        "cipher": cipher,
        "supported": False,
        "error": None,
        "negotiated_version": None,
    }
    try:
        context = _build_context(cipher=cipher)
        _, protocol = _probe(host, port, context, timeout)
        entry["supported"] = True
        entry["negotiated_version"] = protocol
    except ssl.SSLError as exc:
        entry["error"] = _truncate(str(exc))
    except (OSError, socket.error) as exc:
        entry["error"] = _truncate(str(exc))
    return entry


def _version_sort_key(name: str) -> int:
    """Sort key preserving the canonical TLS version order."""
    names = [version.name for version in TLS_VERSIONS]
    return names.index(name) if name in names else len(names)


def _cipher_sort_key(name: str) -> int:
    """Sort key preserving the default cipher list order."""
    return COMMON_CIPHERS.index(name) if name in COMMON_CIPHERS else len(COMMON_CIPHERS)


def enumerate_tls(
    host: str,
    port: int = DEFAULT_PORT,
    timeout: float = DEFAULT_TIMEOUT,
    versions: Optional[List[VersionSpec]] = None,
    ciphers: Optional[List[str]] = None,
    max_workers: int = DEFAULT_WORKERS,
) -> Dict[str, object]:
    """Enumerate supported TLS protocol versions and cipher suites.

    Args:
        host: Target hostname or IP address.
        port: TLS port (default: 443).
        timeout: Connection timeout in seconds.
        versions: TLS versions to test. If None, uses TLS_VERSIONS.
        ciphers: Cipher suites to test. If None, uses COMMON_CIPHERS.
        max_workers: Maximum number of concurrent probes.

    Returns:
        Structured results with per-version and per-cipher probe results,
        supported version/cipher summaries, and security notes.

    Raises:
        ValueError: If an unknown TLS version name is provided.
    """
    resolved_versions = (
        list(TLS_VERSIONS) if versions is None else _resolve_versions(versions)
    )
    cipher_list = list(COMMON_CIPHERS) if ciphers is None else list(ciphers)

    version_results: List[Dict[str, object]] = []
    cipher_results: List[Dict[str, object]] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        version_futures = {
            executor.submit(probe_version, host, port, version, timeout): version
            for version in resolved_versions
        }
        for future in as_completed(version_futures):
            version_results.append(future.result())
        version_results.sort(key=lambda r: _version_sort_key(str(r["version"])))

        cipher_futures = {
            executor.submit(probe_cipher, host, port, cipher, timeout): cipher
            for cipher in cipher_list
        }
        for future in as_completed(cipher_futures):
            cipher_results.append(future.result())
        cipher_results.sort(key=lambda r: _cipher_sort_key(str(r["cipher"])))

    supported_versions = [
        str(result["version"]) for result in version_results if result["supported"]
    ]
    supported_ciphers = [
        str(result["cipher"]) for result in cipher_results if result["supported"]
    ]

    notes: List[str] = []
    for name in supported_versions:
        if name in OBSOLETE_VERSIONS:
            notes.append(f"Obsolete protocol version supported: {name}")
    if supported_versions and not supported_ciphers:
        notes.append("Protocol versions supported but no tested cipher succeeded")

    return {
        "target": host,
        "host": host,
        "port": port,
        "timeout": timeout,
        "versions_tested": len(version_results),
        "ciphers_tested": len(cipher_results),
        "versions": version_results,
        "ciphers": cipher_results,
        "supported_versions": supported_versions,
        "supported_ciphers": supported_ciphers,
        "supported_version_count": len(supported_versions),
        "supported_cipher_count": len(supported_ciphers),
        "notes": notes,
    }


def run_tls(
    target: str,
    port: int = DEFAULT_PORT,
    timeout: float = DEFAULT_TIMEOUT,
    versions: Optional[List[VersionSpec]] = None,
    ciphers: Optional[List[str]] = None,
    max_workers: int = DEFAULT_WORKERS,
) -> Dict[str, object]:
    """Enumerate supported TLS protocol versions and cipher suites for ``target``.

    Args:
        target: Hostname or URL (e.g. example.com or https://example.com).
        port: TLS port (default: 443).
        timeout: Connection timeout in seconds.
        versions: TLS versions to test. If None, uses TLS_VERSIONS.
        ciphers: Cipher suites to test. If None, uses COMMON_CIPHERS.
        max_workers: Maximum number of concurrent probes.

    Returns:
        Structured results with target, host, port, and enumeration data.

    Raises:
        ValueError: If an unknown TLS version name is provided.
    """
    host = _normalize_host(target)
    data = enumerate_tls(
        host,
        port=port,
        timeout=timeout,
        versions=versions,
        ciphers=ciphers,
        max_workers=max_workers,
    )
    data["host"] = host
    data["target"] = target
    return data


def format_tls_report_json(data: Dict[str, object]) -> str:
    """Format TLS enumeration results as JSON."""
    return json.dumps(data, indent=2, default=str)


def format_tls_report_markdown(data: Dict[str, object]) -> str:
    """Format TLS enumeration results as Markdown."""
    lines = ["# ethscan TLS Enumeration Report", ""]
    lines.append(f"- **Target:** {data['target']}")
    lines.append(f"- **Host:** {data['host']}")
    lines.append(f"- **Port:** {data['port']}")
    lines.append(f"- **Versions Tested:** {data.get('versions_tested', 0)}")
    lines.append(f"- **Ciphers Tested:** {data.get('ciphers_tested', 0)}")
    supported_versions = data.get("supported_versions") or []
    lines.append(
        f"- **Supported Versions:** "
        f"{', '.join(supported_versions) if supported_versions else 'None'}"
    )
    lines.append(f"- **Supported Ciphers:** {data.get('supported_cipher_count', 0)}")
    lines.append("")

    notes = data.get("notes") or []
    if notes:
        lines.append("## Findings")
        for note in notes:
            lines.append(f"- {note}")
        lines.append("")

    lines.append("## Protocol Versions")
    versions = data.get("versions") or []
    if versions:
        lines.append("| Version | Supported | Negotiated Cipher | Negotiated Protocol | Error |")
        lines.append("|---------|-----------|-------------------|---------------------|-------|")
        for result in versions:
            supported = "Yes" if result["supported"] else "No"
            cipher_name = result.get("negotiated_cipher") or ""
            protocol = result.get("negotiated_protocol") or ""
            error = (result.get("error") or "").replace("|", "\\|")
            error = _truncate(error, 60)
            lines.append(
                f"| {result['version']} | {supported} | {cipher_name} | {protocol} | {error} |"
            )
    else:
        lines.append("*No protocol versions tested.*")
    lines.append("")

    lines.append("## Cipher Suites")
    ciphers = data.get("ciphers") or []
    if ciphers:
        lines.append("| Cipher | Supported | Negotiated Version | Error |")
        lines.append("|--------|-----------|--------------------|-------|")
        for result in ciphers:
            supported = "Yes" if result["supported"] else "No"
            protocol = result.get("negotiated_version") or ""
            error = (result.get("error") or "").replace("|", "\\|")
            error = _truncate(error, 60)
            lines.append(f"| {result['cipher']} | {supported} | {protocol} | {error} |")
    else:
        lines.append("*No cipher suites tested.*")
    lines.append("")

    return "\n".join(lines)
