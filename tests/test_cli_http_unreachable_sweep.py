"""Permanent CLI-level sweep for the HTTP-facing commands."""
from __future__ import annotations

import json
import socket
import urllib.request
from typing import Any

import pytest
from click.testing import CliRunner

from ethscan import cli

UNREACHABLE = "http://127.0.0.1:9/"


@pytest.fixture(autouse=True)
def _restore_default_socket_timeout():
    original = socket.getdefaulttimeout()
    yield
    socket.setdefaulttimeout(original)


def _run_cli(args):
    result = CliRunner().invoke(cli.cli, args)
    assert result.exit_code == 0, f"{args} exited {result.exit_code}:\n{result.output}"
    assert "Traceback (most recent call last)" not in result.output
    return json.loads(result.output)


def _boom(*a, **k):
    raise RuntimeError("hostile transport")


def test_web(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    monkeypatch.setattr("ethscan.ssl.socket.create_connection", _boom)
    r = _run_cli(["web", "--target", UNREACHABLE, "--checks", "headers", "--output-format", "json"])
    assert r.get("error")


def test_headers(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    r = _run_cli(["headers", "--target", UNREACHABLE, "--output-format", "json"])
    assert r.get("error")


def test_fuzz(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    r = _run_cli(["fuzz", "--target", UNREACHABLE, "--wordlist", "/dev/null", "--output-format", "json"])
    # may need wordlist; fallback built-in if file empty? try


def test_urlcheck(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    monkeypatch.setattr("ethscan.ssl.socket.create_connection", _boom)
    r = _run_cli(["urlcheck", "--target", UNREACHABLE, "--output-format", "json"])
    assert (r.get("web") or {}).get("error")


def test_cert(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    r = _run_cli(["cert", "--target", "127.0.0.1", "--output-format", "json"])
    assert (r.get("cert_data") or {}).get("error")


def test_geo(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    r = _run_cli(["geo", "--target", "8.8.8.8", "--output-format", "json"])
    assert (r.get("geolocation") or {}).get("error")


def test_mac(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    r = _run_cli(["mac", "--target", "00:1A:2B:3C:4D:5E", "--output-format", "json"])
    assert (r.get("mac_data") or {}).get("error")


def test_s3(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    r = _run_cli(["s3", "--target", UNREACHABLE, "--output-format", "json"])
    errs = " ".join(str(e.get("error") or "") for e in r.get("results", []))
    assert errs.strip()


def test_cve(monkeypatch, tmp_path):
    import pathlib
    sf = tmp_path / "services.json"
    sf.write_text('{"services":[{"port":22,"banner":"OpenSSH_7.2"}]}')
    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    r = _run_cli(["cve", "--target", "127.0.0.1", "--services-file", str(sf), "--output-format", "json"])
    assert r.get("error")


def test_subtake(monkeypatch, tmp_path):
    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    r = _run_cli(["subtake", "--target", UNREACHABLE, "--output-format", "json"])
    assert r.get("vulnerable_count") == 0
    assert r.get("vulnerable") == []
"""
"""
