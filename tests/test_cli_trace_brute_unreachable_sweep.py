"""Permanent CLI-level sweep: trace and brute report a hostile transport."""
from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest
from click.testing import CliRunner

from ethscan import cli


@pytest.fixture(autouse=True)
def _restore_default_socket_timeout():
    original = socket.getdefaulttimeout()
    yield
    socket.setdefaulttimeout(original)


def _run_cli(args: list[str]) -> dict:
    result = CliRunner().invoke(cli.cli, args)
    assert result.exit_code == 0, f"{args} exited {result.exit_code}:\n{result.output}"
    assert "Traceback (most recent call last)" not in result.output
    return json.loads(result.output)


def test_trace_cli_hostile_gethostbyname(monkeypatch) -> None:
    class Boom(Exception):
        pass

    def boom(*a, **k):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.trace.socket.gethostbyname", boom)
    data = _run_cli(["trace", "--target", "example.com", "--timeout", "1.0"])
    assert data["error"] == "hostile transport"
    assert data["reached"] is False


def test_trace_cli_hostile_socket(monkeypatch) -> None:
    def boom(*a, **k):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.trace.socket.socket", boom)
    data = _run_cli(["trace", "--target", "127.0.0.1", "--timeout", "1.0"])
    assert data["error"] == "hostile transport"


def test_brute_cli_hostile_ftp(monkeypatch, tmp_path: Path) -> None:
    class FakeFTP:
        def __init__(self, *a, **k):
            pass

        def connect(self, *a, **k):
            raise RuntimeError("hostile transport")

        def close(self):
            pass

    monkeypatch.setattr("ethscan.brute.FTP", FakeFTP)
    monkeypatch.setattr("ftplib.FTP", FakeFTP)

    uf = tmp_path / "u.txt"
    pf = tmp_path / "p.txt"
    uf.write_text("admin\n")
    pf.write_text("admin\n")

    data = _run_cli(
        [
            "brute",
            "--target",
            "127.0.0.1",
            "--user-file",
            str(uf),
            "--pass-file",
            str(pf),
            "--timeout",
            "1.0",
        ]
    )
    assert data["attempts"] == 1
    assert data["successful_count"] == 0
    assert data["results"][0]["error"] == "hostile transport"
