import json
import os

from pipeline.import_manual_citations import parse_manual_file, parse_urls


def test_parses_cited_and_organic_lines(tmp_path):
    p = tmp_path / "manual.txt"
    p.write_text(
        "# comment\n"
        "Q01 Cited: https://a.com/x, https://b.com/y\n"
        "Q01 Organic: https://a.com/x, https://c.com/z\n"
        "Q02 Cited:\n"
    )
    cited, organic = parse_manual_file(str(p))
    assert cited["Q01"] == ["https://a.com/x", "https://b.com/y"]
    assert organic["Q01"] == ["https://a.com/x", "https://c.com/z"]
    assert cited["Q02"] == []


def test_skips_urls_without_scheme():
    urls = parse_urls("https://ok.com, not-a-url, https://also-ok.com", "Q01", "cited")
    assert urls == ["https://ok.com", "https://also-ok.com"]


def test_skips_malformed_lines(tmp_path):
    p = tmp_path / "manual.txt"
    p.write_text("this is not a valid line\nQ01 Cited: https://a.com\n")
    cited, organic = parse_manual_file(str(p))
    assert cited["Q01"] == ["https://a.com"]
