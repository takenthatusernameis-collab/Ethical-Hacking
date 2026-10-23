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

The HTTP-facing commands whose own test file already carries hostile-answer
tests (web, cve and subtake) are not repeated here. The FTP and SMTP commands
are covered here for the failing transport and for a hostile answer; their own
test files keep the real-socket cases.

The ping, osdetect, resolve, dns, stale and subdomains commands have no
connector seam: their transport is a stdlib socket call
(``socket.socket``, ``socket.create_connection``, ``socket.getaddrinfo`` or
``socket.gethostbyname``). A transport failure of an unnamed type there is
patched to raise and must be reported through the module's own failure field,
never raised.
"""
from __future__ import annotations

import ftplib
import struct
from typing import Any

import pytest

from ethscan import (
    dns,
    dnsbrute,
    dnssec,
    ftp,
    ldap,
    memcached,
    mongodb,
    mssql,
    mysql,
    netbios,
    ntp,
    oracle,
    osdetect,
    ping,
    postgresql,
    redis,
    resolve,
    scanner,
    service,
    smb,
    smtp,
    snmp,
    ssh,
    ssl,
    stale,
    subdomains,
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

#: The protocol modules that take the same transport seam as the group above
#: (``connector(host, port, request, timeout)`` answering ``(data, error)``)
#: but report a failing probe in their own wording instead of the
#: "probe failed" of that group.
TRANSPORT_MODULES: tuple[tuple[str, Any, str], ...] = (
    ("netbios", netbios.run_netbios, "node status request failed"),
    ("mysql", mysql.run_mysql, "connector error"),
    ("mongodb", mongodb.run_mongodb, "connector error"),
    ("postgresql", postgresql.run_postgresql, "connector error"),
    ("mssql", mssql.run_mssql, "connector error"),
    ("oracle", oracle.run_oracle, "connector error"),
)

#: The database modules that open a TCP connection to the server.
DATABASE_MODULES: tuple[tuple[str, Any], ...] = (
    ("mysql", mysql.run_mysql),
    ("mongodb", mongodb.run_mongodb),
    ("postgresql", postgresql.run_postgresql),
    ("mssql", mssql.run_mssql),
    ("oracle", oracle.run_oracle),
)

TRANSPORT_MODULE_IDS = [name for name, _runner, _wording in TRANSPORT_MODULES]
DATABASE_MODULE_IDS = [name for name, _runner in DATABASE_MODULES]


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


@pytest.mark.parametrize("answer", HOSTILE_ANSWERS, ids=ANSWER_IDS)
@pytest.mark.parametrize(
    "name,runner,wording", TRANSPORT_MODULES, ids=TRANSPORT_MODULE_IDS
)
def test_transport_hostile_answer_is_reported_not_raised(
    name: str, runner, wording: str, answer: bytes
) -> None:
    """A hostile answer is answered with a result, never with a traceback.

    The database and NBNS modules take the same transport seam as the group
    above; their parsers are reached with the bytes a hostile server can send.
    """
    results = runner("127.0.0.1", connector=_connector_for(answer))

    assert isinstance(results, dict)
    assert "error" in results


@pytest.mark.parametrize(
    "name,runner,wording", TRANSPORT_MODULES, ids=TRANSPORT_MODULE_IDS
)
def test_transport_probe_failure_is_reported_not_raised(
    name: str, runner, wording: str
) -> None:
    """A failure inside the probe block is reported, not raised.

    The module reports it in its own wording: the reason of the failure is
    never lost, and the command never crashes on it.
    """

    def connector(host, port, request, timeout):
        raise RuntimeError("hostile transport")

    results = runner("127.0.0.1", connector=connector)

    error = results.get("error") or ""
    assert wording in error
    assert "hostile transport" in error


@pytest.mark.parametrize("name,runner", DATABASE_MODULES, ids=DATABASE_MODULE_IDS)
def test_database_socket_failure_is_reported_not_raised(
    name: str, runner, monkeypatch
) -> None:
    """A failing socket transport is reported, not raised.

    The socket is the transport the command really uses; a failure of an
    unnamed type there must be reported through the module's own error field.
    """

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr(f"ethscan.{name}.socket.create_connection", boom)

    results = runner("127.0.0.1")

    assert "hostile transport" in (results.get("error") or "")


def test_netbios_socket_failure_is_reported_not_raised(monkeypatch) -> None:
    """A failing NBNS transport is reported, not raised.

    NBNS talks over UDP, so the socket is the seam that fails: a socket that
    cannot even be created must be reported like any other transport failure.
    """

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.netbios.socket.socket", boom)

    results = netbios.run_netbios("127.0.0.1")

    assert "node status request failed" in (results.get("error") or "")
    assert "hostile transport" in (results.get("error") or "")


def test_ftp_hostile_banner_is_reported_not_raised() -> None:
    """A hostile FTP banner is answered with a result, never with a traceback.

    A greeting that is not text is what a hostile server sends; the client
    library reads it as a decode error, which the module reports as a failed
    banner read.
    """

    class _HostileFTP:
        def connect(self, host, port, timeout=30):
            return "220 ready"

        def getwelcome(self):
            raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")

        def login(self, user="anonymous", passwd="", account=""):
            raise ftplib.Error("530 Login incorrect")

        def close(self):
            pass

    results = ftp.run_ftp("127.0.0.1", connector=_HostileFTP)

    assert isinstance(results, dict)
    assert "banner read failed" in (results.get("error") or "")


def test_ftp_probe_failure_is_reported_not_raised() -> None:
    """A failing FTP transport is reported through the error field, not raised."""

    def connector():
        raise RuntimeError("hostile transport")

    results = ftp.run_ftp("127.0.0.1", connector=connector)

    assert isinstance(results, dict)
    assert "hostile transport" in (results.get("error") or "")


@pytest.mark.parametrize("answer", HOSTILE_ANSWERS, ids=ANSWER_IDS)
def test_smtp_hostile_answer_is_reported_not_raised(answer: bytes) -> None:
    """A hostile SMTP answer is answered with a result, never with a traceback."""

    def connector(address, timeout):
        return _ScriptedSocket([answer])

    results = smtp.run_smtp("127.0.0.1", connector=connector)

    assert isinstance(results, dict)
    assert "error" in results


def test_smtp_probe_failure_is_reported_not_raised() -> None:
    """A failing SMTP transport is reported through the error field, not raised."""

    def connector(address, timeout):
        raise RuntimeError("hostile transport")

    results = smtp.run_smtp("127.0.0.1", connector=connector)

    assert isinstance(results, dict)
    assert "hostile transport" in (results.get("error") or "")


def test_scanner_probe_failure_is_reported_not_raised(monkeypatch) -> None:
    """A failing transport is reported as a closed port, not raised.

    The scanner reports a port it could not reach as a closed port; a
    transport failure of an unnamed type must not escape the scan.
    """

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.scanner.socket.create_connection", boom)

    assert scanner.scan_port("127.0.0.1", 80) == (80, False)
    assert scanner.scan_ports("127.0.0.1", [80, 443]) == [(80, False), (443, False)]


def test_dnsbrute_probe_failure_is_reported_not_raised(monkeypatch) -> None:
    """A failing zone-transfer transport is reported in the attempt, not raised."""

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.dnsbrute.socket.create_connection", boom)
    # The raw socket path is the one that is exercised here, whatever the
    # host has installed.
    monkeypatch.setattr("ethscan.dnsbrute.DNS_AVAILABLE", False)

    results = dnsbrute.run_dnsbrute(
        "example.com", nameservers=["127.0.0.1"], subdomains=[]
    )

    assert results["axfr_success"] is False
    assert "hostile transport" in (results["axfr"][0]["error"] or "")


@pytest.mark.parametrize("answer", HOSTILE_ANSWERS, ids=ANSWER_IDS)
def test_dnsbrute_hostile_answer_is_reported_not_raised(
    answer: bytes, monkeypatch
) -> None:
    """A hostile zone-transfer answer is reported, never raised."""

    class _AnsweringSocket:
        def __init__(self) -> None:
            self.answers = [answer]

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def settimeout(self, timeout):
            pass

        def sendall(self, data):
            pass

        def recv(self, size):
            if not self.answers:
                return b""
            return self.answers.pop(0)

    monkeypatch.setattr(
        "ethscan.dnsbrute.socket.create_connection",
        lambda *args, **kwargs: _AnsweringSocket(),
    )
    monkeypatch.setattr("ethscan.dnsbrute.DNS_AVAILABLE", False)

    results = dnsbrute.run_dnsbrute(
        "example.com", nameservers=["127.0.0.1"], subdomains=[]
    )

    assert results["axfr_success"] is False
    assert results["axfr"][0]["error"] is not None


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

    def send(self, data: bytes) -> int:
        self.sent += data
        return len(data)

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


@pytest.mark.parametrize("exc_type", [RuntimeError, TypeError], ids=["runtime_error", "type_error"])
def test_tls_probe_failure_is_reported_not_raised(monkeypatch, exc_type) -> None:
    """A failing TLS transport is reported per probe, not raised.

    Covers both a known transport type (RuntimeError, which the narrow tuple
    already caught) and an unnamed type (TypeError) that used to escape
    ``probe_version`` and ``probe_cipher`` and crash ``run_tls``.
    """

    def boom(*args, **kwargs):
        raise exc_type("hostile transport")

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


def test_ping_transport_failure_is_reported_not_raised(monkeypatch) -> None:
    """A failing TCP fallback socket is reported as a failed probe, not raised."""

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.ping.socket.socket", boom)

    results = ping.run_ping("127.0.0.1", count=1)

    assert isinstance(results, dict)
    probe = results["probes"][0]
    assert probe["response_type"] == ping.RESP_NO_RESPONSE
    assert "hostile transport" in (probe.get("error") or "")
    assert results["failed"] == 1


def test_osdetect_transport_failure_is_reported_not_raised(monkeypatch) -> None:
    """A failing TCP connect is reported as a NO-RESPONSE probe, not raised."""

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.osdetect.socket.create_connection", boom)

    results = osdetect.run_osdetect("127.0.0.1", ports=[80])

    assert isinstance(results, dict)
    probe = results["probes"][0]
    assert probe["response"] == "NO-RESPONSE"
    assert "hostile transport" in (probe.get("error") or "")


def test_resolve_transport_failure_is_reported_not_raised(monkeypatch) -> None:
    """A failing stdlib resolution is reported as empty records, not raised."""

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.resolve.socket.getaddrinfo", boom)

    results = resolve.run_resolve("example.com", record_types=["A"])

    assert isinstance(results, dict)
    assert results["records"]["A"] == []


def test_dns_transport_failure_is_reported_not_raised(monkeypatch) -> None:
    """A failing stdlib resolution is reported as empty records, not raised."""

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.dns.socket.getaddrinfo", boom)

    results = dns.run_dns("example.com")

    assert isinstance(results, dict)
    assert results["records"]["A"] == []


def test_stale_transport_failure_is_reported_not_raised(monkeypatch) -> None:
    """A failing stdlib resolution is reported as a stale domain, not raised."""

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.stale.socket.getaddrinfo", boom)

    results = stale.run_stale(["example.com"])

    assert isinstance(results, dict)
    entry = results["results"][0]
    assert entry["A"] == []
    assert entry["stale"] is True


def test_subdomains_transport_failure_is_reported_not_raised(monkeypatch) -> None:
    """A failing name lookup is reported as unresolved, not raised."""

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.subdomains.socket.gethostbyname", boom)

    results = subdomains.run_subdomains("example.com", subdomains=["www"])

    assert isinstance(results, dict)
    assert results["resolved"] == []
    assert all(entry["ip"] is None for entry in results["all_results"])
