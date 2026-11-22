"""Version information module for ethscan."""

from __future__ import annotations

import csv
import io
import json
import platform
import sys
from pathlib import Path
from typing import Any

from ethscan import __version__
from ethscan.config import find_config_file


def _collect_version_data() -> dict[str, Any]:
    """Collect version and dependency information."""
    try:
        import click as click_module
        click_version = str(click_module.__version__)
    except (ImportError, AttributeError):
        click_version = "unknown"

    try:
        import yaml
        yaml_version = str(yaml.__version__)
    except (ImportError, AttributeError):
        yaml_version = "unknown"

    try:
        import dns
        dns_version = str(dns.__version__)
    except (ImportError, AttributeError):
        dns_version = "not installed"

    config_path = find_config_file(None)
    cache_path = Path.home() / ".cache" / "ethscan"

    dependencies: dict[str, str] = {
        "click": click_version,
        "pyyaml": yaml_version,
        "dnspython": dns_version,
    }
    return {
        "version": __version__,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "dependencies": dependencies,
        "config_file": str(config_path) if config_path else "not found",
        "cache_directory": str(cache_path),
    }


def _as_dict(value: object) -> dict[str, Any]:
    """Return value as a dict, or an empty dict for hostile non-dict input."""
    return value if isinstance(value, dict) else {}


def format_version_report_json(data: object) -> str:
    """Render version information as a JSON string."""
    data = _as_dict(data)
    return json.dumps(data, indent=2) + "\n"


def format_version_report_csv(data: object) -> str:
    """Render version information as a CSV string."""
    data = _as_dict(data)
    output_io = io.StringIO()
    writer = csv.writer(output_io)
    writer.writerow(["key", "value"])
    writer.writerow(["version", data.get("version", "")])
    writer.writerow(["python", data.get("python", "")])
    writer.writerow(["platform", data.get("platform", "")])
    writer.writerow(["architecture", data.get("architecture", "")])
    dependencies = data.get("dependencies", {})
    for dep, ver in dependencies.items():
        writer.writerow([f"dep.{dep}", ver])
    writer.writerow(["config_file", data.get("config_file", "")])
    writer.writerow(["cache_directory", data.get("cache_directory", "")])
    return output_io.getvalue()


def format_version_report_markdown(data: object) -> str:
    """Render version information as a Markdown string."""
    data = _as_dict(data)
    dependencies = data.get("dependencies", {})
    lines = [
        "# ethscan Version Report",
        "",
        f"- **Version:** {data.get('version', '')}",
        f"- **Python:** {data.get('python', '')} ({data.get('platform', '')}, {data.get('architecture', '')})",
        "",
        "## Dependencies",
        "",
        "| Dependency | Version |",
        "|------------|---------|",
        f"| click | {dependencies.get('click', '')} |",
        f"| pyyaml | {dependencies.get('pyyaml', '')} |",
        f"| dnspython | {dependencies.get('dnspython', '')} |",
        "",
        "## Configuration",
        "",
        f"- **Config file:** {data.get('config_file', '')}",
        f"- **Cache directory:** {data.get('cache_directory', '')}",
    ]
    return "\n".join(lines) + "\n"


def get_version_data() -> dict[str, Any]:
    """Get the version data dictionary (for direct use by CLI)."""
    return _collect_version_data()