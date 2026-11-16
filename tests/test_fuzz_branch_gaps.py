"""Focused branch-coverage tests for ethscan.fuzz edge cases."""

import pytest

from ethscan.fuzz import _normalize_base_url
from ethscan.target import TargetSpecError


def test_normalize_base_url_rejects_empty_host():
    with pytest.raises(TargetSpecError, match="Could not parse host"):
        _normalize_base_url("https:///path")
