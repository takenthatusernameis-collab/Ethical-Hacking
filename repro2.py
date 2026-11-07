import importlib, runpy, sys, contextlib
import ethscan.cli as cli_mod
print("initial ethscan.cli id:", id(cli_mod))

# test_main logic
saved_argv = sys.argv
sys.argv = ["ethscan.cli", "brute", "--target", "127.0.0.1", "--user-file", "/tmp/u.txt", "--pass-file", "/tmp/p.txt", "--timeout", "1.0"]
open("/tmp/u.txt","w").write("admin\n"); open("/tmp/p.txt","w").write("admin\n")
sys.modules.pop("ethscan.cli", None)
with contextlib.suppress(SystemExit):
    runpy.run_module("ethscan.cli", run_name="__main__")
sys.argv = saved_argv
import ethscan.cli as cli_mod2
print("after main ethscan.cli id:", id(cli_mod2))

# test_netbios logic
from ethscan import netbios
from ethscan.cli import cli
print("cli is cli_mod2.cli:", cli is cli_mod2.cli)
from click.testing import CliRunner
from unittest.mock import patch
runner = CliRunner()
with patch.object(netbios, "_send_recv", return_value=(b"x", None)):
    r2 = runner.invoke(cli, ["netbios", "--target", "192.168.1.100"])
print("netbios exit:", r2.exit_code, "exception:", type(r2.exception).__name__ if r2.exception else None)

# radix scenario
import tempfile, os
with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
    f.write("10.0.0.0/8\n"); name = f.name
try:
    with patch.object(cli_mod2, "read_lines", side_effect=OSError("Permission denied")):
        r = runner.invoke(cli, ["radix", "--cidr-file", name])
        print("RADIX EXIT CODE:", r.exit_code)
finally:
    os.unlink(name)
