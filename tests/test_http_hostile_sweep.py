"""Permanent sweep test: a hostile HTTP answer is reported, never raised.

The HTTP-facing commands talk to servers that answer with whatever they like,
and the transport itself can fail in a way the module does not name. Every
command answers such an answer with a result and reports the failure through
its own failure field, instead of letting it escape as a traceback.

Three checks per command:

* every body in ``HOSTILE_BODIES`` is answered with a result and never with a
  traceback: the parsers are reached with the bytes a hostile server can
  send;
* a transport that fails with a type the guard does not name does not take
  the command down;
* that failure is reported through the command's own failure field.

The commands whose failure has no field of its own (``cve`` and ``subtake``
report a failed lookup as a missing entry) are covered by the first two
checks only.
"""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any, Callable

import pytest

from ethscan import cert, cve, fuzz, geo, headers, mac, s3, subtake, urlcheck, web

#: A target that is never reached: every command below drives its own
#: transport, so the target only has to be well formed.
TARGET = "http://127.0.0.1:9/"

#: The bodies a hostile server can send: a body that is not what the caller
#: expects, a body that is not text, a body that nests deeper than the
#: parser can read, and a body that is not a document at all.
HOSTILE_BODIES: tuple[bytes, ...] = (
    b"",
    b"not json at all",
    b"[]",
    b"null",
    b"123",
    b"[" * 2000 + b"]" * 2000,
    bytes(range(256)),
    b"<html><body>hostile</body></html>",
)

BODY_IDS = [f"body{index}" for index in range(len(HOSTILE_BODIES))]


class _FakeResponse:
    """A stand-in for the response of ``urllib.request.urlopen``."""

    def __init__(self, body: bytes, status: int = 200) -> None:
        self.body = body
        self.status = status
        self.headers = {"Content-Type": "text/html", "Server": "hostile"}

    def read(self) -> bytes:
        return self.body

    def getcode(self) -> int:
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _responder(body: bytes) -> Callable[..., _FakeResponse]:
    """Return a stand-in for ``urlopen`` that answers with *body*."""

    def urlopen(*_args: Any, **_kwargs: Any) -> _FakeResponse:
        return _FakeResponse(body)

    return urlopen


def _run_web(monkeypatch, tmp_path: Path) -> dict[str, Any]:
    return web.run_web_checks(TARGET, ["headers", "info_disclosure"], timeout=1.0)


def _run_headers(monkeypatch, tmp_path: Path) -> dict[str, Any]:
    return headers.run_headers(TARGET, timeout=1.0)


def _run_fuzz(monkeypatch, tmp_path: Path) -> dict[str, Any]:
    return fuzz.run_fuzz(TARGET, wordlist=["/admin", "/login"], timeout=1.0)


def _run_urlcheck(monkeypatch, tmp_path: Path) -> dict[str, Any]:
    return urlcheck.run_urlcheck(
        TARGET, ["headers"], wordlist=["/admin"], fuzz_paths=True, timeout=1.0
    )


def _run_cert(monkeypatch, tmp_path: Path) -> dict[str, Any]:
    # A numeric host is resolved without a DNS answer.
    return cert.run_cert("127.0.0.1", timeout=1.0, use_cache=False)


def _run_geo(monkeypatch, tmp_path: Path) -> dict[str, Any]:
    return geo.run_geo("8.8.8.8", timeout=1.0, use_cache=False)


def _run_mac(monkeypatch, tmp_path: Path) -> dict[str, Any]:
    return mac.run_mac("00:1A:2B:3C:4D:5E", timeout=1.0, use_cache=False)


def _run_cve(monkeypatch, tmp_path: Path) -> dict[str, Any]:
    services = tmp_path / "services.json"
    services.write_text(
        json.dumps({"services": [{"port": 22, "banner": "OpenSSH_7.2"}]})
    )
    return cve.run_cve(
        "127.0.0.1", services_file=str(services), timeout=1.0, use_cache=False
    )


def _run_s3(monkeypatch, tmp_path: Path) -> dict[str, Any]:
    monkeypatch.setattr(s3, "_resolve_s3_endpoint", lambda *a, **kw: "127.0.0.1")
    return s3.run_s3("example.com", wordlist=["mybucket"], timeout=1.0)


