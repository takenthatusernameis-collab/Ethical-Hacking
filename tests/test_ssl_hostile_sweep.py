"""Permanent sweep test: a hostile TLS/certificate answer is reported, never raised.

``ethscan.ssl`` inspects a server's TLS certificate over a socket. A hostile
endpoint can return malformed certificate structures (decoded dicts with
unexpected types/shapes), bad dates, or fail the transport in unnamed ways.
``run_ssl``/``inspect_certificate`` must answer every hostile case with a
structured result dict and never raise.
"""
from __future__ import annotations

from typing import Any

import pytest

from ethscan import ssl


TARGET = "example.com"

HOSTILE_CERTS: tuple[Any, ...] = (
    None,
    {},
    {"subject": "not-a-tuple"},
    {"subject": [("weird",)], "issuer": "x", "subjectAltName": "nope"},
    {"subject": [(("CN", None),)], "issuer": [(("O", 123),)], "notAfter": 12345},
    {"subjectAltName": [("DNS", None), ("IP", "1.2.3.4"), "garbage", ("DNS",)]},
    {"signatureAlgorithm": 123, "publicKeyInfo": "bad"},
    {"publicKeyInfo": {"bits": "notint"}},
    {"issuer": None, "subject": None, "notAfter": "bad-date"},
    {"subject": [(("CN", "a" * 5000),)], "sans": ["x"]},
    {"notBefore": 0, "notAfter": 0, "subjectAltName": [("DNS", "a" * 2000)]},
    {"signatureAlgorithm": (), "publicKeyInfo": {"size": "x"}},
)


class _FakeConn:
    def __enter__(self):
        return object()

    def __exit__(self, *args):
        return False


class _FakeSSLSock:
    def getpeercert(self, binary=False):
        if binary:
            return b"garbage"
        return {}

    def get_verified_chain(self):
        return []


class _FakeWrapped:
    def __init__(self, cert_dict):
        self._cert = cert_dict

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def getpeercert(self, binary=False):
        if binary:
            return b"garbage"
        return self._cert or {}

    def get_verified_chain(self):
        return []


class _FakeCtx:
    def __init__(self, cert_dict):
        self._cert = cert_dict

    def wrap_socket(self, sock, server_hostname=None):
        return _FakeWrapped(self._cert)


@pytest.mark.parametrize(
    "cert_dict", HOSTILE_CERTS, ids=[f"cert{i}" for i in range(len(HOSTILE_CERTS))]
)
def test_hostile_decoded_cert_is_reported_not_raised(monkeypatch, cert_dict) -> None:
    monkeypatch.setattr("ethscan.ssl.socket.create_connection", lambda *a, **k: _FakeConn())
    monkeypatch.setattr(ssl, "_build_context", lambda verify=True: _FakeCtx(cert_dict))
    monkeypatch.setattr(ssl, "_decode_cert", lambda ssock: cert_dict)

    result = ssl.run_ssl(TARGET)

    assert isinstance(result, dict)
    assert result.get("host") == "example.com"
    assert result.get("target") == TARGET
    assert "error" in result
    assert "cert" in result


@pytest.mark.parametrize("exc_type", [RuntimeError, TypeError, OSError, KeyError])
def test_transport_failure_is_reported_not_raised(monkeypatch, exc_type) -> None:
    def boom(*args, **kwargs):
        raise exc_type("hostile transport")

    monkeypatch.setattr("ethscan.ssl.socket.create_connection", boom)

    result = ssl.run_ssl(TARGET)

    assert isinstance(result, dict)
    assert result.get("host") == "example.com"
    assert result["error"] is not None
    assert "hostile transport" in str(result["error"])


def test_retry_path_hostile_failure_reported_not_raised(monkeypatch) -> None:
    calls = {"n": 0}

    def wrap(host, port, timeout, context, server_hostname=None):
        calls["n"] += 1
        raise RuntimeError("hostile handshake")

    monkeypatch.setattr(ssl, "_wrap_socket", wrap)

    result = ssl.inspect_certificate(TARGET)

    assert isinstance(result, dict)
    assert result["error"]
