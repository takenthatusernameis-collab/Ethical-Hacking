from __future__ import annotations

from ethscan import service


def test_service_format_markdown_hostile_top_level_none() -> None:
    md = service.format_service_report_markdown(None)  # type: ignore[arg-type]
    assert isinstance(md, str)


def test_service_format_csv_hostile_top_level_none() -> None:
    csv_out = service.format_service_report_csv(None)  # type: ignore[arg-type]
    assert isinstance(csv_out, str)
    # Header only
    assert csv_out.startswith("port,service,banner")


def test_service_format_markdown_hostile_nested() -> None:
    data = {"target": "x", "host": "x", "ports_scanned": 0, "services_found": 0, "results": [None, [], "bad", {"port": 80}]}
    md = service.format_service_report_markdown(data)
    assert isinstance(md, str)
    assert "80" in md


def test_service_format_csv_hostile_nested() -> None:
    data = {"target": "x", "host": "x", "ports_scanned": 1, "services_found": 1, "results": [None, "bad", {"port": 22, "banner": "SSH"}]}
    csv_out = service.format_service_report_csv(data)
    assert isinstance(csv_out, str)
    assert "22" in csv_out
