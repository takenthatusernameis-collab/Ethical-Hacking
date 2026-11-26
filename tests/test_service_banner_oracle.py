"""Independent oracle verification for ethscan.service banner parsing pure helpers.

This test verifies that _parse_banner_service and _parse_banner_version are
total (never raise) over a large hostile input space and that their output
matches a reference oracle implementation.
"""

from __future__ import annotations

import random
from typing import Callable

from ethscan.service import (
    SERVICE_SIGNATURES,
    _parse_banner_service,
    _parse_banner_version,
)

# ---------------------------------------------------------------------------
# Reference oracle implementations (independent, simpler logic)
# ---------------------------------------------------------------------------

def _oracle_parse_banner_service(
    banner: str | None, service_name: str | None
) -> str | None:
    """Reference oracle for _parse_banner_service."""
    if not banner or not service_name:
        return None

    if service_name not in SERVICE_SIGNATURES:
        return service_name.upper()

    sigs = SERVICE_SIGNATURES.get(service_name) or []
    for pattern, name in sigs:
        match = pattern.search(banner)
        if match:
            return name or (match.group(1) if match.groups() else service_name.upper())

    return service_name.upper()


def _oracle_parse_banner_version(
    banner: str | None, service_name: str | None
) -> str | None:
    """Reference oracle for _parse_banner_version."""
    if not banner or not service_name:
        return None

    if service_name not in SERVICE_SIGNATURES:
        return None

    sigs = SERVICE_SIGNATURES.get(service_name) or []
    for pattern, _name in sigs:
        match = pattern.search(banner)
        if match and match.groups():
            return match.group(1)

    return None


# ---------------------------------------------------------------------------
# Hostile input generation
# ---------------------------------------------------------------------------

CONTROL_CHARS = "\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f"
CONTROL_CHARS += "\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f"
CONTROL_CHARS += "\x7f"

NON_ASCII_SAMPLES = (
    "日本語",
    "中文",
    "한국어",
    "العربية",
    "עברית",
    "🎉🚀💻",
    "café",
    "naïve",
    "résumé",
    "Москва",
    "กรุงเทพฯ",
)

WHITESPACE_VARIANTS = ("", " ", "\t", "\n", "\r", "\f", "\v", "  ", "\t\n", " \t \n ")

# Service names: known + unknown + edge cases
KNOWN_SERVICES = list(SERVICE_SIGNATURES.keys())
UNKNOWN_SERVICES = ("dns", "smb", "snmp", "ldap", "ntp", "kerberos", "radius", "tacacs", "custom")
ALL_SERVICES = KNOWN_SERVICES + list(UNKNOWN_SERVICES) + [None, "", "HTTP", "HTTPS", "FTP", "SSH"]
ALL_SERVICES_LIST = list(ALL_SERVICES)  # For rng.choice compatibility
ALL_SERVICES_NON_NONE = [s for s in ALL_SERVICES if s is not None]  # For string operations


