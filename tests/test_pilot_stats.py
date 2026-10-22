"""
Tests for pipeline.pilot_stats: scrape-success-rate math and the
underpowered-flag boundary conditions (MIN_USABLE_ROWS=60,
MIN_MINORITY_CLASS=15 from pipeline.common). These numbers are quoted
directly in docs/VIVA_QA.md and the slides, so their arithmetic needs
regression coverage.
"""
import csv
import json

import pipeline.pilot_stats as pilot_stats


def _write_citations(path, n_queries):
    records = [
        {"query_id": f"Q{i:02d}", "category": "gym", "city": "Kochi",
         "cited_urls": [f"https://biz{i}.example.com/"]}
        for i in range(n_queries)
    ]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f)


def _write_dataset(path, n_ok_pos, n_ok_neg, n_failed=0):
    fieldnames = ["query_id", "domain", "label", "scrape_status", "domain_type", "is_duplicate_template"]
    rows = []
    for i in range(n_ok_pos):
        rows.append({"query_id": f"Q{i}", "domain": f"pos{i}.com", "label": 1,
                      "scrape_status": "ok", "domain_type": "business_site", "is_duplicate_template": "False"})
    for i in range(n_ok_neg):
        rows.append({"query_id": f"Q{i}", "domain": f"neg{i}.com", "label": 0,
                      "scrape_status": "ok", "domain_type": "business_site", "is_duplicate_template": "False"})
    for i in range(n_failed):
        rows.append({"query_id": f"Q{i}", "domain": f"fail{i}.com", "label": 0,
                      "scrape_status": "failed", "domain_type": "business_site", "is_duplicate_template": "False"})
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def _run_with_fixture(tmp_path, monkeypatch, n_ok_pos, n_ok_neg, n_failed=0):
    (tmp_path / "data").mkdir()
    (tmp_path / "docs").mkdir()
    _write_citations(str(tmp_path / "data" / "citations.json"), n_queries=5)
    _write_dataset(str(tmp_path / "data" / "dataset.csv"), n_ok_pos, n_ok_neg, n_failed)
    monkeypatch.setattr(pilot_stats, "REPO_ROOT", str(tmp_path))
    pilot_stats.main()
    with open(tmp_path / "data" / "pilot_stats.json", encoding="utf-8") as f:
        return json.load(f)


def test_scrape_success_rate_math(tmp_path, monkeypatch):
    """15 ok rows out of 20 total (5 failed) -> usable=15, success_rate=0.75."""
    stats = _run_with_fixture(tmp_path, monkeypatch, n_ok_pos=10, n_ok_neg=5, n_failed=5)
    assert stats["total_candidate_rows"] == 20
    assert stats["usable_rows"] == 15
    assert stats["scrape_success_rate"] == 0.75
    assert stats["class_balance"] == {"positive": 10, "negative": 10}


def test_underpowered_flag_false_right_at_thresholds(tmp_path, monkeypatch):
    """usable=60 (>= MIN 60) and min_class=15 (>= MIN 15) -> NOT underpowered."""
    stats = _run_with_fixture(tmp_path, monkeypatch, n_ok_pos=15, n_ok_neg=45, n_failed=0)
    assert stats["usable_rows"] == 60
    assert stats["underpowered"] is False


def test_underpowered_flag_true_just_below_minority_class_threshold(tmp_path, monkeypatch):
    """usable=60 but min_class=14 (< MIN 15) -> underpowered, even though row count is fine."""
    stats = _run_with_fixture(tmp_path, monkeypatch, n_ok_pos=14, n_ok_neg=46, n_failed=0)
    assert stats["usable_rows"] == 60
    assert stats["underpowered"] is True


def test_underpowered_flag_true_just_below_row_count_threshold(tmp_path, monkeypatch):
    """usable=59 (< MIN 60) even with balanced classes -> underpowered."""
    stats = _run_with_fixture(tmp_path, monkeypatch, n_ok_pos=30, n_ok_neg=29, n_failed=0)
    assert stats["usable_rows"] == 59
    assert stats["underpowered"] is True
