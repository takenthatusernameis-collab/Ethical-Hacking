"""Tests for the ethscan ssh module."""

import socket
import struct
import types
from typing import Any
from unittest.mock import MagicMock

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
    _get_host_key_info_paramiko,
    _get_host_key_info_stdlib,
    _normalize_host,
    _parse_kexinit,
    _read_packet,
    _send_kexinit,
    _ssh_banner_exchange,
    format_ssh_report_csv,
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

    def name_list(names: list[str]) -> bytes:
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

# ---------------------------------------------------------------------------
# CSV formatter
# ---------------------------------------------------------------------------


def test_format_ssh_report_csv_basic() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "port": 22,
        "timeout": 10.0,
        "banner": "SSH-2.0-OpenSSH_8.9",
        "paramiko_available": False,
        "kex_algorithms": {
            "supported": ["curve25519-sha256", "diffie-hellman-group1-sha1"],
            "weak": ["diffie-hellman-group1-sha1"],
            "strong": ["curve25519-sha256"],
        },
        "host_key_algorithms": {
            "supported": ["ssh-ed25519", "ssh-rsa"],
            "weak": ["ssh-rsa"],
            "strong": ["ssh-ed25519"],
        },
        "encryption_algorithms": {
            "supported": ["aes256-ctr", "aes128-cbc"],
            "weak": ["aes128-cbc"],
            "strong": ["aes256-ctr"],
        },
        "mac_algorithms": {
            "supported": ["hmac-sha2-256", "hmac-sha1"],
            "weak": ["hmac-sha1"],
            "strong": ["hmac-sha2-256"],
        },
        "host_key": {"fingerprint": "aa:bb:cc", "key_type": "ssh-ed25519", "key_bits": 256},
        "findings": [
            {"type": "weak_kex", "algorithm": "diffie-hellman-group1-sha1", "severity": "medium", "description": "Weak key exchange algorithm supported: diffie-hellman-group1-sha1"},
            {"type": "weak_host_key", "algorithm": "ssh-rsa", "severity": "high", "description": "Weak host key type supported: ssh-rsa"},
        ],
        "error": None,
    }
    output = format_ssh_report_csv(data)

    lines = [line.rstrip("\r") for line in output.strip().split("\n")]
    assert lines[0] == "type,algorithm,severity,description"
    assert "weak_kex,diffie-hellman-group1-sha1,medium,Weak key exchange algorithm supported: diffie-hellman-group1-sha1" in lines[1]
    assert "weak_host_key,ssh-rsa,high,Weak host key type supported: ssh-rsa" in lines[2]


def test_format_ssh_report_csv_empty() -> None:
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
        "error": None,
    }
    output = format_ssh_report_csv(data)

    lines = [line.rstrip("\r") for line in output.strip().split("\n")]
    assert lines[0] == "type,algorithm,severity,description"


def test_format_ssh_report_csv_missing_fields() -> None:
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
        "findings": [
            {"type": "weak_kex", "algorithm": "diffie-hellman-group1-sha1"}  # missing severity, description
        ],
        "error": None,
    }
    output = format_ssh_report_csv(data)

    lines = [line.rstrip("\r") for line in output.strip().split("\n")]
    assert "weak_kex,diffie-hellman-group1-sha1,," in lines[1]


def test_format_ssh_report_csv_pipe_escaping() -> None:
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
        "findings": [
            {"type": "weak_kex", "algorithm": "pipe|algo", "severity": "high", "description": "pipe|desc"}
        ],
        "error": None,
    }
    output = format_ssh_report_csv(data)

    # With QUOTE_MINIMAL, pipe characters don't require quoting
    assert "pipe|algo" in output
    assert "pipe|desc" in output


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _kexinit_response(
    kex: list[str] | None = None,
    host_keys: list[str] | None = None,
    ciphers_c2s: list[str] | None = None,
    ciphers_s2c: list[str] | None = None,
    macs_c2s: list[str] | None = None,
    macs_s2c: list[str] | None = None,
    compressions: list[str] | None = None,
    languages: list[str] | None = None,
) -> bytes:
    """Build a valid SSH_MSG_KEXINIT server response (msg_type + cookie + name lists)."""
    cookie = b"\x00" * 16

    def name_list(names: list[str]) -> bytes:
        data = ",".join(names).encode("ascii")
        return struct.pack(">I", len(data)) + data

    payload = b"\x14" + cookie
    payload += name_list(kex or [])
    payload += name_list(host_keys or [])
    payload += name_list(ciphers_c2s or [])
    payload += name_list(ciphers_s2c or [])
    payload += name_list(macs_c2s or [])
    payload += name_list(macs_s2c or [])
    payload += name_list(compressions or ["none"])
    payload += name_list(compressions or ["none"])
    payload += name_list(languages or [""])
    payload += name_list(languages or [""])
    return payload


