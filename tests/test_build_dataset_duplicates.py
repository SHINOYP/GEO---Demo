from pipeline.build_dataset import assign_duplicate_templates


def test_duplicate_template_assignment_is_order_independent():
    """Must give the same canonical pick and duplicate count regardless of
    what order urls are inserted in the input dict — guards against the bug
    where ThreadPoolExecutor completion order (nondeterministic) decided
    which URL was 'canonical' vs 'duplicate'."""
    fingerprints_in_order_a = {
        "https://b.example.com/": "fp1",
        "https://a.example.com/": "fp1",
        "https://c.example.com/": "fp2",
    }
    fingerprints_in_order_b = {
        "https://a.example.com/": "fp1",
        "https://c.example.com/": "fp2",
        "https://b.example.com/": "fp1",
    }
    seen_a, dup_a = assign_duplicate_templates(fingerprints_in_order_a)
    seen_b, dup_b = assign_duplicate_templates(fingerprints_in_order_b)
    assert seen_a == seen_b == {"fp1": "https://a.example.com/", "fp2": "https://c.example.com/"}
    assert dup_a == dup_b == 1


def test_urls_with_no_fingerprint_are_ignored():
    """A failed scrape (fingerprint=None) must not be counted as a
    duplicate or treated as canonical for anything."""
    fingerprints = {
        "https://ok.example.com/": "fp1",
        "https://failed.example.com/": None,
    }
    seen, dup = assign_duplicate_templates(fingerprints)
    assert seen == {"fp1": "https://ok.example.com/"}
    assert dup == 0
