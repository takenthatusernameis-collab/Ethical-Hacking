from __future__ import annotations


import pytest

import ethscan.hash as hashmod


def test_normalize_md4_not_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hashmod, "MD4_AVAILABLE", False)
    with pytest.raises(ValueError):
        hashmod._normalize_algorithm("md4")


def test_compute_md4_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hashmod, "MD4_AVAILABLE", False)
    with pytest.raises(ValueError):
        hashmod._compute_md4("test")


def test_pbkdf2_pepper_unsupported_alg() -> None:
    with pytest.raises(ValueError):
        hashmod._compute_password_hash("x", algorithm="ntlm", salt="s", pepper="p", iterations=1000)
