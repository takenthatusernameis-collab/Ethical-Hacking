"""SSL/TLS certificate inspection module for ethscan."""

import json
import socket
import ssl
from typing import Dict, List, Optional

DEFAULT_PORT = 443
DEFAULT_TIMEOUT = 5.0


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


def _rdn_to_str(rdn: dict) -> str:
    """Render an RDN dict as a comma-separated string."""
    parts = []
    for key, value in rdn.items():
        parts.append(f"{key}={value}")
    return ", ".join(parts)


def _estimate_key_size(public_key_info) -> Optional[int]:
    """Best-effort estimate of the public key size in bits."""
    try:
        if isinstance(public_key_info, dict):
            bits = public_key_info.get("bits")
            if bits:
                return int(bits)
            size = public_key_info.get("size")
            if size:
                return int(size) * 8
        return None
    except (TypeError, ValueError):
        return None


def _parse_cert(cert: dict) -> dict:
    """Parse a dict-form certificate into a structured dictionary.

    Args:
        cert: Certificate dict as returned by ``SSLSocket.getpeercert()``.

    Returns:
        Structured certificate data: subject, issuer, SANs, validity dates,
        signature algorithm, and key size.
    """
    subject_dict = dict(
        item[0]
        for item in cert.get("subject", ())
        if isinstance(item, tuple) and len(item) >= 1
    )
    issuer_dict = dict(
        item[0]
        for item in cert.get("issuer", ())
        if isinstance(item, tuple) and len(item) >= 1
    )

    subject = subject_dict.get("commonName") or _rdn_to_str(subject_dict) or None
    issuer = issuer_dict.get("commonName") or _rdn_to_str(issuer_dict) or None

    san_list = []
    for ext in cert.get("subjectAltName", ()):
        if isinstance(ext, tuple) and len(ext) == 2 and ext[0] == "DNS":
            san_list.append(ext[1])

    not_before = cert.get("notBefore")
    not_after = cert.get("notAfter")

    signature_algorithm = cert.get("signatureAlgorithm")
    if signature_algorithm and isinstance(signature_algorithm, tuple):
        signature_algorithm = signature_algorithm[0]

    key_size = _estimate_key_size(cert.get("publicKeyInfo"))

    return {
        "subject": subject,
        "subject_dict": subject_dict,
        "issuer": issuer,
        "issuer_dict": issuer_dict,
        "sans": sorted(set(san_list)),
        "not_before": not_before,
        "not_after": not_after,
        "signature_algorithm": signature_algorithm,
        "key_size": key_size,
    }


def _wrap_socket(context, host, port, timeout):
    """Wrap a TCP connection with the given SSL context and return the socket.

    Args:
        context: SSL context to use.
        host: Target hostname.
        port: Target port.
        timeout: Connection timeout in seconds.

    Returns:
        Tuple of (wrapped_socket, cert_dict_or_None).
    """
    with socket.create_connection((host, port), timeout=timeout) as sock:
        with context.wrap_socket(sock, server_hostname=host) as ssock:
            cert = _decode_cert(ssock)
            chain = _get_chain(ssock)
            return ssock, cert, len(chain) if chain else 0


def _decode_cert(ssock) -> dict:
    """Decode the peer certificate from an SSL socket into a dict.

    Falls back to ``getpeercert()`` when DER decoding is unavailable.
    """
    cert_bin = ssock.getpeercert(True)
    if cert_bin:
        pem = ssl.DER_cert_to_PEM_cert(cert_bin)
        import os
        import tempfile

        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".pem") as handle:
            handle.write(pem)
            cert_path = handle.name
        try:
            return ssl._ssl._test_decode_cert(cert_path)
        except (ValueError, OSError, ssl.SSLError):
            return ssock.getpeercert() or {}
        finally:
            os.unlink(cert_path)
    return ssock.getpeercert() or {}


def _get_chain(ssock) -> list:
    """Return the verified certificate chain if available, else an empty list."""
    for method_name in ("get_verified_chain", "get_unverified_chain"):
        method = getattr(ssock, method_name, None)
        if method is not None:
            try:
                chain = method()
                if chain:
                    return chain
            except Exception:  # pragma: no cover - defensive
                continue
    return []


