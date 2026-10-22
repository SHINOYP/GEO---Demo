import socket

import pytest

import scraping.scraper as scraper_mod
from scraping.scraper import scrape, ScrapingError


class _FakeResponse:
    def __init__(self, status_code, headers=None, is_redirect=False, content=b"", url="http://example.com/"):
        self.status_code = status_code
        self.headers = headers or {}
        self.is_redirect = is_redirect
        self.is_permanent_redirect = False
        self._content = content
        self.url = url

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size=65536):
        yield self._content


def test_scrape_revalidates_ssrf_on_redirect_to_metadata_endpoint(monkeypatch):
    """A URL that looks public but 302-redirects to the cloud metadata IP must
    be rejected: scrape() must re-run _check_ssrf on every redirect target,
    not just the original URL."""
    monkeypatch.setattr(socket, "gethostbyname", lambda host: "93.184.216.34")
    monkeypatch.setattr(scraper_mod, "_check_robots_txt", lambda url: None)

    redirect_resp = _FakeResponse(
        302,
        headers={"Location": "http://169.254.169.254/latest/meta-data/"},
        is_redirect=True,
    )

    def fake_get(url, headers, timeout, allow_redirects, stream):
        return redirect_resp

    monkeypatch.setattr(scraper_mod.requests, "get", fake_get)

    with pytest.raises(ScrapingError):
        scrape("http://safe-looking.example.com/")


def test_scrape_allows_safe_multi_hop_redirect_chain(monkeypatch):
    """A legitimate multi-hop redirect to another public host must still
    succeed — the SSRF re-check must not block safe redirects."""
    monkeypatch.setattr(socket, "gethostbyname", lambda host: "93.184.216.34")
    monkeypatch.setattr(scraper_mod, "_check_robots_txt", lambda url: None)

    calls = {"n": 0}
    padded_html = "<html><body>" + ("x" * 200) + "</body></html>"

    def fake_get(url, headers, timeout, allow_redirects, stream):
        calls["n"] += 1
        if calls["n"] == 1:
            return _FakeResponse(
                302,
                headers={"Location": "https://still-public.example.com/final"},
                is_redirect=True,
            )
        return _FakeResponse(200, content=padded_html.encode(), url="https://still-public.example.com/final")

    monkeypatch.setattr(scraper_mod.requests, "get", fake_get)

    result = scrape("https://safe-looking.example.com/start")
    assert result["status_code"] == 200
    assert result["final_url"] == "https://still-public.example.com/final"
    assert calls["n"] == 2
