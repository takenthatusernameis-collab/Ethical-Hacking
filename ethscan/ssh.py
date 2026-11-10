"""SSH security assessment module for ethscan."""
from __future__ import annotations

import contextlib
import csv
import io
import json
import socket
import struct
from typing import Any, TypedDict

from ethscan.target import parse_url, url_port, normalize_host

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False


class SshAlgorithms(TypedDict):
    """Algorithm analysis result for a category."""

    supported: list[str]
    weak: list[str]
    strong: list[str]


class SshHostKey(TypedDict, total=False):
    """Host key information."""

    fingerprint: str
    key_type: str
    key_bits: int | None


class SshFinding(TypedDict):
    """Security finding in SSH assessment."""

    type: str
    algorithm: str
    severity: str
    description: str


class SshResult(TypedDict):
    """Complete result from run_ssh."""

    target: str
    host: str
    port: int
    timeout: float
    banner: str | None
    paramiko_available: bool
    kex_algorithms: SshAlgorithms
    host_key_algorithms: SshAlgorithms
    encryption_algorithms: SshAlgorithms
    mac_algorithms: SshAlgorithms
    host_key: SshHostKey | None
    findings: list[SshFinding]
    error: str | None

DEFAULT_PORT = 22
DEFAULT_TIMEOUT = 10.0

WEAK_KEX_ALGORITHMS = {
    "diffie-hellman-group1-sha1",
    "diffie-hellman-group14-sha1",
    "diffie-hellman-group-exchange-sha1",
}

WEAK_CIPHERS = {
    "3des-cbc",
    "aes128-cbc",
    "aes192-cbc",
    "aes256-cbc",
    "arcfour",
    "arcfour128",
    "arcfour256",
    "blowfish-cbc",
    "cast128-cbc",
    "rijndael-cbc@lysator.liu.se",
}

WEAK_MACS = {
    "hmac-md5",
    "hmac-md5-96",
    "hmac-sha1",
    "hmac-sha1-96",
    "hmac-sha2-256",
    "hmac-sha2-512",
}

WEAK_HOST_KEY_TYPES = {
    "ssh-dss",
    "ssh-rsa",
}

STRONG_KEX_ALGORITHMS = {
    "curve25519-sha256",
    "curve25519-sha256@libssh.org",
    "diffie-hellman-group16-sha512",
    "diffie-hellman-group18-sha512",
    "diffie-hellman-group-exchange-sha256",
    "ecdh-sha2-nistp256",
    "ecdh-sha2-nistp384",
    "ecdh-sha2-nistp521",
}

STRONG_CIPHERS = {
    "aes128-ctr",
    "aes192-ctr",
    "aes256-ctr",
    "aes128-gcm@openssh.com",
    "aes256-gcm@openssh.com",
    "chacha20-poly1305@openssh.com",
}

STRONG_MACS = {
    "hmac-sha2-256-etm@openssh.com",
    "hmac-sha2-512-etm@openssh.com",
    "umac-64-etm@openssh.com",
    "umac-128-etm@openssh.com",
}

STRONG_HOST_KEY_TYPES = {
    "ecdsa-sha2-nistp256",
    "ecdsa-sha2-nistp384",
    "ecdsa-sha2-nistp521",
    "ssh-ed25519",
    "rsa-sha2-256",
    "rsa-sha2-512",
}


def _normalize_host(target: str) -> str:
    """Extract a bare hostname from a target that may be a URL or host:port.

    Args:
        target: Bare host (e.g. ssh.example.com) or URL (e.g. ssh://user@host:22/).

    Returns:
        Lowercased hostname without scheme, path, or credentials.
    """
    return normalize_host(target, default_scheme="ssh://")


def _extract_port(target: str, default: int = DEFAULT_PORT) -> int:
    """Extract port from target if present."""
    if "://" not in target:
        target = "ssh://" + target
    parsed = parse_url(target)
    return url_port(parsed) or default


