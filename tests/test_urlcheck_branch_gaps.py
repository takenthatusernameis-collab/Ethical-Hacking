"""Targeted tests to close the 7 branch gaps in ethscan/urlcheck.py run_urlcheck.

Each test isolates one false branch by controlling the mocked return values of
run_web_checks, run_fuzz, and run_ssl. These tests are reversible (test-only).
"""

from unittest.mock import patch

from ethscan.urlcheck import run_urlcheck


def _mock_web_results_dict_sec_headers_not_dict(*args, **kwargs):
    """web_results is dict, but security_headers is not dict -> covers 89->93."""
    return {
        "host": "example.com",
        "security_headers": "not-a-dict",
        "information_disclosure": [],
    }


def _mock_web_results_dict_sec_headers_missing_count_not_int(*args, **kwargs):
    """web_results dict, security_headers dict, missing_count not int -> covers 89->93."""
    return {
        "host": "example.com",
        "security_headers": {"missing_count": "not-an-int"},
        "information_disclosure": [],
    }


def _mock_web_results_dict_sec_headers_missing_count_zero(*args, **kwargs):
    """web_results dict, security_headers dict, missing_count == 0 -> covers 89->93."""
    return {
        "host": "example.com",
        "security_headers": {"missing_count": 0},
        "information_disclosure": [],
    }


def _mock_web_results_dict_sec_headers_missing_count_negative(*args, **kwargs):
    """web_results dict, security_headers dict, missing_count < 0 -> covers 89->93."""
    return {
        "host": "example.com",
        "security_headers": {"missing_count": -1},
        "information_disclosure": [],
    }


def _mock_fuzz_none(*args, **kwargs):
    """Return None for fuzz to skip fuzz findings path."""
    return None


def _mock_ssl_dict_cert_not_dict(*args, **kwargs):
    """ssl_data is dict, but cert is not dict -> covers 105->112."""
    return {
        "host": "example.com",
        "valid": True,
        "cert": "not-a-dict",
    }


def _mock_ssl_dict_cert_dict_key_size_not_int(*args, **kwargs):
    """ssl_data dict, cert dict, key_size not int -> covers 107->109."""
    return {
        "host": "example.com",
        "valid": True,
        "cert": {"key_size": "not-an-int", "signature_algorithm": "sha256WithRSAEncryption"},
    }


def _mock_ssl_dict_cert_dict_key_size_large(*args, **kwargs):
    """ssl_data dict, cert dict, key_size >= 2048 -> covers 107->109."""
    return {
        "host": "example.com",
        "valid": True,
        "cert": {"key_size": 4096, "signature_algorithm": "sha256WithRSAEncryption"},
    }


def _mock_ssl_dict_cert_dict_sig_alg_not_str(*args, **kwargs):
    """ssl_data dict, cert dict, signature_algorithm not str -> covers 110->112."""
    return {
        "host": "example.com",
        "valid": True,
        "cert": {"key_size": 2048, "signature_algorithm": 123},
    }


def _mock_ssl_dict_cert_dict_sig_alg_no_sha1(*args, **kwargs):
    """ssl_data dict, cert dict, signature_algorithm lacks sha1 -> covers 110->112."""
    return {
        "host": "example.com",
        "valid": True,
        "cert": {"key_size": 2048, "signature_algorithm": "sha256WithRSAEncryption"},
    }


def _mock_ssl_dict_valid_true(*args, **kwargs):
    """ssl_data dict, valid True -> covers 113->116."""
    return {
        "host": "example.com",
        "valid": True,
        "cert": {"key_size": 2048, "signature_algorithm": "sha256WithRSAEncryption"},
    }


# Test for 77->79 and 87->96: web_results not a dict
def _mock_web_results_not_dict(*args, **kwargs):
    """web_results is not a dict (e.g., list) -> covers 77->79 and 87->96."""
    # Return a list-like object that has .get but isn't a dict
    class FakeList:
        def get(self, key, default=None):
            return "example.com" if key == "host" else default

    return FakeList()


