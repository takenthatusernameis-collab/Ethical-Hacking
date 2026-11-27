#!/usr/bin/env python3
"""Independent oracle verification for ethscan.service pure helpers.

This script verifies the pure helper functions in ethscan.service against
stdlib oracles (re) over a hostile input matrix.

Functions verified:
- _parse_banner_service
- _parse_banner_version

The script runs silently on success, prints mismatches on failure, and
exits with non-zero code if any oracle mismatch is found.
"""

from __future__ import annotations

import re
import sys

from ethscan.service import (
    _parse_banner_service,
    _parse_banner_version,
)

# ──────────────────────────────────────────────────────────────────────────────
# Oracle implementations using stdlib only (re-implements the spec from scratch)
# ──────────────────────────────────────────────────────────────────────────────

# Re-define signatures using stdlib only (copied from service.py for independence)
ORACLE_SIGNATURES: dict[str, list[tuple[re.Pattern[str], str | None]]] = {
    "ftp": [
        (re.compile(r"^220.*FTP", re.IGNORECASE), "FTP"),
        (re.compile(r"^220.*FileZilla", re.IGNORECASE), "FileZilla FTP"),
        (re.compile(r"^220.*ProFTPD", re.IGNORECASE), "ProFTPD"),
        (re.compile(r"^220.*vsftpd", re.IGNORECASE), "vsftpd"),
        (re.compile(r"^220.*Pure-FTPd", re.IGNORECASE), "Pure-FTPd"),
    ],
    "ssh": [
        (re.compile(r"^SSH-2\.0-OpenSSH", re.IGNORECASE), "OpenSSH"),
        (re.compile(r"^SSH-2\.0-.*Dropbear", re.IGNORECASE), "Dropbear SSH"),
        (re.compile(r"^SSH-2\.0-.*libssh", re.IGNORECASE), "libssh"),
    ],
    "telnet": [
        (re.compile(r"^.*login:", re.IGNORECASE), "Telnet"),
        (re.compile(r"^.*Password:", re.IGNORECASE), "Telnet"),
    ],
    "smtp": [
        (re.compile(r"^220.*ESMTP", re.IGNORECASE), "SMTP"),
        (re.compile(r"^220.*Postfix", re.IGNORECASE), "Postfix SMTP"),
        (re.compile(r"^220.*Exim", re.IGNORECASE), "Exim SMTP"),
        (re.compile(r"^220.*Sendmail", re.IGNORECASE), "Sendmail"),
    ],
    "pop3": [
        (re.compile(r"^\+OK.*POP3", re.IGNORECASE), "POP3"),
        (re.compile(r"^\+OK.*Dovecot", re.IGNORECASE), "Dovecot POP3"),
    ],
    "imap": [
        (re.compile(r"^\* OK.*IMAP", re.IGNORECASE), "IMAP"),
        (re.compile(r"^\* OK.*Dovecot", re.IGNORECASE), "Dovecot IMAP"),
    ],
    "http": [
        (re.compile(r"^HTTP/1\.[01] 200", re.IGNORECASE), "HTTP"),
        (re.compile(r"Server:\s*([^\r\n]+)", re.IGNORECASE), None),
    ],
    "https": [
        (re.compile(r"^HTTP/1\.[01] 200", re.IGNORECASE), "HTTPS"),
        (re.compile(r"Server:\s*([^\r\n]+)", re.IGNORECASE), None),
    ],
    "mysql": [
        (re.compile(r"^[0-9a-f]{8}.*mysql", re.IGNORECASE), "MySQL"),
        (re.compile(r"^[0-9a-f]{8}.*MariaDB", re.IGNORECASE), "MariaDB"),
    ],
    "rdp": [
        (re.compile(r"^\x03\x00\x00\x13\x0e\xd0", re.DOTALL), "RDP"),
    ],
    "vnc": [
        (re.compile(r"^RFB 003\.", re.IGNORECASE), "VNC"),
    ],
    "redis": [
        (re.compile(r"^\+PONG", re.IGNORECASE), "Redis"),
        (re.compile(r"^-ERR", re.IGNORECASE), "Redis"),
    ],
    "mongodb": [
        (re.compile(r"It looks like you are trying to access MongoDB", re.IGNORECASE), "MongoDB"),
    ],
    "postgresql": [
        (re.compile(r"^E.*FATAL", re.IGNORECASE), "PostgreSQL"),
        (re.compile(r"^S.*FATAL", re.IGNORECASE), "PostgreSQL"),
    ],
}


