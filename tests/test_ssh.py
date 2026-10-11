"""Tests for the ethscan ssh module."""

import pytest

from ethscan.ssh import (
    DEFAULT_PORT,
    DEFAULT_TIMEOUT,
    PARAMIKO_AVAILABLE,
    STRONG_CIPHERS,
    STRONG_HOST_KEY_TYPES,
    STRONG_KEX_ALGORITHMS,
    STRONG_MACS,
    WEAK_CIPHERS,
    WEAK_HOST_KEY_TYPES,
    WEAK_KEX_ALGORITHMS,
    WEAK_MACS,
    _analyze_algorithms,
    _extract_port,
    _normalize_host,
    _parse_kexinit,
    format_ssh_report_json,
    format_ssh_report_markdown,
    run_ssh,
)


def test_defaults() -> None:
    assert DEFAULT_PORT == 22
    assert DEFAULT_TIMEOUT == 10.0


def test_normalize_host_bare() -> None:
    assert _normalize_host("example.com") == "example.com"
    assert _normalize_host("EXAMPLE.COM") == "example.com"


def test_normalize_host_url() -> None:
    assert _normalize_host("ssh://example.com") == "example.com"
    assert _normalize_host("ssh://user@example.com:2222/path") == "example.com"
    assert _normalize_host("https://example.com/path") == "example.com"


def test_normalize_host_with_port() -> None:
    assert _normalize_host("example.com:2222") == "example.com"


def test_extract_port_default() -> None:
    assert _extract_port("example.com") == 22
    assert _extract_port("ssh://example.com") == 22


def test_extract_port_from_url() -> None:
    assert _extract_port("ssh://example.com:2222") == 2222
    assert _extract_port("https://example.com:2222/path") == 2222


def test_extract_port_explicit() -> None:
    assert _extract_port("example.com", default=2222) == 2222


def test_weak_kex_algorithms() -> None:
    assert "diffie-hellman-group1-sha1" in WEAK_KEX_ALGORITHMS
    assert "diffie-hellman-group14-sha1" in WEAK_KEX_ALGORITHMS
    assert "diffie-hellman-group-exchange-sha1" in WEAK_KEX_ALGORITHMS


def test_strong_kex_algorithms() -> None:
    assert "curve25519-sha256" in STRONG_KEX_ALGORITHMS
    assert "curve25519-sha256@libssh.org" in STRONG_KEX_ALGORITHMS
    assert "diffie-hellman-group16-sha512" in STRONG_KEX_ALGORITHMS


def test_weak_ciphers() -> None:
    assert "3des-cbc" in WEAK_CIPHERS
    assert "arcfour" in WEAK_CIPHERS
    assert "arcfour128" in WEAK_CIPHERS
    assert "arcfour256" in WEAK_CIPHERS
    assert "aes128-cbc" in WEAK_CIPHERS


def test_strong_ciphers() -> None:
    assert "aes128-ctr" in STRONG_CIPHERS
    assert "aes256-ctr" in STRONG_CIPHERS
    assert "chacha20-poly1305@openssh.com" in STRONG_CIPHERS
    assert "aes128-gcm@openssh.com" in STRONG_CIPHERS


def test_weak_macs() -> None:
    assert "hmac-md5" in WEAK_MACS
    assert "hmac-sha1" in WEAK_MACS
    assert "hmac-sha1-96" in WEAK_MACS


def test_strong_macs() -> None:
    assert "hmac-sha2-256-etm@openssh.com" in STRONG_MACS
    assert "umac-64-etm@openssh.com" in STRONG_MACS


def test_weak_host_key_types() -> None:
    assert "ssh-dss" in WEAK_HOST_KEY_TYPES
    assert "ssh-rsa" in WEAK_HOST_KEY_TYPES


def test_strong_host_key_types() -> None:
    assert "ssh-ed25519" in STRONG_HOST_KEY_TYPES
    assert "ecdsa-sha2-nistp256" in STRONG_HOST_KEY_TYPES
    assert "rsa-sha2-256" in STRONG_HOST_KEY_TYPES


