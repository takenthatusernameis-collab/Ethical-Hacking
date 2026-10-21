"""Permanent sweep test: a hostile server answer is reported, never raised.

The protocol commands talk to servers that answer with whatever they like. The
modules that wrap their probe block report a failure through their own failure
field; the modules that lacked that net (redis, memcached, ntp, ldap, smb,
snmp, ssh and dnssec) now report it the same way, like the other protocol
commands.

Two checks per module:

* every answer in ``HOSTILE_ANSWERS`` is answered with a result and never with
  a traceback: the parsers are reached with the bytes a hostile server can
  send;
* a failure inside the probe block is reported through the module's own
  failure field instead of escaping as an exception.

The protocol modules whose own test file already carries hostile-answer tests
(smtp, ftp, web, cve and subtake) are not repeated here.
"""
from __future__ import annotations

import struct
from typing import Any

import pytest

from ethscan import (
    dnssec,
    ldap,
    memcached,
    ntp,
    redis,
    service,
    smb,
    snmp,
    ssh,
    ssl,
    tls,
    whois,
)

#: The answers a hostile server can send: the framing of each protocol with
#: the content left out, made hostile or not text at all. A length that does
#: not fit the answer, a status line that is not a status line, and bytes that
#: are not text.
HOSTILE_ANSWERS: tuple[bytes, ...] = (
    b"",
    b"\r\n",
    b"\x00\x00\x00\x00",
    b"\xff\xfe\xfd\xfc",
    b"+PONG\r\n",
    b"-ERR unknown command\r\n",
    b"$5\r\nhello\r\n",
    b"$-1\r\n",
    b"*3\r\n$1\r\na\r\n",
    b":not-a-number\r\n",
    b"END\r\n",
    b"VERSION 1.2.3\r\n",
    b"STAT curr_items 12\r\nEND\r\n",
    b"\x1bSSH-2.0-fake\r\n",
    bytes(range(256)),
)

#: The protocol modules that take a transport seam: the connector is called as
#: ``connector(host, port, request, timeout)`` and returns ``(data, error)``.
CONNECTOR_MODULES: tuple[tuple[str, Any, dict[str, Any]], ...] = (
    ("redis", redis.run_redis, {}),
    ("memcached", memcached.run_memcached, {}),
    ("ntp", ntp.run_ntp, {}),
    ("ldap", ldap.run_ldap, {}),
    ("smb2", smb.run_smb2, {}),
    ("smb", smb.run_smb, {}),
    ("snmp", snmp.run_snmp, {}),
)

MODULE_IDS = [name for name, _runner, _kwargs in CONNECTOR_MODULES]
ANSWER_IDS = [f"answer{index}" for index in range(len(HOSTILE_ANSWERS))]


def _connector_for(answer: bytes):
    """Return a connector that answers every request with *answer*."""

    def connector(host, port, request, timeout):
        return answer, None

    return connector


@pytest.mark.parametrize("answer", HOSTILE_ANSWERS, ids=ANSWER_IDS)
@pytest.mark.parametrize("name,runner,kwargs", CONNECTOR_MODULES, ids=MODULE_IDS)
def test_hostile_answer_is_reported_not_raised(
    name: str, runner, kwargs: dict[str, Any], answer: bytes
) -> None:
    """A hostile answer is answered with a result, never with a traceback."""
    results = runner("127.0.0.1", connector=_connector_for(answer), **kwargs)

    assert isinstance(results, dict)
    assert "error" in results


@pytest.mark.parametrize("name,runner,kwargs", CONNECTOR_MODULES, ids=MODULE_IDS)
def test_probe_failure_is_reported_not_raised(
    name: str, runner, kwargs: dict[str, Any]
) -> None:
    """A failure inside the probe block is reported, not raised.

    The connector stands for the part of the probe that goes wrong: a parser
    that meets a byte it cannot read, or a transport that fails in a way the
    module does not know. The command must report it.
    """

    def connector(host, port, request, timeout):
        raise RuntimeError("hostile server answer")

    results = runner("127.0.0.1", connector=connector, **kwargs)

    assert "probe failed" in (results.get("error") or "")