def _ssh_banner_exchange(sock: socket.socket, timeout: float) -> str | None:
    """Perform SSH banner exchange and return server banner."""
    sock.settimeout(timeout)
    try:
        banner = sock.recv(1024).decode("ascii", errors="ignore").strip()
        if banner.startswith("SSH-"):
            return banner
    except (socket.timeout, OSError, UnicodeDecodeError):
        pass
    except Exception:  # noqa: BLE001, S110 - transport can raise any type
        pass
    return None


def _parse_ssh_banner(banner: str) -> dict[str, Any]:
    """Parse an SSH protocol banner into its component fields.

    The banner has the form ``SSH-protoversion-softwareversion-sp[comments]``
    (RFC 4253), e.g. ``SSH-2.0-OpenSSH_8.9 Ubuntu-3ubuntu0.6``.

    Returns a dict with ``protocol_version``, ``software_version``,
    ``software_name``, and ``comments``; any field that could not be parsed
    is ``None``.
    """
    result: dict[str, Any] = {
        "protocol_version": None,
        "software_version": None,
        "software_name": None,
        "comments": None,
    }
    if not banner:
        return result
    # Split on the first two dashes; the remainder (which may itself contain
    # dashes, e.g. "OpenSSH_8.9 Ubuntu-3ubuntu0.6") holds the software
    # version followed by optional comments.
    parts = banner.split("-", 2)
    if len(parts) < 3:
        return result
    result["protocol_version"] = parts[1] or None
    remainder = parts[2].strip()
    if not remainder:
        return result
    # The software version is the first whitespace-separated token; anything
    # after it is a comment (and may itself contain dashes).
    software, _, comments = remainder.partition(" ")
    result["comments"] = comments or None
    if "_" in software:
        name, _, version = software.partition("_")
        result["software_name"] = name or None
        result["software_version"] = version or None
    else:
        result["software_name"] = software or None  # pragma: no cover - defensive
    return result


def _assess_ssh_banner(banner: str) -> list[dict[str, Any]]:
    """Assess an SSH banner and return structured security findings.

    Currently flags out-of-support OpenSSH server versions. OpenSSH 8.4
    (released January 2022) is the cutoff: earlier releases no longer
    receive security fixes.
    """
    findings: list[dict[str, Any]] = []
    parsed = _parse_ssh_banner(banner)
    software_name = parsed.get("software_name")
    version = parsed.get("software_version")
    if not (software_name and version):
        return findings
    if software_name.lower() != "openssh":
        return findings
    try:
        # OpenSSH versions are ``major.minor`` (e.g. ``8.9`` or ``9.3p1``);
        # strip any non-numeric suffix before comparing.
        numeric = "".join(ch for ch in version if ch.isdigit() or ch == ".")
        major, minor = (int(x) for x in numeric.split(".")[:2])
        if (major, minor) < (8, 4):
            findings.append(
                {
                    "type": "old_ssh_version",
                    "algorithm": f"OpenSSH_{version}",
                    "severity": "high",
                    "description": (
                        f"Old OpenSSH server version detected ({version}; "
                        "major < 8.4, out of support and may lack security features)"
                    ),
                }
            )
    except (ValueError, AttributeError, IndexError):
        pass
    return findings