@patch("ethscan.urlcheck.run_web_checks", _mock_web_results_not_dict)
@patch("ethscan.urlcheck.run_fuzz", _mock_fuzz_none)
@patch("ethscan.urlcheck.run_ssl", _mock_fuzz_none)
def test_run_urlcheck_web_results_not_dict_covers_77_79_87_96() -> None:
    """web_results is not a dict -> covers 77->79 and 87->96 false branches."""
    results = run_urlcheck(
        "https://example.com",
        ["headers"],
        wordlist=None,
        fuzz_paths=False,
        port=443,
        timeout=1.0,
        workers=1,
    )
    # host extraction via .get() still works
    assert results["normalized_target"] == "https://example.com"
    # ssl path uses host from web_results.get("host")
    assert "ssl" in results


# Tests for 89->93: various false branches of missing_count checks
@patch("ethscan.urlcheck.run_web_checks", _mock_web_results_dict_sec_headers_not_dict)
@patch("ethscan.urlcheck.run_fuzz", _mock_fuzz_none)
@patch("ethscan.urlcheck.run_ssl", _mock_fuzz_none)
def test_run_urlcheck_sec_headers_not_dict_covers_89_93() -> None:
    """security_headers not a dict -> covers 89->93 false branch."""
    results = run_urlcheck(
        "https://example.com",
        ["headers"],
        wordlist=None,
        fuzz_paths=False,
        port=443,
        timeout=1.0,
        workers=1,
    )
    assert results["summary"]["total_findings"] == 0


@patch("ethscan.urlcheck.run_web_checks", _mock_web_results_dict_sec_headers_missing_count_not_int)
@patch("ethscan.urlcheck.run_fuzz", _mock_fuzz_none)
@patch("ethscan.urlcheck.run_ssl", _mock_fuzz_none)
def test_run_urlcheck_missing_count_not_int_covers_89_93() -> None:
    """security_headers.missing_count not int -> covers 89->93 false branch."""
    results = run_urlcheck(
        "https://example.com",
        ["headers"],
        wordlist=None,
        fuzz_paths=False,
        port=443,
        timeout=1.0,
        workers=1,
    )
    assert results["summary"]["total_findings"] == 0


@patch("ethscan.urlcheck.run_web_checks", _mock_web_results_dict_sec_headers_missing_count_zero)
@patch("ethscan.urlcheck.run_fuzz", _mock_fuzz_none)
@patch("ethscan.urlcheck.run_ssl", _mock_fuzz_none)
def test_run_urlcheck_missing_count_zero_covers_89_93() -> None:
    """security_headers.missing_count == 0 -> covers 89->93 false branch."""
    results = run_urlcheck(
        "https://example.com",
        ["headers"],
        wordlist=None,
        fuzz_paths=False,
        port=443,
        timeout=1.0,
        workers=1,
    )
    assert results["summary"]["total_findings"] == 0


@patch("ethscan.urlcheck.run_web_checks", _mock_web_results_dict_sec_headers_missing_count_negative)
@patch("ethscan.urlcheck.run_fuzz", _mock_fuzz_none)
@patch("ethscan.urlcheck.run_ssl", _mock_fuzz_none)
def test_run_urlcheck_missing_count_negative_covers_89_93() -> None:
    """security_headers.missing_count < 0 -> covers 89->93 false branch."""
    results = run_urlcheck(
        "https://example.com",
        ["headers"],
        wordlist=None,
        fuzz_paths=False,
        port=443,
        timeout=1.0,
        workers=1,
    )
    assert results["summary"]["total_findings"] == 0


# Tests for SSL branches
@patch("ethscan.urlcheck.run_web_checks", lambda *a, **k: {"host": "example.com", "security_headers": {"missing_count": 0}, "information_disclosure": []})
@patch("ethscan.urlcheck.run_fuzz", _mock_fuzz_none)
@patch("ethscan.urlcheck.run_ssl", _mock_ssl_dict_cert_not_dict)
def test_run_urlcheck_ssl_cert_not_dict_covers_105_112() -> None:
    """ssl_data.cert is not a dict -> covers 105->112 false branch."""
    results = run_urlcheck(
        "https://example.com",
        ["headers", "ssl"],
        wordlist=None,
        fuzz_paths=False,
        port=443,
        timeout=1.0,
        workers=1,
    )
    assert results["summary"]["total_findings"] == 0