def _ssh_result(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "target": "example.com",
        "host": "example.com",
        "port": 22,
        "timeout": 10.0,
        "banner": "SSH-2.0-OpenSSH_8.9",
        "paramiko_available": False,
        "kex_algorithms": {"supported": [], "weak": [], "strong": []},
        "host_key_algorithms": {"supported": [], "weak": [], "strong": []},
        "encryption_algorithms": {"supported": [], "weak": [], "strong": []},
        "mac_algorithms": {"supported": [], "weak": [], "strong": []},
        "host_key": None,
        "findings": [],
        "error": None,
    }
    data.update(overrides)
    return data


# ---------------------------------------------------------------------------
# _ssh_banner_exchange
# ---------------------------------------------------------------------------


def test_ssh_banner_exchange_success() -> None:
    sock = MagicMock()
    sock.recv.return_value = b"SSH-2.0-OpenSSH_8.9\r\n"
    assert _ssh_banner_exchange(sock, 5.0) == "SSH-2.0-OpenSSH_8.9"
    sock.settimeout.assert_called_once_with(5.0)


def test_ssh_banner_exchange_non_ssh_prefix() -> None:
    sock = MagicMock()
    sock.recv.return_value = b"HELLO\r\n"
    assert _ssh_banner_exchange(sock, 5.0) is None


def test_ssh_banner_exchange_timeout() -> None:
    sock = MagicMock()
    sock.recv.side_effect = socket.timeout("timed out")
    assert _ssh_banner_exchange(sock, 5.0) is None


def test_ssh_banner_exchange_oserror() -> None:
    sock = MagicMock()
    sock.recv.side_effect = OSError("connection reset")
    assert _ssh_banner_exchange(sock, 5.0) is None


# ---------------------------------------------------------------------------
# _send_kexinit
# ---------------------------------------------------------------------------


def test_send_kexinit_sends_packet() -> None:
    sock = MagicMock()
    _send_kexinit(sock)
    sock.sendall.assert_called_once()
    sent = sock.sendall.call_args[0][0]
    # [4-byte length][SSH_MSG_KEXINIT(0x14)]...
    assert sent[4:5] == b"\x14"
    assert len(sent) > 5 + 16


# ---------------------------------------------------------------------------
# _read_packet
# ---------------------------------------------------------------------------


def test_read_packet_short_length_reply() -> None:
    sock = MagicMock()
    sock.recv.return_value = b"\x00\x00"
    assert _read_packet(sock) is None


def test_read_packet_too_large() -> None:
    sock = MagicMock()
    sock.recv.return_value = struct.pack(">I", 40000)
    assert _read_packet(sock) is None


def test_read_packet_valid() -> None:
    body = b"\x01hello"
    sock = MagicMock()
    sock.recv.side_effect = [struct.pack(">I", len(body)), body]
    assert _read_packet(sock) == b"hello"


def test_read_packet_partial_chunks() -> None:
    body = b"\x00abcdefg"
    sock = MagicMock()
    sock.recv.side_effect = [struct.pack(">I", len(body)), b"\x00ab", b"cdefg"]
    assert _read_packet(sock) == b"abcdefg"


def test_read_packet_empty_chunk() -> None:
    body = b"\x00abcdefg"
    sock = MagicMock()
    sock.recv.side_effect = [struct.pack(">I", len(body)), b"\x00ab", b""]
    assert _read_packet(sock) is None


def test_read_packet_timeout() -> None:
    sock = MagicMock()
    sock.recv.side_effect = socket.timeout("timed out")
    assert _read_packet(sock) is None


def test_read_packet_oserror() -> None:
    sock = MagicMock()
    sock.recv.side_effect = OSError("reset")
    assert _read_packet(sock) is None


# ---------------------------------------------------------------------------
# _parse_kexinit edge cases
# ---------------------------------------------------------------------------


def test_parse_kexinit_too_short() -> None:
    assert _parse_kexinit(b"\x14\x00\x00") == {}


def test_parse_kexinit_truncated_name_length() -> None:
    cookie = b"\x00" * 16
    payload = b"\x14" + cookie + struct.pack(">I", 10)
    assert _parse_kexinit(payload) == {}