def _send_kexinit(sock: socket.socket) -> None:
    """Send a minimal SSH_MSG_KEXINIT packet to trigger server's algorithm list."""
    cookie = b"\x00" * 16

    def name_list(names: list[str]) -> bytes:
        data = ",".join(names).encode("ascii")
        return struct.pack(">I", len(data)) + data

    kex_algos = [
        "curve25519-sha256",
        "curve25519-sha256@libssh.org",
        "ecdh-sha2-nistp256",
        "ecdh-sha2-nistp384",
        "ecdh-sha2-nistp521",
        "diffie-hellman-group16-sha512",
        "diffie-hellman-group18-sha512",
        "diffie-hellman-group-exchange-sha256",
        "diffie-hellman-group14-sha256",
        "diffie-hellman-group14-sha1",
        "diffie-hellman-group1-sha1",
        "diffie-hellman-group-exchange-sha1",
    ]

    server_host_key_algos = [
        "ssh-ed25519",
        "rsa-sha2-256",
        "rsa-sha2-512",
        "ecdsa-sha2-nistp256",
        "ecdsa-sha2-nistp384",
        "ecdsa-sha2-nistp521",
        "ssh-rsa",
        "ssh-dss",
    ]

    encryption_algos = [
        "aes128-ctr",
        "aes192-ctr",
        "aes256-ctr",
        "aes128-gcm@openssh.com",
        "aes256-gcm@openssh.com",
        "chacha20-poly1305@openssh.com",
        "aes128-cbc",
        "aes192-cbc",
        "aes256-cbc",
        "3des-cbc",
        "arcfour",
        "arcfour128",
        "arcfour256",
        "blowfish-cbc",
        "cast128-cbc",
    ]

    mac_algos = [
        "hmac-sha2-256-etm@openssh.com",
        "hmac-sha2-512-etm@openssh.com",
        "umac-64-etm@openssh.com",
        "umac-128-etm@openssh.com",
        "hmac-sha2-256",
        "hmac-sha2-512",
        "hmac-sha1",
        "hmac-sha1-96",
        "hmac-md5",
        "hmac-md5-96",
    ]

    compression_algos = ["none"]
    languages = [""]

    payload = b"\x14"  # SSH_MSG_KEXINIT
    payload += cookie
    payload += name_list(kex_algos)
    payload += name_list(server_host_key_algos)
    payload += name_list(encryption_algos)
    payload += name_list(encryption_algos)
    payload += name_list(mac_algos)
    payload += name_list(mac_algos)
    payload += name_list(compression_algos)
    payload += name_list(compression_algos)
    payload += name_list(languages)
    payload += name_list(languages)
    payload += b"\x00"  # first_kex_packet_follows
    payload += struct.pack(">I", 0)  # reserved

    packet_len = struct.pack(">I", len(payload))
    sock.sendall(packet_len + payload)


def _read_packet(sock: socket.socket) -> bytes | None:
    """Read a single SSH packet and return its payload."""
    try:
        length_bytes = sock.recv(4)
        if len(length_bytes) < 4:
            return None
        length = struct.unpack(">I", length_bytes)[0]
        if length > 35000:  # Max packet size per RFC 4253
            return None
        payload = b""
        while len(payload) < length:
            chunk = sock.recv(length - len(payload))
            if not chunk:
                return None
            payload += chunk
        # Skip padding length byte
        if len(payload) > 0:
            return payload[1:]
    except (socket.timeout, OSError, struct.error):
        pass
    except Exception:  # noqa: BLE001, S110 - transport can raise any type
        pass
    return None


def _parse_kexinit(payload: bytes) -> dict[str, list[str]]:
    """Parse SSH_MSG_KEXINIT payload and extract algorithm lists."""
    if len(payload) < 17:  # msg_type(1) + cookie(16)
        return {}

    offset = 17  # Skip msg_type + cookie
    results = {}
    keys = [
        "kex_algorithms",
        "server_host_key_algorithms",
        "encryption_algorithms_client_to_server",
        "encryption_algorithms_server_to_client",
        "mac_algorithms_client_to_server",
        "mac_algorithms_server_to_client",
        "compression_algorithms_client_to_server",
        "compression_algorithms_server_to_client",
        "languages_client_to_server",
        "languages_server_to_client",
    ]

    for key in keys:
        if offset + 4 > len(payload):
            break
        length = struct.unpack(">I", payload[offset : offset + 4])[0]
        offset += 4
        if offset + length > len(payload):
            break
        data = payload[offset : offset + length].decode("ascii", errors="ignore")
        offset += length
        results[key] = [x for x in data.split(",") if x]

    return results