def _build_context(verify: bool):
    """Build an SSL context, optionally skipping certificate verification."""
    if verify:
        return ssl.create_default_context()
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def inspect_certificate(
    host: str,
    port: int = DEFAULT_PORT,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict:
    """Connect to ``host``:``port`` over TLS and inspect the certificate.

    Args:
        host: Target hostname or IP address.
        port: TLS port (default: 443).
        timeout: Connection timeout in seconds.

    Returns:
        Structured results with target, port, parsed certificate fields,
        chain length, validity status, and any error encountered.
    """
    result: dict = {
        "target": host,
        "port": port,
        "timeout": timeout,
        "error": None,
        "chain_length": 0,
        "cert": None,
        "valid": False,
        "days_remaining": None,
    }

    try:
        # First attempt: verify the certificate chain.
        context = _build_context(verify=True)
        try:
            _, cert, chain_length = _wrap_socket(context, host, port, timeout)
            result["chain_length"] = chain_length
        except ssl.SSLError as exc:
            # Verification failed; retry without verification to still inspect the cert.
            result["error"] = str(exc)
            context = _build_context(verify=False)
            _, cert, _ = _wrap_socket(context, host, port, timeout)

        if cert:
            result["cert"] = _parse_cert(cert)
            not_after = cert.get("notAfter")
            if not_after:
                from datetime import datetime

                try:
                    expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                    result["days_remaining"] = (expiry - datetime.utcnow()).days
                    result["valid"] = result["days_remaining"] > 0
                except (ValueError, TypeError):
                    result["valid"] = False
    except (ssl.SSLError, socket.error, OSError, ValueError) as exc:
        result["error"] = str(exc)
    return result


def run_ssl(
    target: str,
    port: int = DEFAULT_PORT,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict:
    """Inspect the SSL/TLS certificate for ``target``.

    Args:
        target: Hostname or URL (e.g. example.com or https://example.com).
        port: TLS port (default: 443).
        timeout: Connection timeout in seconds.

    Returns:
        Structured results with target, host, port, and certificate data.
    """
    host = _normalize_host(target)
    data = inspect_certificate(host, port=port, timeout=timeout)
    data["host"] = host
    data["target"] = target
    return data


def format_ssl_report_json(data: dict) -> str:
    """Format SSL results as JSON."""
    return json.dumps(data, indent=2, default=str)


def format_ssl_report_markdown(data: dict) -> str:
    """Format SSL results as Markdown."""
    lines = ["# ethscan SSL/TLS Certificate Report", ""]
    lines.append(f"- **Target:** {data['target']}")
    lines.append(f"- **Host:** {data['host']}")
    lines.append(f"- **Port:** {data['port']}")
    lines.append("")

    if data.get("error"):
        lines.append(f"- **Error:** {data['error']}")
        lines.append("")

    cert = data.get("cert") or {}
    if cert:
        lines.append("## Certificate")
        lines.append(f"- **Valid:** {'Yes' if data.get('valid') else 'No'}")
        if cert.get("subject"):
            lines.append(f"- **Subject:** {cert['subject']}")
        if cert.get("issuer"):
            lines.append(f"- **Issuer:** {cert['issuer']}")
        if cert.get("not_before"):
            lines.append(f"- **Not Before:** {cert['not_before']}")
        if cert.get("not_after"):
            lines.append(f"- **Not After:** {cert['not_after']}")
        if cert.get("signature_algorithm"):
            lines.append(f"- **Signature Algorithm:** {cert['signature_algorithm']}")
        if cert.get("key_size"):
            lines.append(f"- **Key Size:** {cert['key_size']} bits")
        if cert.get("sans"):
            lines.append("- **Subject Alternative Names:**")
            for san in cert["sans"]:
                lines.append(f"  - {san}")
        lines.append(f"- **Chain Length:** {data.get('chain_length', 0)}")
        lines.append("")
    elif not data.get("error"):
        lines.append("## Certificate")
        lines.append("*No certificate retrieved.*")
        lines.append("")

    return "\n".join(lines)