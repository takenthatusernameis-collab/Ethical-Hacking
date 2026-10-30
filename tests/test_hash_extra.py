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


def test_md4_init_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    import hashlib as _hashlib
    import importlib

    original_new = _hashlib.new

    def _raising_new(name: str, *args: object, **kwargs: object) -> object:
        if name == "md4":
            raise ValueError("md4 unavailable")
        return original_new(name, *args, **kwargs)  # type: ignore[arg-type,call-arg]

    monkeypatch.setattr(_hashlib, "new", _raising_new)
    try:
        reloaded = importlib.reload(hashmod)
        assert reloaded.MD4_AVAILABLE is False
        assert "md4" not in reloaded._HASHLIB_ALGORITHMS
    finally:
        importlib.reload(hashmod)


def test_md4_init_available(monkeypatch: pytest.MonkeyPatch) -> None:
    import hashlib as _hashlib
    import importlib

    original_new = _hashlib.new

    class _DummyHash:
        def hexdigest(self) -> str:
            return ""

    def _fake_new(name: str, *args: object, **kwargs: object) -> object:
        if name == "md4":
            return _DummyHash()
        return original_new(name, *args, **kwargs)  # type: ignore[arg-type,call-arg]

    monkeypatch.setattr(_hashlib, "new", _fake_new)
    try:
        reloaded = importlib.reload(hashmod)
        assert reloaded.MD4_AVAILABLE is True
        assert "md4" in reloaded._HASHLIB_ALGORITHMS
    finally:
        importlib.reload(hashmod)