def _analyze_algorithms(algorithms: dict[str, list[str]]) -> dict[str, Any]:
    """Analyze algorithm lists for weak/deprecated algorithms."""
    kex = algorithms.get("kex_algorithms", [])
    host_keys = algorithms.get("server_host_key_algorithms", [])
    ciphers_c2s = algorithms.get("encryption_algorithms_client_to_server", [])
    ciphers_s2c = algorithms.get("encryption_algorithms_server_to_client", [])
    macs_c2s = algorithms.get("mac_algorithms_client_to_server", [])
    macs_s2c = algorithms.get("mac_algorithms_server_to_client", [])

    all_ciphers = list(set(ciphers_c2s + ciphers_s2c))
    all_macs = list(set(macs_c2s + macs_s2c))

    findings = {
        "kex_algorithms": {
            "supported": kex,
            "weak": [a for a in kex if a in WEAK_KEX_ALGORITHMS],
            "strong": [a for a in kex if a in STRONG_KEX_ALGORITHMS],
        },
        "host_key_algorithms": {
            "supported": host_keys,
            "weak": [a for a in host_keys if a in WEAK_HOST_KEY_TYPES],
            "strong": [a for a in host_keys if a in STRONG_HOST_KEY_TYPES],
        },
        "encryption_algorithms": {
            "supported": all_ciphers,
            "weak": [a for a in all_ciphers if a in WEAK_CIPHERS],
            "strong": [a for a in all_ciphers if a in STRONG_CIPHERS],
        },
        "mac_algorithms": {
            "supported": all_macs,
            "weak": [a for a in all_macs if a in WEAK_MACS],
            "strong": [a for a in all_macs if a in STRONG_MACS],
        },
    }

    return findings


def _get_host_key_info_paramiko(host: str, port: int, timeout: float) -> dict[str, Any] | None:
    """Get host key fingerprint and type using paramiko."""
    if not PARAMIKO_AVAILABLE:
        return None

    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        transport = paramiko.Transport(sock)
        transport.start_client()
        host_key = transport.get_remote_server_key()
        fingerprint = host_key.get_fingerprint().hex()
        key_type = host_key.get_name()
        transport.close()
        sock.close()
        return {
            "fingerprint": ":".join(fingerprint[i : i + 2] for i in range(0, len(fingerprint), 2)),
            "key_type": key_type,
            "key_bits": host_key.get_bits() if hasattr(host_key, "get_bits") else None,
        }
    except OSError:
        return None
    except Exception:  # noqa: BLE001 - paramiko raises its own SSHException type
        return None


def _get_host_key_info_stdlib(sock: socket.socket) -> dict[str, Any] | None:
    """Attempt to extract host key info from KEXINIT response (limited without full KEX)."""
    return None


def _ssh_connect(
    host: str,
    port: int,
    timeout: float,
    connector=None,
) -> socket.socket:
    """Open a TCP connection to the SSH server.

    Tests may provide a ``connector`` callable that returns a socket-like
    object to substitute for the real transport; a connector that raises is
    propagated so ``run_ssh`` can report it through its own error field.
    """
    if connector is not None:
        return connector(host, port, timeout)
    return socket.create_connection((host, port), timeout=timeout)


