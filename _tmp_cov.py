import tempfile, os, coverage
cov = coverage.Coverage(source=["ethscan"])
cov.start()
from click.testing import CliRunner
from ethscan.cli import cli

config = """
commands:
  ping:
    bogus_key: 123
    count: 1
"""
with tempfile.TemporaryDirectory() as d:
    cfg = os.path.join(d, "ethscan.yaml")
    with open(cfg, "w") as f:
        f.write(config)
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(cli, ["--config", cfg, "ping", "--target", "127.0.0.1"])
    print("EXIT:", result.exit_code)
cov.stop()
cov.save()
cov.report(include=["ethscan/cli.py"], show_missing=True)