def test_analyze_algorithms() -> None:
    algorithms = {
        "kex_algorithms": [
            "curve25519-sha256",
            "diffie-hellman-group1-sha1",
            "diffie-hellman-group14-sha1",
        ],
        "server_host_key_algorithms": ["ssh-ed25519", "ssh-rsa", "ssh-dss"],
        "encryption_algorithms_client_to_server": ["aes256-ctr", "aes128-cbc", "3des-cbc"],
        "encryption_algorithms_server_to_client": ["aes256-ctr", "arcfour"],
        "mac_algorithms_client_to_server": ["hmac-sha2-256-etm@openssh.com", "hmac-sha1"],
        "mac_algorithms_server_to_client": ["hmac-sha2-256-etm@openssh.com", "hmac-md5"],
    }

    result = _analyze_algorithms(algorithms)

    assert "curve25519-sha256" in result["kex_algorithms"]["strong"]
    assert "diffie-hellman-group1-sha1" in result["kex_algorithms"]["weak"]
    assert "diffie-hellman-group14-sha1" in result["kex_algorithms"]["weak"]

    assert "ssh-ed25519" in result["host_key_algorithms"]["strong"]
    assert "ssh-rsa" in result["host_key_algorithms"]["weak"]
    assert "ssh-dss" in result["host_key_algorithms"]["weak"]

    assert "aes256-ctr" in result["encryption_algorithms"]["strong"]
    assert "aes128-cbc" in result["encryption_algorithms"]["weak"]
    assert "3des-cbc" in result["encryption_algorithms"]["weak"]
    assert "arcfour" in result["encryption_algorithms"]["weak"]

    assert "hmac-sha2-256-etm@openssh.com" in result["mac_algorithms"]["strong"]
    assert "hmac-sha1" in result["mac_algorithms"]["weak"]
    assert "hmac-md5" in result["mac_algorithms"]["weak"]


def test_analyze_algorithms_empty() -> None:
    result = _analyze_algorithms({})
    assert result["kex_algorithms"]["supported"] == []
    assert result["kex_algorithms"]["weak"] == []
    assert result["kex_algorithms"]["strong"] == []


def test_parse_kexinit_minimal() -> None:
    cookie = b"\x00" * 16
    payload = b"\x14" + cookie
    for _ in range(10):
        payload += struct.pack(">I", 0)
    result = _parse_kexinit(payload)
    assert result["kex_algorithms"] == []
    assert result["server_host_key_algorithms"] == []


def test_parse_kexinit_with_algorithms() -> None:
    import struct

    cookie = b"\x00" * 16

    def name_list(names: List[str]) -> bytes:
        data = ",".join(names).encode("ascii")
        return struct.pack(">I", len(data)) + data

    payload = b"\x14" + cookie
    payload += name_list(["curve25519-sha256", "diffie-hellman-group1-sha1"])
    payload += name_list(["ssh-ed25519", "ssh-rsa"])
    payload += name_list(["aes256-ctr", "aes128-cbc"])
    payload += name_list(["aes256-ctr", "3des-cbc"])
    payload += name_list(["hmac-sha2-256", "hmac-sha1"])
    payload += name_list(["hmac-sha2-256", "hmac-md5"])
    payload += name_list(["none"])
    payload += name_list(["none"])
    payload += name_list([""])
    payload += name_list([""])

    result = _parse_kexinit(payload)
    assert "curve25519-sha256" in result["kex_algorithms"]
    assert "diffie-hellman-group1-sha1" in result["kex_algorithms"]
    assert "ssh-ed25519" in result["server_host_key_algorithms"]
    assert "ssh-rsa" in result["server_host_key_algorithms"]
    assert "aes256-ctr" in result["encryption_algorithms_client_to_server"]
    assert "aes128-cbc" in result["encryption_algorithms_client_to_server"]
    assert "3des-cbc" in result["encryption_algorithms_server_to_client"]
    assert "hmac-sha2-256" in result["mac_algorithms_client_to_server"]
    assert "hmac-sha1" in result["mac_algorithms_client_to_server"]
    assert "hmac-md5" in result["mac_algorithms_server_to_client"]


def test_format_ssh_report_json() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "port": 22,
        "timeout": 10.0,
        "banner": "SSH-2.0-OpenSSH_8.9",
        "paramiko_available": False,
        "kex_algorithms": {"supported": ["curve25519-sha256"], "weak": [], "strong": ["curve25519-sha256"]},
        "host_key_algorithms": {"supported": ["ssh-ed25519"], "weak": [], "strong": ["ssh-ed25519"]},
        "encryption_algorithms": {"supported": ["aes256-ctr"], "weak": [], "strong": ["aes256-ctr"]},
        "mac_algorithms": {"supported": ["hmac-sha2-256"], "weak": [], "strong": ["hmac-sha2-256"]},
        "host_key": {"fingerprint": "aa:bb:cc", "key_type": "ssh-ed25519", "key_bits": 256},
        "findings": [],
        "error": None,
    }
    output = format_ssh_report_json(data)
    assert "example.com" in output
    assert "SSH-2.0-OpenSSH_8.9" in output
    assert "curve25519-sha256" in output
    assert "ssh-ed25519" in output


