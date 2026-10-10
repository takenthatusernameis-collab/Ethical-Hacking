"""HTTP fuzzing module for ethscan."""

import json
import urllib.request
import urllib.error
import urllib.parse
from typing import Dict, List, Tuple, Optional


DEFAULT_WORDLIST = [
    "/admin",
    "/login",
    "/config",
    "/backup",
    "/test",
    "/dev",
    "/api",
    "/swagger",
    "/docs",
    "/robots.txt",
    "/sitemap.xml",
    "/.git",
    "/.env",
    "/phpinfo.php",
    "/server-status",
    "/actuator",
    "/health",
    "/metrics",
]


def load_wordlist(path: str) -> List[str]:
    """Load wordlist from file, one path per line.

    Args:
        path: Path to wordlist file.

    Returns:
        List of paths (lines stripped, empty lines skipped).
    """
    with open(path, "r", encoding="utf-8") as handle:
        return [line.strip() for line in handle if line.strip() and not line.startswith("#")]


def _normalize_base_url(target: str) -> str:
    """Normalize target to a base URL with scheme."""
    normalized = target.strip()
    if "://" not in normalized:
        normalized = "https://" + normalized
    parsed = urllib.parse.urlparse(normalized)
    return f"{parsed.scheme}://{parsed.netloc}"


def _join_url(base: str, path: str) -> str:
    """Join base URL with path, handling slashes correctly."""
    base = base.rstrip("/")
    path = path.lstrip("/")
    return f"{base}/{path}"


def fuzz_path(base_url: str, path: str, timeout: float = 5.0) -> Dict[str, object]:
    """Send a single HTTP request to a path and return result.

    Args:
        base_url: Base URL (e.g., https://example.com).
        path: Path to test (e.g., /admin).
        timeout: Request timeout in seconds.

    Returns:
        Dict with path, status_code, and error (if any).
    """
    url = _join_url(base_url, path)
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return {"path": path, "status_code": response.status, "error": None}
    except urllib.error.HTTPError as exc:
        return {"path": path, "status_code": exc.code, "error": None}
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return {"path": path, "status_code": None, "error": str(exc)}


def run_fuzz(
    target: str,
    wordlist: Optional[List[str]] = None,
    timeout: float = 5.0,
) -> Dict[str, object]:
    """Run HTTP fuzzing against target.

    Args:
        target: Target URL (e.g., https://example.com).
        wordlist: List of paths to test. If None, uses DEFAULT_WORDLIST.
        timeout: Per-request timeout in seconds.

    Returns:
        Structured results with target, base_url, and findings.
    """
    base_url = _normalize_base_url(target)
    paths = wordlist if wordlist is not None else DEFAULT_WORDLIST

    results: List[Dict[str, object]] = []
    for path in paths:
        result = fuzz_path(base_url, path, timeout=timeout)
        results.append(result)

    non_404 = [r for r in results if r.get("status_code") and r["status_code"] != 404]

    return {
        "target": target,
        "base_url": base_url,
        "paths_tested": len(paths),
        "findings": non_404,
        "all_results": results,
    }


def format_fuzz_report_json(data: Dict[str, object]) -> str:
    """Format fuzz results as JSON."""
    return json.dumps(data, indent=2, default=str)


def format_fuzz_report_markdown(data: Dict[str, object]) -> str:
    """Format fuzz results as Markdown."""
    lines = ["# ethscan HTTP Fuzz Report", ""]
    lines.append(f"- **Target:** {data['target']}")
    lines.append(f"- **Base URL:** {data['base_url']}")
    lines.append(f"- **Paths Tested:** {data['paths_tested']}")
    lines.append(f"- **Findings (non-404):** {len(data['findings'])}")
    lines.append("")

    if data["findings"]:
        lines.append("## Findings")
        lines.append("| Path | Status Code |")
        lines.append("|------|-------------|")
        for finding in data["findings"]:
            code = finding["status_code"]
            path = finding["path"]
            lines.append(f"| {path} | {code} |")
        lines.append("")

    lines.append("## All Results")
    lines.append("| Path | Status Code | Error |")
    lines.append("|------|-------------|-------|")
    for result in data["all_results"]:
        code = result["status_code"] if result["status_code"] is not None else "N/A"
        error = result["error"] or ""
        lines.append(f"| {result['path']} | {code} | {error} |")

    return "\n".join(lines)