def test_parse_kexinit_truncated_length_field() -> None:
    cookie = b"\x00" * 16
    payload = b"\x14" + cookie
    for _ in range(8):
        payload += struct.pack(">I", 0)
    payload += b"\x00\x00"
    result = _parse_kexinit(payload)
    assert len(result) == 8
    assert result["kex_algorithms"] == []


# ---------------------------------------------------------------------------
# _get_host_key_info_paramiko / _get_host_key_info_stdlib
# ---------------------------------------------------------------------------


def test_get_host_key_info_paramiko_unavailable() -> None:
    assert _get_host_key_info_paramiko("example.com", 22, 1.0) is None


def test_get_host_key_info_stdlib_returns_none() -> None:
    assert _get_host_key_info_stdlib(MagicMock()) is None


def test_get_host_key_info_paramiko_success(monkeypatch) -> None:
    fake_paramiko = types.ModuleType("paramiko")
    fake_host_key = MagicMock()
    fake_host_key.get_fingerprint.return_value = b"\xde\xad\xbe\xef"
    fake_host_key.get_name.return_value = "ssh-ed25519"
    fake_host_key.get_bits.return_value = 256
    fake_transport = MagicMock()
    fake_transport.get_remote_server_key.return_value = fake_host_key
    fake_paramiko.Transport = lambda sock: fake_transport

    fake_sock = MagicMock()
    monkeypatch.setattr("ethscan.ssh.socket.create_connection", lambda *a, **k: fake_sock)
    monkeypatch.setattr("ethscan.ssh.paramiko", fake_paramiko, raising=False)
    monkeypatch.setattr("ethscan.ssh.PARAMIKO_AVAILABLE", True)

    result = _get_host_key_info_paramiko("example.com", 22, 1.0)
    assert result is not None
    assert result["fingerprint"] == "de:ad:be:ef"
    assert result["key_type"] == "ssh-ed25519"
    assert result["key_bits"] == 256
    fake_transport.close.assert_called_once()
    fake_sock.close.assert_called_once()


def test_get_host_key_info_paramiko_exception(monkeypatch) -> None:
    fake_paramiko = types.ModuleType("paramiko")
    fake_transport = MagicMock()
    fake_transport.start_client.side_effect = Exception("handshake failed")
    fake_paramiko.Transport = lambda sock: fake_transport

    fake_sock = MagicMock()
    monkeypatch.setattr("ethscan.ssh.socket.create_connection", lambda *a, **k: fake_sock)
    monkeypatch.setattr("ethscan.ssh.paramiko", fake_paramiko, raising=False)
    monkeypatch.setattr("ethscan.ssh.PARAMIKO_AVAILABLE", True)

    assert _get_host_key_info_paramiko("example.com", 22, 1.0) is None


# ---------------------------------------------------------------------------
# run_ssh paths
# ---------------------------------------------------------------------------


def test_run_ssh_success(monkeypatch) -> None:
    response = _kexinit_response(
        kex=["curve25519-sha256", "diffie-hellman-group1-sha1"],
        host_keys=["ssh-ed25519", "ssh-rsa"],
        ciphers_c2s=["aes256-ctr", "aes128-cbc"],
        ciphers_s2c=[],
        macs_c2s=["hmac-sha2-256", "hmac-sha1"],
        macs_s2c=[],
    )
    fake_sock = MagicMock()
    monkeypatch.setattr("ethscan.ssh.socket.create_connection", lambda *a, **k: fake_sock)
    monkeypatch.setattr("ethscan.ssh._ssh_banner_exchange", lambda s, t: "SSH-2.0-OpenSSH_8.9")
    monkeypatch.setattr("ethscan.ssh._send_kexinit", lambda s: None)
    monkeypatch.setattr("ethscan.ssh._read_packet", lambda s: response)

    result = run_ssh("example.com", port=22, timeout=1.0)

    assert result["banner"] == "SSH-2.0-OpenSSH_8.9"
    assert result["error"] is None
    assert result["paramiko_available"] is False
    assert "curve25519-sha256" in result["kex_algorithms"]["supported"]
    assert "diffie-hellman-group1-sha1" in result["kex_algorithms"]["weak"]
    assert "ssh-rsa" in result["host_key_algorithms"]["weak"]
    assert "aes128-cbc" in result["encryption_algorithms"]["weak"]
    assert "hmac-sha1" in result["mac_algorithms"]["weak"]
    finding_types = {f["type"] for f in result["findings"]}
    assert {"weak_kex", "weak_host_key", "weak_cipher", "weak_mac"} <= finding_types
    fake_sock.close.assert_called_once()