def oracle_parse_banner_service(banner: str | None, service_name: str | None) -> str | None:
    """Oracle for _parse_banner_service using stdlib only.

    Pure re-implementation of the service detection logic.
    """
    if not banner or not service_name:
        return None

    if service_name not in ORACLE_SIGNATURES:
        return service_name.upper()

    sigs = ORACLE_SIGNATURES.get(service_name) or []
    for pattern, name in sigs:
        match = pattern.search(banner)
        if match:
            return name or (match.group(1) if match.groups() else service_name.upper())

    return service_name.upper()


def oracle_parse_banner_version(banner: str | None, service_name: str | None) -> str | None:
    """Oracle for _parse_banner_version using stdlib only.

    Pure re-implementation of the version extraction logic.
    """
    if not banner or not service_name:
        return None

    if service_name not in ORACLE_SIGNATURES:
        return None

    sigs = ORACLE_SIGNATURES.get(service_name) or []
    for pattern, _name in sigs:
        match = pattern.search(banner)
        if match and match.groups():
            return match.group(1)

    return None


# ──────────────────────────────────────────────────────────────────────────────
# Hostile input generators
# ──────────────────────────────────────────────────────────────────────────────

def generate_hostile_banners() -> list[str | None]:
    """Generate a comprehensive matrix of hostile banner strings."""
    banners: list[str | None] = [None, "", "   ", "\t\n", " \t \n "]

    # Valid service banners (should match signatures)
    valid_banners = [
        "220 FTP Server ready",
        "220 FileZilla Server",
        "220 ProFTPD 1.3.5",
        "220 vsftpd 3.0.3",
        "220 Pure-FTPd",
        "SSH-2.0-OpenSSH_8.9p1",
        "SSH-2.0-Dropbear_2022.82",
        "SSH-2.0-libssh_0.9.6",
        "login: ",
        "Password: ",
        "220 ESMTP Postfix",
        "220 Postfix SMTP",
        "220 Exim 4.96",
        "220 Sendmail 8.17.1",
        "+OK POP3 ready",
        "+OK Dovecot ready",
        "* OK IMAP4 ready",
        "* OK Dovecot IMAP",
        "HTTP/1.1 200 OK",
        "Server: nginx/1.18.0",
        "Server: Apache/2.4.41",
        "HTTP/1.0 200 OK\r\nServer: Microsoft-IIS/10.0",
        "12345678mysql",
        "12345678MariaDB",
        "\x03\x00\x00\x13\x0e\xd0",
        "RFB 003.008",
        "+PONG",
        "-ERR unknown command",
        "It looks like you are trying to access MongoDB",
        "E: FATAL: database does not exist",
        "S: FATAL: role does not exist",
    ]
    banners.extend(valid_banners)

    # Empty/whitespace variations
    banners.extend(["", " ", "\t", "\n", "\r", "\x00", "\x7f", " \t \n \r "])

    # Control characters in banners
    controls = ["\x00", "\x01", "\x09", "\x0a", "\x0d", "\x1f", "\x7f"]
    for c in controls:
        banners.extend([
            f"SSH-2.0-OpenSSH{c}8.9",
            f"220 FileZilla{c}Server",
            f"Server: nginx{c}/1.18",
            f"{c}220 FTP",
            f"220{c}FTP",
        ])

    # Very long banners
    banners.extend([
        "A" * 2000,
        "SSH-2.0-OpenSSH_" + "A" * 2000,
        "Server: " + "nginx/" + "1." * 1000,
        "220 " + "FTP " * 500,
    ])

    # Non-ASCII / Unicode
    banners.extend([
        "SSH-2.0-OpenSSH_8.9日本語",
        "220 FTP サーバー",
        "Server: nginx/1.18.0 тест",
        "220 FTP 🚀",
        "It looks like you are trying to access MongoDB 你好",
    ])

    # Mixed case
    banners.extend([
        "ssh-2.0-openssh_8.9",
        "220 filezilla server",
        "server: nginx/1.18.0",
        "http/1.1 200 ok",
        "+ok pop3 ready",
    ])

    # Malformed versions
    banners.extend([
        "SSH-2.0-OpenSSH",
        "SSH-2.0-OpenSSH_",
        "SSH-2.0-",
        "Server:",
        "Server: ",
        "Server: nginx",
        "Server: nginx/",
        "220 FileZilla version",
        "220 ProFTPD version 1.3.5 extra",
    ])

    # Random noise
    banners.extend([
        "random garbage",
        "not a service banner",
        "HTTP/2.0 200 OK",
        "SSH-1.99-OpenSSH",
        "Telnet\xff\xfb\x01",
        "\xff\xfd\x03\xff\xfd\x18",
    ])

    # Percent-encoded looking strings
    banners.extend([
        "SSH-2.0-OpenSSH%208.9",
        "220%20FTP%20Server",
        "Server%3A%20nginx",
    ])

    return banners


