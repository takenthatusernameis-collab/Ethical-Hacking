"""HTTP fuzzing module for ethscan."""
from __future__ import annotations

import csv
import http.client
import io
import json
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

from ethscan.fileio import read_lines
from ethscan.target import check_target_host, parse_url, strip_userinfo, url_port

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


def load_wordlist(path: str) -> list[str]:
    """Load wordlist from file, one path per line.

    Args:
        path: Path to wordlist file.

    Returns:
        List of paths (lines stripped, empty lines skipped).
    """
    return read_lines(path)


def _normalize_base_url(target: str) -> str:
    """Normalize target to a base URL with scheme.

    The userinfo of the target is dropped: ``urllib.request`` would keep it
    in the host it connects to, and ``http.client`` would read the text
    after the last colon of that host as the port.

    Raises:
        TargetSpecError: If the target carries an unusable host or port.
    """
    normalized = target.strip()
    if "://" not in normalized:
        normalized = "https://" + normalized
    check_target_host(normalized)
    parsed = parse_url(normalized)
    url_port(parsed)
    return f"{parsed.scheme}://{strip_userinfo(parsed.netloc)}"


def _join_url(base: str, path: str) -> str:
    """Join base URL with path, handling slashes correctly."""
    base = base.rstrip("/")
    path = path.lstrip("/")
    return f"{base}/{path}"


def fuzz_path(base_url: str, path: str, timeout: float = 5.0) -> dict[str, object]:
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
    except http.client.HTTPException as exc:
        # ``http.client.InvalidURL`` (raised for a path that holds a space or a
        # control character) derives from ``HTTPException`` and not from
        # ``ValueError``, so it escapes the ``except`` below. A path of a
        # wordlist that cannot be requested is a failed probe, not a crash.
        return {"path": path, "status_code": None, "error": str(exc)}
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return {"path": path, "status_code": None, "error": str(exc)}


def run_fuzz(
    target: str,
    wordlist: list[str] | None = None,
    timeout: float = 5.0,
    workers: int = 1,
) -> dict[str, object]:
    """Run HTTP fuzzing against target.

    Args:
        target: Target URL (e.g., https://example.com).
        wordlist: List of paths to test. If None, uses DEFAULT_WORDLIST.
        timeout: Per-request timeout in seconds.
        workers: Number of concurrent workers (default: 1).

    Returns:
        Structured results with target, base_url, and findings.
    """
    base_url = _normalize_base_url(target)
    paths = wordlist if wordlist is not None else DEFAULT_WORDLIST

    results: list[dict[str, object]] = []

    if workers <= 1:
        for path in paths:
            result = fuzz_path(base_url, path, timeout=timeout)
            results.append(result)
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_path = {
                executor.submit(fuzz_path, base_url, path, timeout=timeout): path
                for path in paths
            }
            for future in as_completed(future_to_path):
                results.append(future.result())

    # Sort results to maintain consistent order (by original path order)
    path_to_index = {path: i for i, path in enumerate(paths)}
    results.sort(key=lambda r: path_to_index.get(r.get("path", ""), 0))

    non_404 = [r for r in results if r.get("status_code") and r["status_code"] != 404]

    return {
        "target": target,
        "base_url": base_url,
        "paths_tested": len(paths),
        "findings": non_404,
        "all_results": results,
    }


def format_fuzz_report_json(data: dict[str, object]) -> str:
    """Format fuzz results as JSON."""
    return json.dumps(data, indent=2, default=str)


def format_fuzz_report_markdown(data: dict[str, object]) -> str:
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


def format_fuzz_report_csv(data: dict[str, object]) -> str:
    """Format fuzz results as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["target", "base_url", "path", "status_code", "error", "is_finding"])
    for result in data.get("all_results", []):
        status_code = result.get("status_code")
        is_finding = status_code is not None and status_code != 404
        writer.writerow([
            data.get("target", ""),
            data.get("base_url", ""),
            result.get("path", ""),
            status_code if status_code is not None else "",
            result.get("error") or "",
            "true" if is_finding else "false",
        ])
    return output.getvalue().rstrip("\r\n")