def test_run_ssh_no_banner(monkeypatch) -> None:
    fake_sock = MagicMock()
    monkeypatch.setattr("ethscan.ssh.socket.create_connection", lambda *a, **k: fake_sock)
    monkeypatch.setattr("ethscan.ssh._ssh_banner_exchange", lambda s, t: None)

    result = run_ssh("example.com", port=22, timeout=1.0)

    assert result["banner"] is None
    assert result["error"] == "No SSH banner received"
    fake_sock.close.assert_called_once()


def test_run_ssh_no_kexinit_response(monkeypatch) -> None:
    fake_sock = MagicMock()
    monkeypatch.setattr("ethscan.ssh.socket.create_connection", lambda *a, **k: fake_sock)
    monkeypatch.setattr("ethscan.ssh._ssh_banner_exchange", lambda s, t: "SSH-2.0-OpenSSH_8.9")
    monkeypatch.setattr("ethscan.ssh._send_kexinit", lambda s: None)
    monkeypatch.setattr("ethscan.ssh._read_packet", lambda s: None)

    result = run_ssh("example.com", port=22, timeout=1.0)

    assert result["banner"] == "SSH-2.0-OpenSSH_8.9"
    assert result["error"] is None
    assert result["findings"] == []
    fake_sock.close.assert_called_once()


def test_run_ssh_non_kexinit_response(monkeypatch) -> None:
    fake_sock = MagicMock()
    monkeypatch.setattr("ethscan.ssh.socket.create_connection", lambda *a, **k: fake_sock)
    monkeypatch.setattr("ethscan.ssh._ssh_banner_exchange", lambda s, t: "SSH-2.0-OpenSSH_8.9")
    monkeypatch.setattr("ethscan.ssh._send_kexinit", lambda s: None)
    monkeypatch.setattr("ethscan.ssh._read_packet", lambda s: b"\x99something")

    result = run_ssh("example.com", port=22, timeout=1.0)

    assert result["banner"] == "SSH-2.0-OpenSSH_8.9"
    assert result["error"] is None
    assert result["kex_algorithms"]["supported"] == []
    fake_sock.close.assert_called_once()


def test_run_ssh_oserror(monkeypatch) -> None:
    def mock_create_connection(*args, **kwargs):
        raise OSError("network is unreachable")

    monkeypatch.setattr("ethscan.ssh.socket.create_connection", mock_create_connection)

    result = run_ssh("example.com", port=22, timeout=1.0)
    assert result["error"] == "Connection error: network is unreachable"
    assert result["banner"] is None


def test_run_ssh_send_kexinit_oserror(monkeypatch) -> None:
    fake_sock = MagicMock()
    fake_sock.sendall.side_effect = OSError("send failed")
    monkeypatch.setattr("ethscan.ssh.socket.create_connection", lambda *a, **k: fake_sock)
    monkeypatch.setattr("ethscan.ssh._ssh_banner_exchange", lambda s, t: "SSH-2.0-OpenSSH_8.9")

    result = run_ssh("example.com", port=22, timeout=1.0)
    assert result["error"] == "Connection error: send failed"
    fake_sock.close.assert_called_once()


def test_run_ssh_close_swallows_exception(monkeypatch) -> None:
    fake_sock = MagicMock()
    fake_sock.close.side_effect = RuntimeError("close failed")
    monkeypatch.setattr("ethscan.ssh.socket.create_connection", lambda *a, **k: fake_sock)
    monkeypatch.setattr("ethscan.ssh._ssh_banner_exchange", lambda s, t: None)

    result = run_ssh("example.com", port=22, timeout=1.0)
    assert result["error"] == "No SSH banner received"
    assert result["banner"] is None
    fake_sock.close.assert_called_once()


