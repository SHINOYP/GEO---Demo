from pipeline.common import canonicalize_url, domain_of


def test_strips_trailing_slash():
    assert canonicalize_url("https://Example.com/page/") == canonicalize_url("https://example.com/page")


def test_lowercases_host():
    assert canonicalize_url("https://EXAMPLE.com/Page") == "https://example.com/Page"


def test_strips_tracking_params():
    a = canonicalize_url("https://example.com/page?utm_source=x&id=5")
    b = canonicalize_url("https://example.com/page?id=5")
    assert a == b


def test_strips_fragment():
    a = canonicalize_url("https://example.com/page#section")
    b = canonicalize_url("https://example.com/page")
    assert a == b


def test_different_paths_not_equal():
    assert canonicalize_url("https://example.com/a") != canonicalize_url("https://example.com/b")


def test_domain_of_strips_path():
    assert domain_of("https://Example.com/a/b?x=1") == "example.com"
