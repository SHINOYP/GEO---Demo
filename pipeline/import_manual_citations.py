"""
Convert manually-collected data (data/manual_citations.txt) into the same
data/citations.json + data/candidates.json format the automated
collect_citations.py / collect_candidates.py scripts would have produced
from paid APIs — so build_dataset.py, pilot_stats.py, and evaluate.py all
work unchanged regardless of which collection method was used.

This exists because the real-data pilot does not require a paid API key:
a human can manually search each query on https://www.perplexity.ai and
https://www.google.com (both free) and copy down the result urls by hand.
That is still real, non-fabricated data — it is just collected by a
person using the websites instead of a script calling an API. The
collection method is recorded in the output so this is never ambiguous
later (see docs/DATA_CARD.md).

Usage:
    python -m pipeline.import_manual_citations
    python -m pipeline.import_manual_citations --in data/manual_citations.txt
"""
import argparse
import csv
import json
import os
import re
import sys

from pipeline.common import REPO_ROOT, canonicalize_url, domain_of

LINE_RE = re.compile(r"^(Q\d+)\s+(Cited|Organic)\s*:\s*(.*)$", re.IGNORECASE)


def load_queries(path: str) -> dict:
    with open(path, newline="", encoding="utf-8") as f:
        return {row["query_id"]: row for row in csv.DictReader(f)}


def parse_urls(raw: str, qid: str, kind: str) -> list:
    urls = []
    for u in raw.split(","):
        u = u.strip()
        if not u:
            continue
        if not u.startswith("http://") and not u.startswith("https://"):
            print(f"WARNING: {qid} {kind} has a url without http(s):// — skipping: {u!r}", file=sys.stderr)
            continue
        urls.append(u)
    return urls


def parse_manual_file(path: str):
    """Returns (cited: {qid: [urls]}, organic: {qid: [urls]})."""
    cited, organic = {}, {}
    with open(path, encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            m = LINE_RE.match(stripped)
            if not m:
                print(f"WARNING: line {lineno} doesn't match 'Q01 Cited: ...' format, skipping: {stripped!r}",
                      file=sys.stderr)
                continue
            qid, kind, rest = m.group(1), m.group(2).lower(), m.group(3)
            target = cited if kind == "cited" else organic
            target[qid] = parse_urls(rest, qid, kind)
    return cited, organic


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", default=os.path.join(REPO_ROOT, "data", "manual_citations.txt"))
    ap.add_argument("--queries", default=os.path.join(REPO_ROOT, "pipeline", "queries.csv"))
    ap.add_argument("--out-citations", default=os.path.join(REPO_ROOT, "data", "citations.json"))
    ap.add_argument("--out-candidates", default=os.path.join(REPO_ROOT, "data", "candidates.json"))
    args = ap.parse_args()

    if not os.path.exists(args.in_path):
        print(f"ERROR: {args.in_path} not found. Copy data/manual_citations_template.txt to "
              f"data/manual_citations.txt, fill it in, then re-run.", file=sys.stderr)
        sys.exit(1)

    queries = load_queries(args.queries)
    cited, organic = parse_manual_file(args.in_path)

    missing = [qid for qid in queries if not cited.get(qid) and not organic.get(qid)]
    if missing:
        print(f"NOTE: nothing recorded yet for: {', '.join(missing)} "
              f"(fine if you haven't gotten to them yet).")

    citation_records = []
    candidate_map = {}
    for qid, q in queries.items():
        cited_urls = [canonicalize_url(u) for u in cited.get(qid, [])]
        organic_urls = [canonicalize_url(u) for u in organic.get(qid, [])]
        citation_records.append({
            "query_id": qid,
            "category": q["category"],
            "city": q["city"],
            "query_text": q["query_text"],
            "repeat": 0,
            "cited_urls": cited_urls,
            "cited_domains": sorted({domain_of(u) for u in cited_urls}),
            "collection_method": "manual_web_ui",
        })
        candidate_map[qid] = organic_urls

    with open(args.out_citations, "w", encoding="utf-8") as f:
        json.dump(citation_records, f, indent=2, ensure_ascii=False)
    with open(args.out_candidates, "w", encoding="utf-8") as f:
        json.dump(candidate_map, f, indent=2, ensure_ascii=False)

    total_cited = sum(len(r["cited_urls"]) for r in citation_records)
    total_organic = sum(len(v) for v in candidate_map.values())
    print(f"Wrote {len(citation_records)} query records ({total_cited} cited urls) to {args.out_citations}")
    print(f"Wrote candidate pools ({total_organic} organic urls) to {args.out_candidates}")
    print("collection_method='manual_web_ui' recorded in every record — real, human-collected "
          "data, not synthetic, and not from a paid API.")


if __name__ == "__main__":
    main()
