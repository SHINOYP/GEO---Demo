from pipeline.import_manual_citations import parse_manual_file, parse_urls


def test_parses_cited_lines(tmp_path):
    p = tmp_path / "manual.txt"
    p.write_text(
        "# comment\n"
        "Q01: https://a.com/x, https://b.com/y\n"
        "Q02:\n"
    )
    cited = parse_manual_file(str(p))
    assert cited["Q01"] == ["https://a.com/x", "https://b.com/y"]
    assert cited["Q02"] == []


def test_skips_urls_without_scheme():
    urls = parse_urls("https://ok.com, not-a-url, https://also-ok.com", "Q01")
    assert urls == ["https://ok.com", "https://also-ok.com"]


def test_skips_malformed_lines(tmp_path):
    p = tmp_path / "manual.txt"
    p.write_text("this is not a valid line\nQ01: https://a.com\n")
    cited = parse_manual_file(str(p))
    assert cited["Q01"] == ["https://a.com"]


def test_duplicate_query_id_across_concatenated_worksheets_warns_and_keeps_last(tmp_path, capsys):
    """manual_citations_full.txt is built by concatenating two worksheets
    (Q01-Q100, Q101-Q200) into one file. If the same Q-id is ever present in
    both sections (e.g. a copy-paste slip while combining worksheets), the
    earlier worksheet's citations must not be discarded silently."""
    p = tmp_path / "manual.txt"
    p.write_text(
        "# batch 1\n"
        "Q01: https://first.example.com/a\n"
        "# batch 2 (accidentally overlaps)\n"
        "Q01: https://second.example.com/b\n"
    )
    cited = parse_manual_file(str(p))
    # Document current behavior: last occurrence wins.
    assert cited["Q01"] == ["https://second.example.com/b"]
    # A duplicate Q-id must be surfaced, not swallowed silently.
    err = capsys.readouterr().err
    assert "Q01" in err and "duplicate" in err.lower(), (
        "parse_manual_file should warn when the same query_id appears twice "
        "in a concatenated worksheet, since the earlier citations are discarded"
    )
