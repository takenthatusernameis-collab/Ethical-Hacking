import importlib, runpy, sys, contextlib
import ethscan.cli as cli_mod
print("initial ethscan.cli id:", id(cli_mod))
print("initial read_lines is cli_mod.read_lines:", cli_mod.read_lines)

# simulate test_main: test_cli_module_as_main_runs_the_brute_command
saved_argv = sys.argv
sys.argv = ["ethscan.cli", "brute", "--target", "127.0.0.1", "--user-file", "/tmp/u.txt", "--pass-file", "/tmp/p.txt", "--timeout", "1.0"]
sys.modules.pop("ethscan.cli", None)
with contextlib.suppress(SystemExit):
    runpy.run_module("ethscan.cli", run_name="__main__")
sys.argv = saved_argv
import ethscan.cli as cli_mod2
print("after runpy ethscan.cli id:", id(cli_mod2), "same as initial:", cli_mod2 is cli_mod)

# simulate test_netbios: from ethscan.cli import cli at runtime
from ethscan.cli import cli
print("cli is cli_mod2.cli:", cli is cli_mod2.cli)

# now the radix scenario
from click.testing import CliRunner
import tempfile, os
from unittest.mock import patch
with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
    f.write("10.0.0.0/8\n"); name = f.name
try:
    print("read_lines before patch is cli_mod2.read_lines:", cli_mod2.read_lines)
    with patch.object(cli_mod2, "read_lines", side_effect=OSError("Permission denied")):
        print("read_lines during patch:", cli_mod2.read_lines)
        runner = CliRunner()
        r = runner.invoke(cli, ["radix", "--cidr-file", name])
        print("EXIT CODE:", r.exit_code)
finally:
    os.unlink(name)
