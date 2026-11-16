"""Focused branch-coverage tests for ethscan.s3.

Closes reachable partial branches identified in branch-coverage analysis of
ethscan/s3.py.

Covered in this file (reachable):
- 294->328: a response that is neither 200 nor 403 (e.g. 204) leaves
  exists=True, public=False, and returns without an error.
- 297->298: a non-2xx, non-403 status returned directly by urlopen (e.g. 418)
  is reported as an unexpected status in the result error field.
- 306->310: an HTTPError whose status is not 403/404/400 (e.g. 500) is
  recorded as the status code with an in-band error.
- 314->315: an HTTPError whose status is not 403/404/400/5xx (e.g. 418) is
  reported as an unexpected status in the result error field.
"""
from __future__ import annotations

import urllib.error
from email.message import Message
from typing import Any

from ethscan.s3 import check_bucket_public


class _FakeResponse:
    def __init__(self, status: int) -> None:
        self._status = status

    def getcode(self) -> int:
        return self._status

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None


def _mock_dns(resolved: str | None = "1.2.3.4") -> Any:
    return lambda bucket_name, region, timeout=5.0: resolved


def test_check_bucket_public_unexpected_success_status(monkeypatch) -> None:
    # 294->328: urlopen returns a non-200/non-403 2xx status without raising.
    monkeypatch.setattr("ethscan.s3._resolve_s3_endpoint", _mock_dns("1.2.3.4"))
    monkeypatch.setattr(
        "ethscan.s3.urllib.request.urlopen",
        lambda req, timeout=None: _FakeResponse(204),
    )
    result = check_bucket_public("mybucket", "us-east-1", 1.0)
    assert result["status_code"] == 204
    assert result["exists"] is True
    assert result["public"] is False
    assert result["error"] is None


def test_check_bucket_public_http_error_unhandled_status(monkeypatch) -> None:
    # 306->310: an HTTPError with a 5xx status is recorded with an error.
    monkeypatch.setattr("ethscan.s3._resolve_s3_endpoint", _mock_dns("1.2.3.4"))

    def _raise(req: object, timeout: float | None = None) -> Any:
        raise urllib.error.HTTPError(
            "https://x", 500, "Server Error", Message(), None
        )

    monkeypatch.setattr("ethscan.s3.urllib.request.urlopen", _raise)
    result = check_bucket_public("mybucket", "us-east-1", 1.0)
    assert result["status_code"] == 500
    assert result["exists"] is False
    assert result["public"] is False
    assert result["error"] == "Server error: HTTP 500"


def test_check_bucket_public_unexpected_direct_status(monkeypatch) -> None:
    # 297->298: urlopen returns a non-2xx, non-403 status directly (e.g. 418).
    monkeypatch.setattr("ethscan.s3._resolve_s3_endpoint", _mock_dns("1.2.3.4"))
    monkeypatch.setattr(
        "ethscan.s3.urllib.request.urlopen",
        lambda req, timeout=None: _FakeResponse(418),
    )
    result = check_bucket_public("mybucket", "us-east-1", 1.0)
    assert result["status_code"] == 418
    assert result["exists"] is False
    assert result["public"] is False
    assert result["error"] == "Unexpected HTTP status 418"


def test_check_bucket_public_http_error_unexpected_status(monkeypatch) -> None:
    # 314->315: an HTTPError whose status is not 403/404/400/5xx (e.g. 418).
    monkeypatch.setattr("ethscan.s3._resolve_s3_endpoint", _mock_dns("1.2.3.4"))

    def _raise(req: object, timeout: float | None = None) -> Any:
        raise urllib.error.HTTPError(
            "https://x", 418, "I'm a teapot", Message(), None
        )

    monkeypatch.setattr("ethscan.s3.urllib.request.urlopen", _raise)
    result = check_bucket_public("mybucket", "us-east-1", 1.0)
    assert result["status_code"] == 418
    assert result["exists"] is False
    assert result["public"] is False
    assert result["error"] == "Unexpected HTTP status 418"