"""Oracle verification tests for ethscan.cidr pure helpers.

These tests verify the pure helper functions in ethscan.cidr against
stdlib oracles (ipaddress only) over a hostile input matrix. The
independent oracles live in oracle_verify_cidr.py; this file exposes
them as regression tests.

Functions verified:
- normalize_cidr
- _contains_ip
- _subtract_networks
- run_cidr
"""

from __future__ import annotations

from oracle_verify_cidr import (
    verify_contains_ip,
    verify_normalize_cidr,
    verify_run_cidr,
    verify_subtract_networks,
)

import pytest


def _fail_on_mismatches(func_name: str, mismatches: list[tuple[str, str, str]]) -> None:
    if mismatches:
        details = "\n".join(
            f"  {func_name}({inp}) => ours={ours!r}, oracle={oracle!r}"
            for inp, ours, oracle in mismatches[:20]
        )
        if len(mismatches) > 20:
            details += f"\n  ... and {len(mismatches) - 20} more"
        pytest.fail(f"{func_name} has {len(mismatches)} mismatches:\n{details}")


def test_normalize_cidr_matches_oracle() -> None:
    """normalize_cidr output matches stdlib ipaddress oracle for all hostile inputs."""
    _fail_on_mismatches("normalize_cidr", verify_normalize_cidr())


def test_contains_ip_matches_oracle() -> None:
    """_contains_ip output matches stdlib ipaddress oracle for all hostile inputs."""
    _fail_on_mismatches("_contains_ip", verify_contains_ip())


def test_subtract_networks_matches_oracle() -> None:
    """_subtract_networks output matches stdlib ipaddress oracle for all hostile inputs."""
    _fail_on_mismatches("_subtract_networks", verify_subtract_networks())


def test_run_cidr_matches_oracle() -> None:
    """run_cidr output matches stdlib ipaddress oracle for all hostile inputs."""
    _fail_on_mismatches("run_cidr", verify_run_cidr())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
