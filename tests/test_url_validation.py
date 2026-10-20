import pytest

from scraping.scraper import _check_ssrf, ScrapingError


def test_rejects_non_http_scheme():
    with pytest.raises(ScrapingError):
        _check_ssrf("ftp://example.com/file")


def test_rejects_localhost():
    with pytest.raises(ScrapingError):
        _check_ssrf("http://localhost/")


def test_rejects_loopback_ip():
    with pytest.raises(ScrapingError):
        _check_ssrf("http://127.0.0.1/")


def test_rejects_cloud_metadata_endpoint():
    with pytest.raises(ScrapingError):
        _check_ssrf("http://169.254.169.254/latest/meta-data/")


def test_rejects_private_ip_literal():
    with pytest.raises(ScrapingError):
        _check_ssrf("http://10.0.0.5/")


def test_allows_public_looking_host(monkeypatch):
    # Don't hit the network to resolve DNS; just confirm a well-known public
    # IP is not blocked by the range check itself.
    import socket
    monkeypatch.setattr(socket, "gethostbyname", lambda host: "93.184.216.34")
    _check_ssrf("http://example.com/")  # should not raise