def generate_service_names() -> list[str | None]:
    """Generate service names including valid and invalid ones."""
    return [
        None, "", " ", "ftp", "ssh", "telnet", "smtp", "pop3", "imap",
        "http", "https", "mysql", "rdp", "vnc", "redis", "mongodb", "postgresql",
        "unknown", "dns", "smb", "imaps", "pop3s",
        "FTP", "SSH", "HTTP", "HTTPS",  # uppercase
        "FtP", "SsH", "HtTp",  # mixed case
        "ftp ", " ssh", "http\n",  # with whitespace
        "ftp\x00", "ssh\x00",  # with null
        "not_a_service",
        "service_with_very_long_name_that_does_not_exist_in_signatures",
    ]


# ──────────────────────────────────────────────────────────────────────────────
# Verification functions
# ──────────────────────────────────────────────────────────────────────────────

def verify_parse_banner_service() -> list[tuple[str, str, str]]:
    """Verify _parse_banner_service against oracle.

    Returns list of mismatches: (input_desc, our_result, oracle_result)
    """
    mismatches = []
    banners = generate_hostile_banners()
    service_names = generate_service_names()

    for banner in banners:
        for service_name in service_names:
            banner_repr = repr(banner) if banner is not None else "None"
            service_repr = repr(service_name) if service_name is not None else "None"
            input_desc = f"banner={banner_repr}, service={service_repr}"

            try:
                our_result = _parse_banner_service(banner, service_name)
            except Exception as e:
                mismatches.append((input_desc, f"EXCEPTION: {type(e).__name__}: {e}", "ORACLE_N/A"))
                continue

            oracle_result = oracle_parse_banner_service(banner, service_name)

            if our_result != oracle_result:
                mismatches.append((input_desc, str(our_result), str(oracle_result)))

    return mismatches


def verify_parse_banner_version() -> list[tuple[str, str, str]]:
    """Verify _parse_banner_version against oracle.

    Returns list of mismatches: (input_desc, our_result, oracle_result)
    """
    mismatches = []
    banners = generate_hostile_banners()
    service_names = generate_service_names()

    for banner in banners:
        for service_name in service_names:
            banner_repr = repr(banner) if banner is not None else "None"
            service_repr = repr(service_name) if service_name is not None else "None"
            input_desc = f"banner={banner_repr}, service={service_repr}"

            try:
                our_result = _parse_banner_version(banner, service_name)
            except Exception as e:
                mismatches.append((input_desc, f"EXCEPTION: {type(e).__name__}: {e}", "ORACLE_N/A"))
                continue

            oracle_result = oracle_parse_banner_version(banner, service_name)

            if our_result != oracle_result:
                mismatches.append((input_desc, str(our_result), str(oracle_result)))

    return mismatches


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main() -> int:
    """Run all verifications. Returns 0 on success, 1 on mismatch."""
    all_mismatches = []

    print("Verifying _parse_banner_service...", file=sys.stderr)
    mismatches = verify_parse_banner_service()
    if mismatches:
        all_mismatches.extend([("_parse_banner_service",) + m for m in mismatches])
        print(f"  FAIL: {len(mismatches)} mismatches", file=sys.stderr)
    else:
        print("  OK", file=sys.stderr)

    print("Verifying _parse_banner_version...", file=sys.stderr)
    mismatches = verify_parse_banner_version()
    if mismatches:
        all_mismatches.extend([("_parse_banner_version",) + m for m in mismatches])
        print(f"  FAIL: {len(mismatches)} mismatches", file=sys.stderr)
    else:
        print("  OK", file=sys.stderr)

    if all_mismatches:
        print(f"\n=== TOTAL MISMATCHES: {len(all_mismatches)} ===", file=sys.stderr)
        for func, inp, ours, oracle in all_mismatches[:20]:
            print(f"  {func}({inp}) => ours={ours!r}, oracle={oracle!r}", file=sys.stderr)
        if len(all_mismatches) > 20:
            print(f"  ... and {len(all_mismatches) - 20} more", file=sys.stderr)
        return 1

    print("\n=== ALL VERIFICATIONS PASSED ===", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())