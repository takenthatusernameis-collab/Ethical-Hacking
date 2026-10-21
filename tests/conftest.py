"""Shared fixtures for the permanent sweeps.

The option sweeps walk every command of the CLI with hostile option values.
Some of the commands reach the internet: the cert command fetches certificate
transparency data from a public API, the whois command talks to a whois
server, and the resolver of the machine running the tests may answer slowly
or not at all. Without the fixture below the sweeps depend on the latency of
those servers and trip their own per-invocation alarm.

The fixture keeps the sweeps off the internet: the HTTP transport and the
resolution of a name that is not a numeric address fail at once. Connections
to a numeric address stay untouched, so the commands that probe the local
target of the sweeps behave as they do otherwise.
"""
from __future__ import annotations

import socket

import pytest

#: The name resolution of the interpreter, kept before the fixture patches it.
_REAL_GETADDRINFO = socket.getaddrinfo
_REAL_GETHOSTBYNAME = socket.gethostbyname


@pytest.fixture
def no_external_network(monkeypatch) -> None:
    """Make the external network fail at once, so a sweep needs no internet.

    A name that is not a numeric address fails the way a name that does not
    resolve fails, and the HTTP transport fails the way it fails when the
    server cannot be reached. Both failures are the ones a command has to
    report, so the sweep keeps checking what it is meant to check.
    """

    def boom(*args, **kwargs):
        raise OSError("external network blocked")

    def unresolvable(*args, **kwargs):
        raise socket.gaierror("name does not resolve")

    def guarded_getaddrinfo(host, *args, **kwargs):
        try:
            socket.inet_aton(host)
        except (OSError, TypeError):
            unresolvable()
        return _REAL_GETADDRINFO(host, *args, **kwargs)

    def guarded_gethostbyname(host):
        try:
            socket.inet_aton(host)
        except (OSError, TypeError):
            unresolvable()
        return _REAL_GETHOSTBYNAME(host)

    monkeypatch.setattr("urllib.request.urlopen", boom)
    monkeypatch.setattr("socket.create_connection", boom)
    monkeypatch.setattr("socket.getaddrinfo", guarded_getaddrinfo)
    monkeypatch.setattr("socket.gethostbyname", guarded_gethostbyname)
