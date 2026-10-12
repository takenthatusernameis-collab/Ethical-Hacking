"""SSH security assessment module for ethscan."""

import csv
import io
import json
import socket
import struct
from typing import Any, Dict, List, Optional, Tuple

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False

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
    normalized = target.strip()
    if "://" not in normalized:
        normalized = "ssh://" + normalized
    from urllib.parse import urlparse

    parsed = urlparse(normalized)
    return (parsed.hostname or parsed.netloc or "").lower()


def _extract_port(target: str, default: int = DEFAULT_PORT) -> int:
    """Extract port from target if present."""
    if "://" not in target:
        target = "ssh://" + target
    from urllib.parse import urlparse

    parsed = urlparse(target)
    return parsed.port or default


def _ssh_banner_exchange(sock: socket.socket, timeout: float) -> Optional[str]:
    """Perform SSH banner exchange and return server banner."""
    sock.settimeout(timeout)
    try:
        banner = sock.recv(1024).decode("ascii", errors="ignore").strip()
        if banner.startswith("SSH-"):
            return banner
    except (socket.timeout, OSError, UnicodeDecodeError):
        pass
    return None


def _send_kexinit(sock: socket.socket) -> None:
    """Send a minimal SSH_MSG_KEXINIT packet to trigger server's algorithm list."""
    cookie = b"\x00" * 16

    def name_list(names: List[str]) -> bytes:
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


def _read_packet(sock: socket.socket) -> Optional[bytes]:
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
    return None


def _parse_kexinit(payload: bytes) -> Dict[str, List[str]]:
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


def _analyze_algorithms(algorithms: Dict[str, List[str]]) -> Dict[str, Any]:
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


def _get_host_key_info_paramiko(host: str, port: int, timeout: float) -> Optional[Dict[str, Any]]:
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
    except Exception:
        return None


def _get_host_key_info_stdlib(sock: socket.socket) -> Optional[Dict[str, Any]]:
    """Attempt to extract host key info from KEXINIT response (limited without full KEX)."""
    return None


def run_ssh(
    target: str,
    port: Optional[int] = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> Dict[str, Any]:
    """Run SSH security assessment against a target.

    Args:
        target: Target host or URL (e.g. ssh.example.com or ssh://example.com:2222).
        port: Override target port. If None, extracts from target or uses default 22.
        timeout: Connection timeout in seconds.

    Returns:
        Structured results with banner, supported algorithms, weak algorithm findings,
        and host key information.
    """
    host = _normalize_host(target)
    resolved_port = port if port is not None else _extract_port(target)

    result: Dict[str, Any] = {
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
        sock = socket.create_connection((host, resolved_port), timeout=timeout)
        banner = _ssh_banner_exchange(sock, timeout)
        result["banner"] = banner

        if not banner:
            result["error"] = "No SSH banner received"
            return result

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
    except OSError as exc:
        result["error"] = f"Connection error: {exc}"
    finally:
        if sock:
            try:
                sock.close()
            except Exception:
                pass

    return result


def format_ssh_report_json(data: Dict[str, Any]) -> str:
    """Format SSH assessment results as JSON."""
    return json.dumps(data, indent=2, default=str)


def format_ssh_report_markdown(data: Dict[str, Any]) -> str:
    """Format SSH assessment results as Markdown."""
    lines = ["# ethscan SSH Security Assessment Report", ""]
    lines.append(f"- **Target:** {data['target']}")
    lines.append(f"- **Host:** {data['host']}")
    lines.append(f"- **Port:** {data['port']}")
    lines.append(f"- **Timeout:** {data['timeout']}s")
    lines.append(f"- **Paramiko Available:** {'Yes' if data['paramiko_available'] else 'No (stdlib only)'}")
    lines.append("")

    if data["error"]:
        lines.append(f"- **Error:** {data['error']}")
        lines.append("")
        return "\n".join(lines)

    if data["banner"]:
        lines.append(f"- **Server Banner:** `{data['banner']}`")
        lines.append("")

    def render_algo_section(title: str, algo_data: Dict[str, List[str]]) -> None:
        lines.append(f"## {title}")
        if algo_data["supported"]:
            lines.append("### Supported Algorithms")
            for algo in sorted(algo_data["supported"]):
                if algo in algo_data["weak"]:
                    lines.append(f"- **{algo}** ⚠️ (weak/deprecated)")
                elif algo in algo_data["strong"]:
                    lines.append(f"- **{algo}** ✓ (strong)")
                else:
                    lines.append(f"- {algo}")
        else:
            lines.append("*No algorithms reported*")
        lines.append("")

    render_algo_section("Key Exchange Algorithms", data["kex_algorithms"])
    render_algo_section("Host Key Algorithms", data["host_key_algorithms"])
    render_algo_section("Encryption Algorithms", data["encryption_algorithms"])
    render_algo_section("MAC Algorithms", data["mac_algorithms"])

    if data["host_key"]:
        hk = data["host_key"]
        lines.append("## Host Key")
        lines.append(f"- **Type:** {hk['key_type']}")
        lines.append(f"- **Fingerprint (SHA256):** {hk['fingerprint']}")
        if hk.get("key_bits"):
            lines.append(f"- **Key Size:** {hk['key_bits']} bits")
        lines.append("")

    if data["findings"]:
        lines.append("## Security Findings")
        for finding in data["findings"]:
            severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(finding["severity"], "⚪")
            lines.append(f"- {severity_icon} **[{finding['severity'].upper()}]** {finding['description']}")
        lines.append("")
    else:
        lines.append("## Security Findings")
        lines.append("*No weak algorithms detected*")
        lines.append("")

    return "\n".join(lines)
def format_ssh_report_csv(data: Dict[str, object]) -> str:
    """Format SSH security assessment results as CSV."""
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    writer.writerow([
        "type",
        "algorithm",
        "severity",
        "description",
    ])
    findings = data.get("findings") or []
    for finding in findings:
        writer.writerow([
            finding.get("type", ""),
            finding.get("algorithm", ""),
            finding.get("severity", ""),
            finding.get("description", ""),
        ])
    return output.getvalue().rstrip("\r\n")
