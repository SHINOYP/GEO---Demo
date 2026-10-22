from pipeline.build_dataset import build_rows_to_scrape


def test_pool_is_union_of_cited_and_candidate_urls():
    citations = [{
        "query_id": "Q01", "category": "gym", "city": "Kochi",
        "cited_urls": ["https://cited-only.example.com/"],
    }]
    candidates = {"Q01": ["https://candidate-only.example.com/", "https://cited-only.example.com/"]}
    rows = build_rows_to_scrape(citations, candidates)
    urls_and_labels = {url: label for (_, _, _, url, label) in rows}
    assert urls_and_labels == {
        "https://cited-only.example.com/": 1,
        "https://candidate-only.example.com/": 0,
    }


def test_url_cited_for_one_query_is_unlabeled_candidate_for_another():
    """The same URL can be a cited (label=1) source for one query and merely
    an uncited candidate (label=0) for a different query — label is per
    (query_id, url), never attached to the URL globally."""
    citations = [
        {"query_id": "Q01", "category": "gym", "city": "Kochi", "cited_urls": ["https://shared.example.com/"]},
        {"query_id": "Q02", "category": "gym", "city": "Mumbai", "cited_urls": []},
    ]
    candidates = {"Q01": [], "Q02": ["https://shared.example.com/"]}
    rows = build_rows_to_scrape(citations, candidates)
    by_query = {(qid, url): label for (qid, _, _, url, label) in rows}
    assert by_query[("Q01", "https://shared.example.com/")] == 1
    assert by_query[("Q02", "https://shared.example.com/")] == 0


def test_candidate_urls_are_canonicalized_before_pool_union():
    """candidates.json urls go through canonicalize_url before being unioned
    with cited_urls (which are already canonical) — otherwise a URL that is
    both cited and a raw, non-canonical candidate would appear twice in the
    pool instead of being deduped into one labeled row."""
    citations = [{"query_id": "Q01", "category": "gym", "city": "Kochi",
                  "cited_urls": ["https://example.com/page"]}]
    candidates = {"Q01": ["https://Example.com/page/?utm_source=x"]}
    rows = build_rows_to_scrape(citations, candidates)
    assert len(rows) == 1
    assert rows[0][3] == "https://example.com/page"
    assert rows[0][4] == 1


def test_rows_are_sorted_by_url_for_reproducible_dataset_row_order():
    """build_rows_to_scrape must not rely on raw set iteration order, which
    is not reproducible across processes without a pinned PYTHONHASHSEED."""
    citations = [{"query_id": "Q01", "category": "gym", "city": "Kochi", "cited_urls": []}]
    candidates = {"Q01": ["https://zzz.example.com/", "https://aaa.example.com/", "https://mmm.example.com/"]}
    rows = build_rows_to_scrape(citations, candidates)
    urls = [url for (_, _, _, url, _) in rows]
    assert urls == sorted(urls)