def run_ssh(
    target: str,
    port: int | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    connector=None,
) -> SshResult:
    """Run SSH security assessment against a target.

    Args:
        target: Target host or URL (e.g. ssh.example.com or ssh://example.com:2222).
        port: Override target port. If None, extracts from target or uses default 22.
        timeout: Connection timeout in seconds.
        connector: Callable returning a socket-like transport (for testing).

    Returns:
        Structured results with banner, supported algorithms, weak algorithm findings,
        and host key information.
    """
    host = _normalize_host(target)
    resolved_port = port if port is not None else _extract_port(target)

    result: SshResult = {
        "target": target,
        "host": host,
        "port": resolved_port,
        "timeout": timeout,
        "banner": None,
        "paramiko_available": PARAMIKO_AVAILABLE,
        "kex_algorithms": {"supported": [], "weak": [], "strong": []},
        "host_key_algorithms": {"supported": [], "weak": [], "strong": []},
        "encryption_algorithms": {"supported": [], "weak": [], "strong": []},
        "mac_algorithms": {"supported": [], "weak": [], "strong": []},
        "host_key": None,
        "findings": [],
        "error": None,
    }

    sock = None
    try:
        sock = _ssh_connect(host, resolved_port, timeout, connector)
        banner = _ssh_banner_exchange(sock, timeout)
        result["banner"] = banner

        if not banner:
            result["error"] = "No SSH banner received"
            return result

        # Flag out-of-support SSH server versions (e.g. old OpenSSH).
        for finding in _assess_ssh_banner(banner):
            result["findings"].append(finding)

        _send_kexinit(sock)
        response = _read_packet(sock)

        if response and response[0:1] == b"\x14":  # SSH_MSG_KEXINIT
            algorithms = _parse_kexinit(response)
            analysis = _analyze_algorithms(algorithms)
            result["kex_algorithms"] = analysis["kex_algorithms"]
            result["host_key_algorithms"] = analysis["host_key_algorithms"]
            result["encryption_algorithms"] = analysis["encryption_algorithms"]
            result["mac_algorithms"] = analysis["mac_algorithms"]

            for weak_kex in analysis["kex_algorithms"]["weak"]:
                result["findings"].append(
                    {
                        "type": "weak_kex",
                        "algorithm": weak_kex,
                        "severity": "medium",
                        "description": f"Weak key exchange algorithm supported: {weak_kex}",
                    }
                )
            for weak_cipher in analysis["encryption_algorithms"]["weak"]:
                result["findings"].append(
                    {
                        "type": "weak_cipher",
                        "algorithm": weak_cipher,
                        "severity": "medium",
                        "description": f"Weak encryption algorithm supported: {weak_cipher}",
                    }
                )
            for weak_mac in analysis["mac_algorithms"]["weak"]:
                result["findings"].append(
                    {
                        "type": "weak_mac",
                        "algorithm": weak_mac,
                        "severity": "medium",
                        "description": f"Weak MAC algorithm supported: {weak_mac}",
                    }
                )
            for weak_host_key in analysis["host_key_algorithms"]["weak"]:
                result["findings"].append(
                    {
                        "type": "weak_host_key",
                        "algorithm": weak_host_key,
                        "severity": "high",
                        "description": f"Weak host key type supported: {weak_host_key}",
                    }
                )

        if PARAMIKO_AVAILABLE:
            host_key_info = _get_host_key_info_paramiko(host, resolved_port, timeout)
            if host_key_info:
                result["host_key"] = host_key_info
                if host_key_info["key_type"] in WEAK_HOST_KEY_TYPES:
                    result["findings"].append(
                        {
                            "type": "weak_host_key",
                            "algorithm": host_key_info["key_type"],
                            "severity": "high",
                            "description": f"Server uses weak host key type: {host_key_info['key_type']}",
                        }
                    )

    except socket.timeout:
        result["error"] = "Connection timeout"
    except ConnectionRefusedError:
        result["error"] = "Connection refused"
    # A host that is not a valid host name ("....") raises a UnicodeError,
    # which is a ValueError, when the resolver encodes it.
    except (OSError, ValueError) as exc:
        result["error"] = f"Connection error: {exc}"
    # A hostile server must never crash the command: whatever it sends is
    # reported through the module's own failure field.
    except Exception as exc:  # noqa: BLE001 - a remote answer must not raise
        result["error"] = f"ssh probe failed: {exc}"
    finally:
        if sock:
            with contextlib.suppress(Exception):
                sock.close()

    return result