@patch("ethscan.urlcheck.run_web_checks", lambda *a, **k: {"host": "example.com", "security_headers": {"missing_count": 0}, "information_disclosure": []})
@patch("ethscan.urlcheck.run_fuzz", _mock_fuzz_none)
@patch("ethscan.urlcheck.run_ssl", _mock_ssl_dict_cert_dict_key_size_not_int)
def test_run_urlcheck_ssl_key_size_not_int_covers_107_109() -> None:
    """ssl_data.cert.key_size is not int -> covers 107->109 false branch."""
    results = run_urlcheck(
        "https://example.com",
        ["headers", "ssl"],
        wordlist=None,
        fuzz_paths=False,
        port=443,
        timeout=1.0,
        workers=1,
    )
    assert results["summary"]["total_findings"] == 0


@patch("ethscan.urlcheck.run_web_checks", lambda *a, **k: {"host": "example.com", "security_headers": {"missing_count": 0}, "information_disclosure": []})
@patch("ethscan.urlcheck.run_fuzz", _mock_fuzz_none)
@patch("ethscan.urlcheck.run_ssl", _mock_ssl_dict_cert_dict_key_size_large)
def test_run_urlcheck_ssl_key_size_ge_2048_covers_107_109() -> None:
    """ssl_data.cert.key_size >= 2048 -> covers 107->109 false branch."""
    results = run_urlcheck(
        "https://example.com",
        ["headers", "ssl"],
        wordlist=None,
        fuzz_paths=False,
        port=443,
        timeout=1.0,
        workers=1,
    )
    assert results["summary"]["total_findings"] == 0


@patch("ethscan.urlcheck.run_web_checks", lambda *a, **k: {"host": "example.com", "security_headers": {"missing_count": 0}, "information_disclosure": []})
@patch("ethscan.urlcheck.run_fuzz", _mock_fuzz_none)
@patch("ethscan.urlcheck.run_ssl", _mock_ssl_dict_cert_dict_sig_alg_not_str)
def test_run_urlcheck_ssl_sig_alg_not_str_covers_110_112() -> None:
    """ssl_data.cert.signature_algorithm is not str -> covers 110->112 false branch."""
    results = run_urlcheck(
        "https://example.com",
        ["headers", "ssl"],
        wordlist=None,
        fuzz_paths=False,
        port=443,
        timeout=1.0,
        workers=1,
    )
    assert results["summary"]["total_findings"] == 0


@patch("ethscan.urlcheck.run_web_checks", lambda *a, **k: {"host": "example.com", "security_headers": {"missing_count": 0}, "information_disclosure": []})
@patch("ethscan.urlcheck.run_fuzz", _mock_fuzz_none)
@patch("ethscan.urlcheck.run_ssl", _mock_ssl_dict_cert_dict_sig_alg_no_sha1)
def test_run_urlcheck_ssl_sig_alg_no_sha1_covers_110_112() -> None:
    """ssl_data.cert.signature_algorithm lacks sha1 -> covers 110->112 false branch."""
    results = run_urlcheck(
        "https://example.com",
        ["headers", "ssl"],
        wordlist=None,
        fuzz_paths=False,
        port=443,
        timeout=1.0,
        workers=1,
    )
    assert results["summary"]["total_findings"] == 0


@patch("ethscan.urlcheck.run_web_checks", lambda *a, **k: {"host": "example.com", "security_headers": {"missing_count": 0}, "information_disclosure": []})
@patch("ethscan.urlcheck.run_fuzz", _mock_fuzz_none)
@patch("ethscan.urlcheck.run_ssl", _mock_ssl_dict_valid_true)
def test_run_urlcheck_ssl_valid_true_covers_113_116() -> None:
    """ssl_data.valid is True -> covers 113->116 false branch."""
    results = run_urlcheck(
        "https://example.com",
        ["headers", "ssl"],
        wordlist=None,
        fuzz_paths=False,
        port=443,
        timeout=1.0,
        workers=1,
    )
    assert results["summary"]["total_findings"] == 0