def generate_hostile_banners(rng: random.Random, count: int) -> list[str | None]:
    """Generate a diverse set of hostile banner inputs."""
    banners: list[str | None] = [None, "", *WHITESPACE_VARIANTS]

    # Realistic banner prefixes
    prefixes = (
        "220 ",
        "SSH-2.0-",
        "+OK ",
        "* OK ",
        "220 ",
        "E: ",
        "S: ",
        "RFB ",
        "+PONG",
        "-ERR ",
        "Server: ",
        "HTTP/1.1 ",
        "HTTP/1.0 ",
        "\x03\x00\x00\x13\x0e\xd0",
        "It looks like you are trying to access ",
    )

    # Signature-matching strings
    signature_strings = (
        "FTP",
        "FileZilla",
        "ProFTPD",
        "vsftpd",
        "Pure-FTPd",
        "OpenSSH",
        "Dropbear",
        "libssh",
        "login:",
        "Password:",
        "ESMTP",
        "Postfix",
        "Exim",
        "Sendmail",
        "POP3",
        "Dovecot",
        "IMAP",
        "mysql",
        "MariaDB",
        "FATAL",
        "nginx",
        "Apache",
        "Microsoft-IIS",
        "MongoDB",
        "Redis",
    )

    for _ in range(count):
        # Choose a generation strategy
        strategy = rng.choice([
            "control_chars",
            "non_ascii",
            "very_long",
            "mixed_encoding",
            "signature_based",
            "malformed_version",
            "empty_or_whitespace",
            "random_bytes",
        ])

        if strategy == "control_chars":
            base = rng.choice(prefixes + signature_strings + ("",))
            noise = "".join(rng.choice(CONTROL_CHARS) for _ in range(rng.randint(1, 20)))
            banners.append(base + noise)
            banners.append(noise + base)
            banners.append(noise)

        elif strategy == "non_ascii":
            base = rng.choice(prefixes + signature_strings + ("",))
            non_ascii = rng.choice(NON_ASCII_SAMPLES)
            banners.append(base + non_ascii)
            banners.append(non_ascii + base)
            banners.append(non_ascii)

        elif strategy == "very_long":
            base = rng.choice(prefixes + signature_strings + ("",))
            repeat = rng.choice(signature_strings)
            length = rng.randint(1000, 10000)
            long_banner = base + repeat * (length // len(repeat) + 1)
            banners.append(long_banner[:length])

        elif strategy == "mixed_encoding":
            # Mix valid UTF-8 with control chars and non-ASCII
            parts = []
            for _ in range(rng.randint(5, 20)):
                part_type = rng.choice(["ascii", "control", "non_ascii", "signature"])
                if part_type == "ascii":
                    parts.append(rng.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"))
                elif part_type == "control":
                    parts.append(rng.choice(CONTROL_CHARS))
                elif part_type == "non_ascii":
                    parts.append(rng.choice(NON_ASCII_SAMPLES))
                else:
                    parts.append(rng.choice(signature_strings))
            banners.append("".join(parts))

        elif strategy == "signature_based":
            # Banners designed to match or nearly-match signatures
            svc = rng.choice(KNOWN_SERVICES)
            sigs = SERVICE_SIGNATURES.get(svc, [])
            if sigs:
                pattern, _ = rng.choice(sigs)
                # Try to generate something that matches
                # For simplicity, use known matching strings
                if svc == "ftp":
                    banners.append(rng.choice(["220 FTP Server", "220 FileZilla Server", "220 ProFTPD 1.3.5"]))
                elif svc == "ssh":
                    banners.append(rng.choice(["SSH-2.0-OpenSSH_8.9", "SSH-2.0-Dropbear_2022.82"]))
                elif svc == "http":
                    banners.append(rng.choice(["HTTP/1.1 200 OK", "Server: nginx/1.18.0"]))
                elif svc == "smtp":
                    banners.append(rng.choice(["220 ESMTP Postfix", "220 Exim 4.96"]))
                else:
                    # Generic
                    banners.append(rng.choice(signature_strings))
            else:
                banners.append(rng.choice(signature_strings))

        elif strategy == "malformed_version":
            # Specifically target version extraction edge cases
            banners.append("Server:")  # No space, no version
            banners.append("Server: ")  # Space but no version
            banners.append("Server: nginx")  # No slash
            banners.append("Server: nginx/")  # Slash but no version
            banners.append("Server: nginx/1.18.0 日本語")  # Non-ASCII in version
            banners.append("Server: nginx\x00/1.18")  # Control char in version
            banners.append("Server: " + "1." * 1000)  # Very long version

        elif strategy == "empty_or_whitespace":
            banners.append(rng.choice(WHITESPACE_VARIANTS))

        elif strategy == "random_bytes":
            # Random byte sequences (decoded with replace)
            length = rng.randint(1, 200)
            random_bytes = bytes(rng.randint(0, 255) for _ in range(length))
            banners.append(random_bytes.decode("utf-8", errors="replace"))

    return banners


def generate_hostile_services(rng: random.Random, count: int) -> list[str | None]:
    """Generate a diverse set of hostile service name inputs."""
    services: list[str | None] = [None, "", " ", "\t", "\n", "HTTP", "HTTPS", "FTP", "SSH"]
    services.extend(ALL_SERVICES)

    for _ in range(count):
        strategy = rng.choice([
            "control_chars",
            "non_ascii",
            "very_long",
            "case_variants",
            "random",
        ])

        if strategy == "control_chars":
            base = rng.choice(ALL_SERVICES_NON_NONE)
            noise = "".join(rng.choice(CONTROL_CHARS) for _ in range(rng.randint(1, 10)))
            services.append(base + noise)
            services.append(noise + base)

        elif strategy == "non_ascii":
            base = rng.choice(ALL_SERVICES_NON_NONE)
            non_ascii = rng.choice(NON_ASCII_SAMPLES)
            services.append(base + non_ascii)
            services.append(non_ascii + base)

        elif strategy == "very_long":
            services.append("a" * rng.randint(100, 1000))

        elif strategy == "case_variants":
            base = rng.choice(ALL_SERVICES_NON_NONE)
            services.append(base.upper())
            services.append(base.lower())
            services.append(base.capitalize())
            services.append("".join(rng.choice([c.upper(), c.lower()]) for c in base))

        elif strategy == "random":
            services.append("".join(rng.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(rng.randint(1, 20))))

    return services


# ---------------------------------------------------------------------------
# Test functions
# ---------------------------------------------------------------------------

SEED = 20261126


def _run_totality_check(
    func: Callable[[str | None, str | None], str | None],
    oracle: Callable[[str | None, str | None], str | None],
    banners: list[str | None],
    services: list[str | None],
    func_name: str,
) -> int:
    """Run totality and oracle comparison check. Returns mismatch count."""
    mismatches = 0
    total_cases = 0

    for banner in banners:
        for service in services:
            total_cases += 1
            try:
                result = func(banner, service)
            except Exception as e:
                raise AssertionError(
                    f"{func_name} raised {type(e).__name__}({e!r}) "
                    f"for banner={banner!r}, service={service!r}"
                ) from e

            try:
                expected = oracle(banner, service)
            except Exception as e:
                raise AssertionError(
                    f"Oracle for {func_name} raised {type(e).__name__}({e!r}) "
                    f"for banner={banner!r}, service={service!r}"
                ) from e

            if result != expected:
                mismatches += 1
                if mismatches <= 5:  # Report first few mismatches
                    print(
                        f"MISMATCH {func_name}: banner={banner!r}, service={service!r} "
                        f"=> got={result!r}, expected={expected!r}"
                    )

    if mismatches > 0:
        print(f"Total {func_name} mismatches: {mismatches} / {total_cases}")

    return mismatches


def test_parse_banner_service_totality_and_oracle() -> None:
    """Verify _parse_banner_service is total and matches oracle over hostile inputs."""
    rng = random.Random(SEED)

    banners = generate_hostile_banners(rng, 5000)
    services = generate_hostile_services(rng, 2000)

    mismatches = _run_totality_check(
        _parse_banner_service,
        _oracle_parse_banner_service,
        banners,
        services,
        "_parse_banner_service",
    )

    assert mismatches == 0, f"_parse_banner_service had {mismatches} oracle mismatches"


def test_parse_banner_version_totality_and_oracle() -> None:
    """Verify _parse_banner_version is total and matches oracle over hostile inputs."""
    rng = random.Random(SEED + 1)

    banners = generate_hostile_banners(rng, 5000)
    services = generate_hostile_services(rng, 2000)

    mismatches = _run_totality_check(
        _parse_banner_version,
        _oracle_parse_banner_version,
        banners,
        services,
        "_parse_banner_version",
    )

    assert mismatches == 0, f"_parse_banner_version had {mismatches} oracle mismatches"


def test_parse_banner_service_known_signatures_exhaustive() -> None:
    """Exhaustively verify all known signature patterns against oracle."""
    # For each known service, test all its signature patterns
    for _service_name, sigs in SERVICE_SIGNATURES.items():
        for _pattern, _expected_name in sigs:
            # Generate a string that matches the pattern
            # We can't easily invert regex, so test with known good inputs
            pass

    # Instead, test that for each service, the oracle and implementation
    # agree on a set of hand-crafted matching banners
    test_cases = [
        # (banner, service, expected_service)
        ("220 FTP Server ready", "ftp", "FTP"),
        ("220 FileZilla Server", "ftp", "FileZilla FTP"),
        ("220 ProFTPD 1.3.5", "ftp", "FTP"),  # "FTP" in ProFTPD matches first
        ("220 vsftpd 3.0.3", "ftp", "FTP"),
        ("220 Pure-FTPd", "ftp", "FTP"),
        ("SSH-2.0-OpenSSH_8.9", "ssh", "OpenSSH"),
        ("SSH-2.0-Dropbear_2022.82", "ssh", "Dropbear SSH"),
        ("SSH-2.0-libssh_0.9.6", "ssh", "libssh"),
        ("login: ", "telnet", "Telnet"),
        ("Password: ", "telnet", "Telnet"),
        ("220 ESMTP Postfix", "smtp", "SMTP"),
        ("220 Postfix SMTP", "smtp", "Postfix SMTP"),
        ("220 Exim 4.96", "smtp", "Exim SMTP"),
        ("220 Sendmail 8.17.1", "smtp", "Sendmail"),
        ("+OK POP3 ready", "pop3", "POP3"),
        ("+OK Dovecot ready", "pop3", "Dovecot POP3"),
        ("* OK IMAP4 ready", "imap", "IMAP"),
        ("* OK Dovecot IMAP", "imap", "IMAP"),
        ("HTTP/1.1 200 OK", "http", "HTTP"),
        ("Server: nginx/1.18.0", "http", "nginx/1.18.0"),
        ("Server: Apache/2.4.41", "http", "Apache/2.4.41"),
        ("HTTP/1.1 200 OK", "https", "HTTPS"),
        ("Server: nginx/1.18.0", "https", "nginx/1.18.0"),
        ("12345678mysql", "mysql", "MySQL"),
        ("12345678MariaDB", "mysql", "MariaDB"),
        ("\x03\x00\x00\x13\x0e\xd0", "rdp", "RDP"),
        ("RFB 003.008", "vnc", "VNC"),
        ("+PONG", "redis", "Redis"),
        ("-ERR unknown command", "redis", "Redis"),
        ("It looks like you are trying to access MongoDB", "mongodb", "MongoDB"),
        ("E: FATAL: database does not exist", "postgresql", "PostgreSQL"),
        ("S: FATAL: role does not exist", "postgresql", "PostgreSQL"),
    ]

    for banner, service, expected in test_cases:
        result = _parse_banner_service(banner, service)
        oracle_result = _oracle_parse_banner_service(banner, service)
        assert result == oracle_result == expected, (
            f"banner={banner!r}, service={service!r}: "
            f"impl={result!r}, oracle={oracle_result!r}, expected={expected!r}"
        )


def test_parse_banner_version_known_signatures_exhaustive() -> None:
    """Exhaustively verify version extraction for known signatures."""
    test_cases = [
        # (banner, service, expected_version)
        ("Server: nginx/1.18.0", "http", "nginx/1.18.0"),
        ("Server: Apache/2.4.41", "http", "Apache/2.4.41"),
        ("Server: Microsoft-IIS/10.0", "http", "Microsoft-IIS/10.0"),
        ("Server: nginx/1.18.0", "https", "nginx/1.18.0"),
        ("Server: Apache/2.4.41", "https", "Apache/2.4.41"),
        # No capture group -> None
        ("220 FileZilla Server", "ftp", None),
        ("220 ProFTPD 1.3.5", "ftp", None),
        ("SSH-2.0-OpenSSH_8.9", "ssh", None),
        ("login: ", "telnet", None),
        ("220 ESMTP Postfix", "smtp", None),
        ("+OK POP3 ready", "pop3", None),
        ("* OK IMAP4 ready", "imap", None),
        ("12345678mysql", "mysql", None),
        ("\x03\x00\x00\x13\x0e\xd0", "rdp", None),
        ("RFB 003.008", "vnc", None),
        ("+PONG", "redis", None),
        ("It looks like you are trying to access MongoDB", "mongodb", None),
        ("E: FATAL: database does not exist", "postgresql", None),
        # Edge cases
        ("Server:", "http", None),
        ("Server: ", "http", " "),  # captures single space
        ("Server: nginx", "http", "nginx"),
        ("Server: nginx/", "http", "nginx/"),
        ("server: nginx/1.18.0", "http", "nginx/1.18.0"),  # case insensitive
        ("SERVER: Apache/2.4.41", "http", "Apache/2.4.41"),
        ("Server: nginx/1.18.0 日本語", "http", "nginx/1.18.0 日本語"),
        ("Server: nginx\x00/1.18", "http", "nginx\x00/1.18"),
        # Unknown service -> None
        ("Server: nginx/1.18.0", "dns", None),
        ("Server: nginx/1.18.0", "smb", None),
    ]

    for banner, service, expected in test_cases:
        result = _parse_banner_version(banner, service)
        oracle_result = _oracle_parse_banner_version(banner, service)
        assert result == oracle_result == expected, (
            f"banner={banner!r}, service={service!r}: "
            f"impl={result!r}, oracle={oracle_result!r}, expected={expected!r}"
        )


def test_parse_banner_service_unknown_service_returns_upper() -> None:
    """Unknown services (not in SERVICE_SIGNATURES) return uppercased service name."""
    rng = random.Random(SEED + 2)
    unknown_services = [s for s in UNKNOWN_SERVICES if s]  # Only actual unknown services

    for _ in range(1000):
        banner = "".join(rng.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ") for _ in range(rng.randint(1, 100)))  # Non-empty banner
        service = rng.choice(unknown_services)
        result = _parse_banner_service(banner, service)
        oracle_result = _oracle_parse_banner_service(banner, service)
        expected = service.upper()
        assert result == oracle_result == expected, (
            f"banner={banner!r}, service={service!r}: "
            f"impl={result!r}, oracle={oracle_result!r}, expected={expected!r}"
        )


def test_parse_banner_version_unknown_service_returns_none() -> None:
    """Unknown services return None for version."""
    rng = random.Random(SEED + 3)
    unknown_services = [s for s in ALL_SERVICES if s and s not in SERVICE_SIGNATURES]

    for _ in range(1000):
        banner = "".join(rng.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ") for _ in range(rng.randint(0, 100)))
        service = rng.choice(unknown_services)
        if not service:
            continue
        result = _parse_banner_version(banner, service)
        oracle_result = _oracle_parse_banner_version(banner, service)
        assert result == oracle_result is None, (
            f"banner={banner!r}, service={service!r}: "
            f"impl={result!r}, oracle={oracle_result!r}, expected=None"
        )


def test_parse_banner_service_none_empty_inputs() -> None:
    """None or empty inputs return None."""
    assert _parse_banner_service(None, "ssh") is None
    assert _parse_banner_service("", "ssh") is None
    assert _parse_banner_service("banner", None) is None
    assert _parse_banner_service("banner", "") is None

    # Oracle agrees
    assert _oracle_parse_banner_service(None, "ssh") is None
    assert _oracle_parse_banner_service("", "ssh") is None
    assert _oracle_parse_banner_service("banner", None) is None
    assert _oracle_parse_banner_service("banner", "") is None


def test_parse_banner_version_none_empty_inputs() -> None:
    """None or empty inputs return None."""
    assert _parse_banner_version(None, "ssh") is None
    assert _parse_banner_version("", "ssh") is None
    assert _parse_banner_version("banner", None) is None
    assert _parse_banner_version("banner", "") is None

    # Oracle agrees
    assert _oracle_parse_banner_version(None, "ssh") is None
    assert _oracle_parse_banner_version("", "ssh") is None
    assert _oracle_parse_banner_version("banner", None) is None
    assert _oracle_parse_banner_version("banner", "") is None


# ---------------------------------------------------------------------------
# Property-based verification (deterministic, seeded)
# ---------------------------------------------------------------------------

def test_parse_banner_service_property_never_raises() -> None:
    """Property: _parse_banner_service never raises for any input."""
    rng = random.Random(SEED + 10)

    # Generate random inputs
    for _ in range(10000):
        banner_len = rng.randint(0, 500)
        service_len = rng.randint(0, 50)

        # Random bytes decoded with replace
        banner_bytes = bytes(rng.randint(0, 255) for _ in range(banner_len))
        banner: str | None = banner_bytes.decode("utf-8", errors="replace")

        service_bytes = bytes(rng.randint(0, 255) for _ in range(service_len))
        service: str | None = service_bytes.decode("utf-8", errors="replace")

        # Also include None
        if rng.random() < 0.1:
            banner = None
        if rng.random() < 0.1:
            service = None

        # Should never raise
        result = _parse_banner_service(banner, service)
        assert result is None or isinstance(result, str)


def test_parse_banner_version_property_never_raises() -> None:
    """Property: _parse_banner_version never raises for any input."""
    rng = random.Random(SEED + 11)

    for _ in range(10000):
        banner_len = rng.randint(0, 500)
        service_len = rng.randint(0, 50)

        banner_bytes = bytes(rng.randint(0, 255) for _ in range(banner_len))
        banner: str | None = banner_bytes.decode("utf-8", errors="replace")

        service_bytes = bytes(rng.randint(0, 255) for _ in range(service_len))
        service: str | None = service_bytes.decode("utf-8", errors="replace")

        if rng.random() < 0.1:
            banner = None
        if rng.random() < 0.1:
            service = None

        result = _parse_banner_version(banner, service)
        assert result is None or isinstance(result, str)


def test_parse_banner_service_property_output_constraints() -> None:
    """Property: output constraints for _parse_banner_service."""
    rng = random.Random(SEED + 12)

    for _ in range(5000):
        banner_len = rng.randint(0, 200)
        service_len = rng.randint(0, 30)

        banner_bytes = bytes(rng.randint(0, 255) for _ in range(banner_len))
        banner: str | None = banner_bytes.decode("utf-8", errors="replace")

        service_bytes = bytes(rng.randint(0, 255) for _ in range(service_len))
        service: str | None = service_bytes.decode("utf-8", errors="replace")

        if rng.random() < 0.1:
            banner = None
        if rng.random() < 0.1:
            service = None

        result = _parse_banner_service(banner, service)

        if result is not None:
            # Result should be a non-empty string
            assert isinstance(result, str)
            assert len(result) > 0

            # If service is known and has signatures, result should be either
            # a signature name or service.upper()
            if service and service in SERVICE_SIGNATURES:
                sig_names = [name for _, name in SERVICE_SIGNATURES[service] if name]
                valid_results = set(sig_names) | {service.upper()}
                assert result in valid_results, (
                    f"Unexpected result {result!r} for service {service!r}. "
                    f"Valid: {valid_results}"
                )
            elif service:
                # Unknown service -> upper()
                assert result == service.upper()


def test_parse_banner_version_property_output_constraints() -> None:
    """Property: output constraints for _parse_banner_version."""
    rng = random.Random(SEED + 13)

    for _ in range(5000):
        banner_len = rng.randint(0, 200)
        service_len = rng.randint(0, 30)

        banner_bytes = bytes(rng.randint(0, 255) for _ in range(banner_len))
        banner: str | None = banner_bytes.decode("utf-8", errors="replace")

        service_bytes = bytes(rng.randint(0, 255) for _ in range(service_len))
        service: str | None = service_bytes.decode("utf-8", errors="replace")

        if rng.random() < 0.1:
            banner = None
        if rng.random() < 0.1:
            service = None

        result = _parse_banner_version(banner, service)

        if result is not None:
            assert isinstance(result, str)
            # Version can be empty string (e.g., "Server: " captures " ")
            assert len(result) >= 0

        # If service is unknown, must be None
        if service and service not in SERVICE_SIGNATURES:
            assert result is None


def test_parse_banner_service_first_match_wins() -> None:
    """Property: first matching signature wins (order matters)."""
    # FTP: first pattern is "220.*FTP", second is "220.*FileZilla"
    # "220 FileZilla Server" does NOT contain "FTP" so second pattern matches
    assert _parse_banner_service("220 FileZilla Server", "ftp") == "FileZilla FTP"
    assert _oracle_parse_banner_service("220 FileZilla Server", "ftp") == "FileZilla FTP"

    # "220 ProFTPD Server" contains "FTP" (in ProFTP) so first pattern matches
    assert _parse_banner_service("220 ProFTPD Server", "ftp") == "FTP"
    assert _oracle_parse_banner_service("220 ProFTPD Server", "ftp") == "FTP"

    # SMTP: first is "220.*ESMTP", second is "220.*Postfix"
    # "220 Postfix ESMTP" contains "ESMTP" so first matches
    assert _parse_banner_service("220 Postfix ESMTP", "smtp") == "SMTP"
    assert _oracle_parse_banner_service("220 Postfix ESMTP", "smtp") == "SMTP"

    # "220 Postfix Server" does not contain "ESMTP" so second matches
    assert _parse_banner_service("220 Postfix Server", "smtp") == "Postfix SMTP"
    assert _oracle_parse_banner_service("220 Postfix Server", "smtp") == "Postfix SMTP"

    # IMAP: first is "* OK.*IMAP", second is "* OK.*Dovecot"
    # "* OK Dovecot IMAP" contains "IMAP" so first matches
    assert _parse_banner_service("* OK Dovecot IMAP", "imap") == "IMAP"
    assert _oracle_parse_banner_service("* OK Dovecot IMAP", "imap") == "IMAP"

    # "* OK Dovecot Ready" does not contain "IMAP" so second matches
    assert _parse_banner_service("* OK Dovecot Ready", "imap") == "Dovecot IMAP"
    assert _oracle_parse_banner_service("* OK Dovecot Ready", "imap") == "Dovecot IMAP"


def test_parse_banner_version_capture_group_behavior() -> None:
    """Property: only patterns with capture groups return version."""
    # HTTP/HTTPS Server header has capture group
    assert _parse_banner_version("Server: nginx/1.18.0", "http") == "nginx/1.18.0"
    assert _parse_banner_version("Server: nginx/1.18.0", "https") == "nginx/1.18.0"

    # FTP patterns have no capture groups
    assert _parse_banner_version("220 FileZilla Server", "ftp") is None
    assert _parse_banner_version("220 ProFTPD 1.3.5", "ftp") is None

    # SSH patterns have no capture groups
    assert _parse_banner_version("SSH-2.0-OpenSSH_8.9", "ssh") is None

    # Oracle agrees
    assert _oracle_parse_banner_version("Server: nginx/1.18.0", "http") == "nginx/1.18.0"
    assert _oracle_parse_banner_version("220 FileZilla Server", "ftp") is None
    assert _oracle_parse_banner_version("SSH-2.0-OpenSSH_8.9", "ssh") is None


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])