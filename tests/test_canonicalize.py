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


def test_does_not_strip_params_that_merely_start_with_tracking_prefixes():
    """'ref' and 'source' must be stripped as exact tracking params (e.g.
    ?ref=affiliate123), but must NOT swallow unrelated params that happen to
    start with the same letters, like 'refund' or 'sourceLanguage' — those
    carry real page-identifying information and must not be conflated."""
    a = canonicalize_url("https://example.com/page?refund=50&id=5")
    b = canonicalize_url("https://example.com/page?refund=90&id=5")
    assert a != b, "canonicalize_url is incorrectly treating 'refund' as the 'ref' tracking param"

    c = canonicalize_url("https://example.com/page?sourceLanguage=en&id=5")
    d = canonicalize_url("https://example.com/page?id=5")
    assert c != d, "canonicalize_url is incorrectly treating 'sourceLanguage' as the 'source' tracking param"

    # Exact tracking params must still be stripped.
    e = canonicalize_url("https://example.com/page?ref=affiliate123&id=5")
    assert e == d


def test_domain_of_strips_path():
    assert domain_of("https://Example.com/a/b?x=1") == "example.com"