class _ScriptedSocket:
    """A socket stand-in that replays a fixed list of server answers."""

    def __init__(self, answers: list[bytes]) -> None:
        self.answers = list(answers)
        self.sent = b""
        self.closed = False

    def settimeout(self, _timeout: float) -> None:
        pass

    def recv(self, _size: int) -> bytes:
        if not self.answers:
            return b""
        return self.answers.pop(0)

    def sendall(self, data: bytes) -> None:
        self.sent += data

    def close(self) -> None:
        self.closed = True


def test_ssh_hostile_answer_is_reported_not_raised(monkeypatch) -> None:
    """A hostile SSH answer is answered with a result, never with a traceback."""
    banner = b"SSH-2.0-OpenSSH_8.9\r\n"
    # A KEXINIT whose first name list claims a length that does not fit.
    kexinit = b"\x04\x14" + b"\x00" * 16 + struct.pack(">I", 0xFFFFFFFF) + b"\x00" * 4
    sock = _ScriptedSocket([banner, struct.pack(">I", len(kexinit)), kexinit])
    monkeypatch.setattr(ssh.socket, "create_connection", lambda *a, **kw: sock)

    result = ssh.run_ssh("127.0.0.1")

    assert result["error"] is None
    assert result["banner"] == "SSH-2.0-OpenSSH_8.9"


def test_ssh_probe_failure_is_reported_not_raised(monkeypatch) -> None:
    """A failure inside the SSH probe is reported, not raised."""

    def boom(*args, **kwargs):
        raise RuntimeError("hostile server answer")

    monkeypatch.setattr(ssh.socket, "create_connection", boom)

    result = ssh.run_ssh("127.0.0.1")

    assert "probe failed" in (result.get("error") or "")


def test_dnssec_probe_failure_is_reported_not_raised(monkeypatch) -> None:
    """A failure inside the DNSSEC probe is reported, not raised."""

    def boom(*args, **kwargs):
        raise RuntimeError("hostile server answer")

    # Both the dnspython path and the stdlib path are stubbed, so the check
    # holds whether or not dnspython is installed.
    monkeypatch.setattr(
        dnssec, "_resolve_nameservers", lambda domain, timeout: ["127.0.0.1"]
    )
    monkeypatch.setattr(dnssec, "_query_dnskey_raw", boom)
    monkeypatch.setattr(dnssec, "_query_dnskey_dnspython", boom)

    result = dnssec.run_dnssec("example.com")

    assert "probe failed" in (result["dnskey"].get("error") or "")
    assert "probe failed" in (result["ds"].get("error") or "")


def test_ssl_probe_failure_is_reported_not_raised(monkeypatch) -> None:
    """A failing SSL transport is reported through the error field, not raised."""

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.ssl.socket.create_connection", boom)

    result = ssl.run_ssl("example.com")

    assert isinstance(result, dict)
    assert result["error"] is not None
    assert "hostile transport" in result["error"]


def test_tls_probe_failure_is_reported_not_raised(monkeypatch) -> None:
    """A failing TLS transport is reported per probe, not raised."""

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.tls.socket.create_connection", boom)

    result = tls.run_tls("example.com")

    assert isinstance(result, dict)
    for entry in result["versions"]:
        assert entry["supported"] is False
        assert entry["error"] is not None
    for entry in result["ciphers"]:
        assert entry["supported"] is False
        assert entry["error"] is not None


def test_whois_probe_failure_is_reported_not_raised(monkeypatch) -> None:
    """A failing WHOIS transport is reported through the error field, not raised."""

    class BoomSocket:
        def __init__(self, *a, **k):
            pass

        def settimeout(self, *a, **k):
            pass

        def connect(self, *a, **k):
            raise RuntimeError("hostile transport")

        def close(self, *a, **k):
            pass

    monkeypatch.setattr("ethscan.whois.socket.socket", BoomSocket)

    result = whois.run_whois("example.com")

    assert isinstance(result, dict)
    assert result["error"] is not None
    assert "hostile transport" in result["error"]


def test_service_probe_failure_is_reported_not_raised(monkeypatch) -> None:
    """A failing service-detection transport is reported, not raised."""

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.service.socket.create_connection", boom)

    result = service.run_service("127.0.0.1")

    assert isinstance(result, dict)
    assert result["services_found"] == 0
    assert result["results"] == []
