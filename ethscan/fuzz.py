"""HTTP fuzzing module for ethscan."""
from __future__ import annotations

import csv
import http.client
import io
import json
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import cast
from urllib.parse import SplitResult

from ethscan.fileio import read_lines
from ethscan.target import TargetSpecError, check_target_host, parse_url, strip_userinfo, url_port

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
    url_port(cast("SplitResult", parsed))
    host = parsed.hostname or parsed.netloc or ""
    if not host:
        raise TargetSpecError(f"Could not parse host from target {target!r}")
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
    except Exception as exc:  # noqa: BLE001 - urlopen can raise any failure
        # A transport failure of a type the guard does not name must not take
        # the command down: the path is a failed probe, not a crash.
        return {"path": path, "status_code": None, "error": str(exc) or exc.__class__.__name__}


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
    # A wordlist handed in from a cache or pipeline can hold hostile entries
    # (ints, None, lists): a path that is not a string is a skipped probe, not
    # a crash of the command.
    paths = [p for p in paths if isinstance(p, str)]

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
    results.sort(key=lambda r: path_to_index.get(cast("str", r.get("path", "")), 0))

    non_404 = []
    for r in results:
        status_code = cast("int | None", r.get("status_code"))
        if status_code is not None and status_code != 404:
            non_404.append(r)

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
    if not isinstance(data, dict):
        lines.append("*No structured report data.*")
        return "\n".join(lines)
    lines.append(f"- **Target:** {data.get('target', '')}")
    lines.append(f"- **Base URL:** {data.get('base_url', '')}")
    lines.append(f"- **Paths Tested:** {data.get('paths_tested', 0)}")
    findings_list = data.get("findings") or []
    if not isinstance(findings_list, list):
        findings_list = []
    lines.append(f"- **Findings (non-404):** {len(findings_list)}")
    lines.append("")

    if findings_list:
        lines.append("## Findings")
        lines.append("| Path | Status Code |")
        lines.append("|------|-------------|")
        for finding in findings_list:
            if not isinstance(finding, dict):
                continue
            code = finding.get("status_code", "N/A")
            path = finding.get("path", "")
            lines.append(f"| {path} | {code} |")
        lines.append("")

    lines.append("## All Results")
    lines.append("| Path | Status Code | Error |")
    lines.append("|------|-------------|-------|")
    all_results_list = data.get("all_results") or []
    if isinstance(all_results_list, list):
        for result in all_results_list:
            if not isinstance(result, dict):
                continue
            code = result.get("status_code") if result.get("status_code") is not None else "N/A"
            error = result.get("error") or ""
            lines.append(f"| {result.get('path', '')} | {code} | {error} |")

    return "\n".join(lines)


def format_fuzz_report_csv(data: dict[str, object]) -> str:
    """Format fuzz results as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["target", "base_url", "path", "status_code", "error", "is_finding"])
    all_results_data = data.get("all_results") if isinstance(data, dict) else None
    if not isinstance(all_results_data, list):
        all_results_data = []
    for result in all_results_data:
        if not isinstance(result, dict):
            continue
        status_code = result.get("status_code")
        is_finding = status_code is not None and status_code != 404
        writer.writerow([
            data.get("target", "") if isinstance(data, dict) else "",
            data.get("base_url", "") if isinstance(data, dict) else "",
            result.get("path", ""),
            status_code if status_code is not None else "",
            result.get("error") or "",
            "true" if is_finding else "false",
        ])

    # A findings section mirroring the Markdown report: every non-404 result
    # is listed as a finding. The all_results table above already marks each
    # row with is_finding, but a reader filtering by the "finding" section
    # header gets the same list the Markdown and JSON reports show.
    findings = data.get("findings") or [] if isinstance(data, dict) else []
    if isinstance(findings, list) and findings:
        writer.writerow([])
        writer.writerow(["finding_path", "finding_status_code"])
        for finding in findings:
            if isinstance(finding, dict):
                writer.writerow([
                    finding.get("path", ""),
                    finding.get("status_code", ""),
                ])

    return output.getvalue().rstrip("\r\n")