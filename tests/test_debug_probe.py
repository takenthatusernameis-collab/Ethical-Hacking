"""Temporary debug probe - to be deleted."""
import ethscan.cli
from ethscan.cli import cli
from click.testing import CliRunner
from unittest.mock import patch
import tempfile, os, sys


def test_debug_bound_at_collection() -> None:
    print("DEBUG probe ethscan.cli id:", id(ethscan.cli))
    print("DEBUG sys.modules ethscan.cli id:", id(sys.modules["ethscan.cli"]))
    print("DEBUG cli is ethscan.cli.cli:", cli is ethscan.cli.cli)
    radix_cmd = cli.commands["radix"]
    print("DEBUG radix callback module:", radix.callback.__module__)
    print("DEBUG radix callback globals is ethscan.cli:", radix.callback.__globals__ is ethscan.cli.__dict__)
    runner = CliRunner()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("10.0.0.0/8\n"); name = f.name
    try:
        with patch.object(ethscan.cli, "read_lines", side_effect=OSError("Permission denied")):
            print("DEBUG patched ethscan.cli.read_lines:", ethscan.cli.read_lines.__class__.__name__)
            print("DEBUG callback globals read_lines:", radix.callback.__globals__.get("read_lines").__class__.__name__)
            r = runner.invoke(cli, ["radix", "--cidr-file", name])
            print("DEBUG exit code:", r.exit_code)
    finally:
        os.unlink(name)