def format_ssh_report_json(data: SshResult) -> str:
    """Format SSH assessment results as JSON."""
    if not isinstance(data, dict):
        return "{}"
    return json.dumps(data, indent=2, default=str)


def format_ssh_report_markdown(data: SshResult) -> str:
    """Format SSH assessment results as Markdown."""
    if not isinstance(data, dict):
        data = {}
    lines = ["# ethscan SSH Security Assessment Report", ""]
    lines.append(f"- **Target:** {data.get('target', '')}")
    lines.append(f"- **Host:** {data.get('host', '')}")
    lines.append(f"- **Port:** {data.get('port', '')}")
    lines.append(f"- **Timeout:** {data.get('timeout', '')}s")
    lines.append(f"- **Paramiko Available:** {'Yes' if data.get('paramiko_available') else 'No (stdlib only)'}")
    lines.append("")

    if data.get("error"):
        lines.append(f"- **Error:** {data.get('error')}")
        lines.append("")
        return "\n".join(lines)

    if data.get("banner"):
        lines.append(f"- **Server Banner:** `{data.get('banner')}`")
        lines.append("")

    def render_algo_section(title: str, algo_data: dict[str, list[str]]) -> None:
        lines.append(f"## {title}")
        if not isinstance(algo_data, dict):
            algo_data = {}
        supported = algo_data.get("supported") or []
        weak = set(algo_data.get("weak") or [])
        strong = set(algo_data.get("strong") or [])
        if supported:
            lines.append("### Supported Algorithms")
            for algo in sorted(supported):
                if algo in weak:
                    lines.append(f"- **{algo}** ⚠️ (weak/deprecated)")
                elif algo in strong:
                    lines.append(f"- **{algo}** ✓ (strong)")
                else:
                    lines.append(f"- {algo}")
        else:
            lines.append("*No algorithms reported*")
        lines.append("")

    render_algo_section("Key Exchange Algorithms", data.get("kex_algorithms") or {})
    render_algo_section("Host Key Algorithms", data.get("host_key_algorithms") or {})
    render_algo_section("Encryption Algorithms", data.get("encryption_algorithms") or {})
    render_algo_section("MAC Algorithms", data.get("mac_algorithms") or {})

    host_key = data.get("host_key")
    if isinstance(host_key, dict) and host_key:
        lines.append("## Host Key")
        lines.append(f"- **Type:** {host_key.get('key_type', '')}")
        lines.append(f"- **Fingerprint (SHA256):** {host_key.get('fingerprint', '')}")
        if host_key.get("key_bits"):
            lines.append(f"- **Key Size:** {host_key.get('key_bits')} bits")
        lines.append("")

    findings_obj = data.get("findings")
    findings = list(findings_obj) if isinstance(findings_obj, (list, tuple)) else []
    if findings:
        lines.append("## Security Findings")
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            severity = str(finding.get("severity", "") or "")
            description = str(finding.get("description", "") or "")
            severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(severity, "⚪")
            lines.append(f"- {severity_icon} **[{severity.upper()}]** {description}")
        lines.append("")
    else:
        lines.append("## Security Findings")
        lines.append("*No weak algorithms detected*")
        lines.append("")

    return "\n".join(lines)
def format_ssh_report_csv(data: SshResult) -> str:
    """Format SSH security assessment results as CSV."""
    if not isinstance(data, dict):
        data = {}
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "type",
        "algorithm",
        "severity",
        "description",
    ])

    error = data.get("error")
    if error:
        writer.writerow(["error", "", "", str(error)])
        return output.getvalue().rstrip("\r\n")

    findings = data.get("findings") or []
    if not isinstance(findings, list):
        findings = []
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        writer.writerow([
            finding.get("type", ""),
            finding.get("algorithm", ""),
            finding.get("severity", ""),
            finding.get("description", ""),
        ])
    return output.getvalue().rstrip("\r\n")