def _run_subtake(monkeypatch, tmp_path: Path) -> dict[str, Any]:
    monkeypatch.setattr(
        subtake, "resolve_cname", lambda *a, **kw: "victim.azurewebsites.net"
    )
    monkeypatch.setattr(subtake, "resolve_a_records", lambda *a, **kw: ["127.0.0.1"])
    monkeypatch.setattr(subtake, "resolve_aaaa_records", lambda *a, **kw: [])
    monkeypatch.setattr(
        subtake,
        "check_takeover_signature",
        lambda *a, **kw: {
            "service": "Azure",
            "fingerprint": "azurewebsites",
            "description": "hostile",
        },
    )
    return subtake.run_subtake(
        "example.com", subdomains=["www"], timeout=1.0, http_timeout=1.0
    )


#: The HTTP-facing commands, the way each of them is driven, and the field
#: each of them uses to report a failure. A command whose failure has no
#: field of its own reports it as a missing entry and is listed with ``None``.
COMMANDS: tuple[
    tuple[str, Callable[[Any, Path], dict[str, Any]], Callable[[dict[str, Any]], str] | None],
    ...,
] = (
    ("web", _run_web, lambda result: str(result.get("error") or "")),
    ("headers", _run_headers, lambda result: str(result.get("error") or "")),
    (
        "fuzz",
        _run_fuzz,
        lambda result: " ".join(
            str(entry.get("error") or "") for entry in result.get("all_results", [])
        ),
    ),
    (
        "urlcheck",
        _run_urlcheck,
        lambda result: str(result.get("web", {}).get("error") or ""),
    ),
    (
        "cert",
        _run_cert,
        lambda result: str(result.get("cert_data", {}).get("error") or ""),
    ),
    (
        "geo",
        _run_geo,
        lambda result: str(result.get("geolocation", {}).get("error") or ""),
    ),
    (
        "mac",
        _run_mac,
        lambda result: str(result.get("mac_data", {}).get("error") or ""),
    ),
    (
        "s3",
        _run_s3,
        lambda result: " ".join(
            str(entry.get("error") or "") for entry in result.get("results", [])
        ),
    ),
    ("cve", _run_cve, None),
    ("subtake", _run_subtake, None),
)

MODULE_IDS = [name for name, _runner, _error_of in COMMANDS]
REPORTING_COMMANDS = [entry for entry in COMMANDS if entry[2] is not None]
REPORTING_IDS = [name for name, _runner, _error_of in REPORTING_COMMANDS]


@pytest.mark.parametrize("body", HOSTILE_BODIES, ids=BODY_IDS)
@pytest.mark.parametrize("name,runner,error_of", COMMANDS, ids=MODULE_IDS)
def test_hostile_body_is_answered_with_a_result(
    name: str, runner, error_of, body: bytes, monkeypatch, tmp_path: Path
) -> None:
    """A hostile body is answered with a result, never with a traceback."""
    monkeypatch.setattr(urllib.request, "urlopen", _responder(body))

    results = runner(monkeypatch, tmp_path)

    assert isinstance(results, dict)


@pytest.mark.parametrize("name,runner,error_of", COMMANDS, ids=MODULE_IDS)
def test_failing_transport_does_not_take_the_command_down(
    name: str, runner, error_of, monkeypatch, tmp_path: Path
) -> None:
    """A transport failure of an unnamed type does not take the command down."""

    def boom(*_args: Any, **_kwargs: Any):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr(urllib.request, "urlopen", boom)

    results = runner(monkeypatch, tmp_path)

    assert isinstance(results, dict)


@pytest.mark.parametrize("name,runner,error_of", REPORTING_COMMANDS, ids=REPORTING_IDS)
def test_failing_transport_is_reported_through_the_own_field(
    name: str, runner, error_of, monkeypatch, tmp_path: Path
) -> None:
    """A failing transport is reported through the command's own failure field."""

    def boom(*_args: Any, **_kwargs: Any):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr(urllib.request, "urlopen", boom)

    results = runner(monkeypatch, tmp_path)

    assert error_of(results)
