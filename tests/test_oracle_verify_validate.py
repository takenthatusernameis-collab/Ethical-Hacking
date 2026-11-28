"""Oracle verification tests for ethscan.validate pure helpers."""

from __future__ import annotations

from oracle_verify_validate import (
    verify_run_validate,
    verify_validate_cidr,
    verify_validate_port_spec,
)

import pytest


def _fail_on_mismatches(func_name: str, mismatches: list) -> None:
    if mismatches:
        details = "\n".join(
            f"  {func_name}({inp}) => ours={ours!r}, oracle={oracle!r}"
            for inp, ours, oracle in mismatches[:20]
        )
        if len(mismatches) > 20:
            details += f"\n  ... and {len(mismatches) - 20} more"
        pytest.fail(f"{func_name} has {len(mismatches)} mismatches:\n{details}")


def test_validate_port_spec_matches_oracle() -> None:
    _fail_on_mismatches("_validate_port_spec", verify_validate_port_spec())


def test_validate_cidr_matches_oracle() -> None:
    _fail_on_mismatches("_validate_cidr", verify_validate_cidr())


def test_run_validate_matches_oracle() -> None:
    _fail_on_mismatches("run_validate", verify_run_validate())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