def test_run_ssh_paramiko_weak_host_key(monkeypatch) -> None:
    response = _kexinit_response(kex=["curve25519-sha256"], host_keys=["ssh-ed25519"])
    fake_sock = MagicMock()
    monkeypatch.setattr("ethscan.ssh.socket.create_connection", lambda *a, **k: fake_sock)
    monkeypatch.setattr("ethscan.ssh._ssh_banner_exchange", lambda s, t: "SSH-2.0-OpenSSH_8.9")
    monkeypatch.setattr("ethscan.ssh._send_kexinit", lambda s: None)
    monkeypatch.setattr("ethscan.ssh._read_packet", lambda s: response)
    monkeypatch.setattr("ethscan.ssh.PARAMIKO_AVAILABLE", True)
    monkeypatch.setattr(
        "ethscan.ssh._get_host_key_info_paramiko",
        lambda host, port, timeout: {
            "fingerprint": "aa:bb:cc",
            "key_type": "ssh-rsa",
            "key_bits": 2048,
        },
    )

    result = run_ssh("example.com", port=22, timeout=1.0)
    assert result["paramiko_available"] is True
    assert result["host_key"]["key_type"] == "ssh-rsa"
    assert any(
        f["type"] == "weak_host_key" and f["algorithm"] == "ssh-rsa"
        for f in result["findings"]
    )
    fake_sock.close.assert_called_once()


def test_run_ssh_paramiko_strong_host_key(monkeypatch) -> None:
    response = _kexinit_response(kex=["curve25519-sha256"], host_keys=["ssh-ed25519"])
    fake_sock = MagicMock()
    monkeypatch.setattr("ethscan.ssh.socket.create_connection", lambda *a, **k: fake_sock)
    monkeypatch.setattr("ethscan.ssh._ssh_banner_exchange", lambda s, t: "SSH-2.0-OpenSSH_8.9")
    monkeypatch.setattr("ethscan.ssh._send_kexinit", lambda s: None)
    monkeypatch.setattr("ethscan.ssh._read_packet", lambda s: response)
    monkeypatch.setattr("ethscan.ssh.PARAMIKO_AVAILABLE", True)
    monkeypatch.setattr(
        "ethscan.ssh._get_host_key_info_paramiko",
        lambda host, port, timeout: {
            "fingerprint": "aa:bb:cc",
            "key_type": "ssh-ed25519",
            "key_bits": 256,
        },
    )

    result = run_ssh("example.com", port=22, timeout=1.0)
    assert result["host_key"]["key_type"] == "ssh-ed25519"
    # Strong host key type must not add a weak_host_key finding.
    assert not any(f["type"] == "weak_host_key" for f in result["findings"])


def test_run_ssh_paramiko_no_host_key(monkeypatch) -> None:
    response = _kexinit_response(kex=["curve25519-sha256"], host_keys=["ssh-ed25519"])
    fake_sock = MagicMock()
    monkeypatch.setattr("ethscan.ssh.socket.create_connection", lambda *a, **k: fake_sock)
    monkeypatch.setattr("ethscan.ssh._ssh_banner_exchange", lambda s, t: "SSH-2.0-OpenSSH_8.9")
    monkeypatch.setattr("ethscan.ssh._send_kexinit", lambda s: None)
    monkeypatch.setattr("ethscan.ssh._read_packet", lambda s: response)
    monkeypatch.setattr("ethscan.ssh.PARAMIKO_AVAILABLE", True)
    monkeypatch.setattr("ethscan.ssh._get_host_key_info_paramiko", lambda host, port, timeout: None)

    result = run_ssh("example.com", port=22, timeout=1.0)
    assert result["host_key"] is None


# ---------------------------------------------------------------------------
# Markdown formatter edge cases
# ---------------------------------------------------------------------------


def test_format_ssh_report_markdown_neutral_algo() -> None:
    data = _ssh_result(
        kex_algorithms={"supported": ["custom-kex"], "weak": [], "strong": []},
        banner="SSH-2.0-test",
        findings=[],
    )
    output = format_ssh_report_markdown(data)
    assert "- custom-kex" in output


def test_format_ssh_report_markdown_no_findings() -> None:
    data = _ssh_result(banner="SSH-2.0-test", findings=[])
    output = format_ssh_report_markdown(data)
    assert "No weak algorithms detected" in output
def test_paramiko_import_success(monkeypatch):
    """Test paramiko import when available."""
    import sys
    from importlib import reload

    # Create a mock paramiko module
    mock_paramiko = types.ModuleType('paramiko')
    monkeypatch.setitem(sys.modules, 'paramiko', mock_paramiko)

    # Reload the ssh module to trigger the import
    import ethscan.ssh
    reload(ethscan.ssh)
    assert ethscan.ssh.PARAMIKO_AVAILABLE is True

    # Clean up
    monkeypatch.delitem(sys.modules, 'paramiko', raising=False)
    reload(ethscan.ssh)
