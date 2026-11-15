"""Focused branch-coverage tests for ethscan.subdomains."""

from __future__ import annotations

from concurrent.futures import Future
from typing import Any

import ethscan.subdomains as subdomains_mod
from ethscan.subdomains import (
    format_subdomains_report_csv,
    format_subdomains_report_markdown,
    run_subdomains,
)


def test_enumerate_depth_future_exception_missing_label(monkeypatch) -> None:
    """Cover 182->173: exception path where future not in future_to_label."""

    def fake_as_completed(futures):  # noqa: ANN001
        bad: Future[Any] = Future()
        bad.set_exception(RuntimeError("boom"))
        yield bad
        yield from list(futures)

    monkeypatch.setattr(subdomains_mod, "as_completed", fake_as_completed)
    monkeypatch.setattr(
        subdomains_mod,
        "resolve_subdomain",
        lambda subdomain, domain, timeout=2.0, resolver=None: (subdomain, "1.2.3.4"),
    )

    result = run_subdomains("example.com", subdomains=["www"], recursive=False)
    # unknown future had no mapped label so it should be ignored; normal result kept
    assert result["resolved_count"] == 1
    assert result["all_results"][0]["hostname"] == "www.example.com"


def test_run_subdomains_recursive_multiple_resolved_bases(monkeypatch) -> None:
    """Exercise recursive enumeration across multiple resolved base domains."""

    def fake_resolve(
        subdomain: str,
        domain: str,
        timeout: float = 2.0,
        resolver: str | None = None,
    ):
        hostname = f"{subdomain}.{domain}"
        if hostname == "www.example.com":
            return subdomain, "1.2.3.4"
        if hostname == "api.www.example.com":
            # resolves at depth 1 under base www.example.com
            return subdomain, "2.2.2.2"
        if hostname == "api.example.com":
            # also resolves at depth 0, producing a second base domain for depth 1
            return subdomain, "3.3.3.3"
        return subdomain, None

    monkeypatch.setattr(subdomains_mod, "resolve_subdomain", fake_resolve)

    result = run_subdomains(
        "example.com",
        subdomains=["www", "api"],
        recursive=True,
        max_depth=1,
    )

    hostnames = [r["hostname"] for r in result["all_results"]]
    assert hostnames.count("api.example.com") == 1
    assert "api.www.example.com" in hostnames
    depth1 = result["per_depth"][1]
    assert depth1["depth"] == 1
    assert depth1["subdomains_tested"] == 4  # 2 resolved base domains * 2 labels
    assert any(r["hostname"] == "api.www.example.com" for r in depth1["results"])


def test_format_subdomains_markdown_truthy_nonlist_sections() -> None:
    """Cover formatter false branches where sections are truthy but not lists."""
    data: dict[str, Any] = {
        "target": "example.com",
        "domain": "example.com",
        "recursive": True,
        "max_depth": 1,
        "resolved": "bad",
        "all_results": "bad",
        "per_depth": "bad",
    }
    md = format_subdomains_report_markdown(data)
    assert "## Resolved Subdomains" in md
    assert "## All Results" in md
    assert "## Recursive Enumeration (Per Depth)" in md
    # per_depth was truthy but not a list, so no depth subsections rendered
    assert "### Depth 1" not in md


def test_format_subdomains_csv_truthy_nonlist_all_results() -> None:
    """Cover 361->371: CSV all_results truthy but not a list."""
    data: dict[str, Any] = {
        "target": "example.com",
        "domain": "example.com",
        "all_results": "bad",
    }
    csv_text = format_subdomains_report_csv(data)
    assert csv_text.splitlines() == ["subdomain,hostname,ip,resolved"]