def test_format_ssh_report_json_error() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "port": 22,
        "timeout": 10.0,
        "banner": None,
        "paramiko_available": False,
        "kex_algorithms": {"supported": [], "weak": [], "strong": []},
        "host_key_algorithms": {"supported": [], "weak": [], "strong": []},
        "encryption_algorithms": {"supported": [], "weak": [], "strong": []},
        "mac_algorithms": {"supported": [], "weak": [], "strong": []},
        "host_key": None,
        "findings": [],
        "error": "connection refused",
    }
    output = format_ssh_report_json(data)
    assert "connection refused" in output


def test_format_ssh_report_markdown() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "port": 22,
        "timeout": 10.0,
        "banner": "SSH-2.0-OpenSSH_8.9",
        "paramiko_available": False,
        "kex_algorithms": {"supported": ["curve25519-sha256", "diffie-hellman-group1-sha1"], "weak": ["diffie-hellman-group1-sha1"], "strong": ["curve25519-sha256"]},
        "host_key_algorithms": {"supported": ["ssh-ed25519", "ssh-rsa"], "weak": ["ssh-rsa"], "strong": ["ssh-ed25519"]},
        "encryption_algorithms": {"supported": ["aes256-ctr", "aes128-cbc"], "weak": ["aes128-cbc"], "strong": ["aes256-ctr"]},
        "mac_algorithms": {"supported": ["hmac-sha2-256", "hmac-sha1"], "weak": ["hmac-sha1"], "strong": ["hmac-sha2-256"]},
        "host_key": {"fingerprint": "aa:bb:cc", "key_type": "ssh-ed25519", "key_bits": 256},
        "findings": [
            {"type": "weak_kex", "algorithm": "diffie-hellman-group1-sha1", "severity": "medium", "description": "Weak key exchange algorithm supported: diffie-hellman-group1-sha1"},
            {"type": "weak_host_key", "algorithm": "ssh-rsa", "severity": "high", "description": "Weak host key type supported: ssh-rsa"},
        ],
        "error": None,
    }
    output = format_ssh_report_markdown(data)
    assert "# ethscan SSH Security Assessment Report" in output
    assert "example.com" in output
    assert "SSH-2.0-OpenSSH_8.9" in output
    assert "diffie-hellman-group1-sha1" in output
    assert "ssh-rsa" in output
    assert "⚠️" in output
    assert "✓" in output
    assert "Security Findings" in output
    assert "🔴" in output or "🟡" in output


def test_format_ssh_report_markdown_error() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "port": 22,
        "timeout": 10.0,
        "banner": None,
        "paramiko_available": False,
        "kex_algorithms": {"supported": [], "weak": [], "strong": []},
        "host_key_algorithms": {"supported": [], "weak": [], "strong": []},
        "encryption_algorithms": {"supported": [], "weak": [], "strong": []},
        "mac_algorithms": {"supported": [], "weak": [], "strong": []},
        "host_key": None,
        "findings": [],
        "error": "connection refused",
    }
    output = format_ssh_report_markdown(data)
    assert "connection refused" in output


def test_run_ssh_offline(monkeypatch) -> None:
    def mock_create_connection(*args, **kwargs):
        raise ConnectionRefusedError("connection refused")

    monkeypatch.setattr("ethscan.ssh.socket.create_connection", mock_create_connection)

    result = run_ssh("nonexistent.invalid.host", port=22, timeout=0.1)
    assert result["host"] == "nonexistent.invalid.host"
    assert result["target"] == "nonexistent.invalid.host"
    assert result["port"] == 22
    assert result["error"] == "Connection refused"
    assert result["banner"] is None


def test_run_ssh_timeout(monkeypatch) -> None:
    def mock_create_connection(*args, **kwargs):
        raise socket.timeout("timed out")

    import socket
    monkeypatch.setattr("ethscan.ssh.socket.create_connection", mock_create_connection)

    result = run_ssh("example.com", port=22, timeout=0.1)
    assert result["error"] == "Connection timeout"


def test_paramiko_available_flag() -> None:
    assert isinstance(PARAMIKO_AVAILABLE, bool)


# Need to import struct and socket for some tests
import struct
import socket
from typing import List