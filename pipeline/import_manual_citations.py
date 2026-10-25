"""
Convert manually-collected Perplexity citations (data/manual_citations_full.txt)
into data/citations.json — the same shape pipeline/collect_citations.py
would have produced from the paid API — so build_dataset.py,
pilot_stats.py, and evaluate.py all work unchanged regardless of which
collection method was used.

This exists because the real-data pilot does not require a paid API key:
a human can manually search each query on https://www.perplexity.ai
(free) and copy down the cited URLs by hand. That is still real,
non-fabricated data — it is just collected by a person using the website
instead of a script calling an API. Every record is tagged
collection_method="manual_web_ui" so this is never ambiguous later (see
docs/DATA_CARD.md).

The candidate pool (data/candidates.json) is collected separately — see
docs/DATA_CARD.md for how it was built in this project.

data/manual_citations_full.txt is the authoritative, fully-filled worksheet
(all 200 queries) and is the default `--in`. The original two partial
collection passes are archived at data/manual_citations_archive/ for
history only — do not pass them with `--in` or this will silently
regenerate citations.json from an incomplete source (the script will now
refuse to overwrite a more-complete citations.json with a less-complete
one; see the --force flag).

Usage:
    python -m pipeline.import_manual_citations
    python -m pipeline.import_manual_citations --in data/manual_citations_full.txt
"""
import argparse
import csv
import json
import os
import re
import sys

from pipeline.common import REPO_ROOT, canonicalize_url, domain_of

LINE_RE = re.compile(r"^(Q\d+)\s*:\s*(.*)$")


def load_queries(path: str) -> dict:
    with open(path, newline="", encoding="utf-8") as f:
        return {row["query_id"]: row for row in csv.DictReader(f)}


def parse_urls(raw: str, qid: str) -> list:
    urls = []
    for u in raw.split(","):
        u = u.strip()
        if not u:
            continue
        if not u.startswith("http://") and not u.startswith("https://"):
            print(f"WARNING: {qid} has a url without http(s):// — skipping: {u!r}", file=sys.stderr)
            continue
        urls.append(u)
    return urls


def parse_manual_file(path: str) -> dict:
    """Returns {query_id: [urls]} from lines like 'Q01: url, url'."""
    cited = {}
    with open(path, encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            m = LINE_RE.match(stripped)
            if not m:
                print(f"WARNING: line {lineno} doesn't match 'Q01: url, url' format, skipping: {stripped!r}",
                      file=sys.stderr)
                continue
            qid, rest = m.group(1), m.group(2)
            if qid in cited:
                print(f"WARNING: duplicate query_id {qid!r} at line {lineno} — overwriting "
                      f"previously parsed citations for this id (worksheets may have been "
                      f"concatenated with overlapping ids)", file=sys.stderr)
            cited[qid] = parse_urls(rest, qid)
    return cited


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", default=os.path.join(REPO_ROOT, "data", "manual_citations_full.txt"))
    ap.add_argument("--queries", default=os.path.join(REPO_ROOT, "pipeline", "queries.csv"))
    ap.add_argument("--out-citations", default=os.path.join(REPO_ROOT, "data", "citations.json"))
    ap.add_argument("--force", action="store_true",
                     help="Overwrite --out-citations even if the newly-parsed file has fewer "
                          "queries with citations than the file already there (by default this "
                          "is refused, to stop an incomplete worksheet from silently clobbering "
                          "more-complete, already-collected real data).")
    args = ap.parse_args()

    if not os.path.exists(args.in_path):
        print(f"ERROR: {args.in_path} not found. Fill in data/manual_citations_full.txt "
              f"(format documented in its own header comments), then re-run.", file=sys.stderr)
        sys.exit(1)

    queries = load_queries(args.queries)
    cited = parse_manual_file(args.in_path)

    missing = [qid for qid in queries if not cited.get(qid)]
    if missing:
        print(f"NOTE: nothing recorded yet for: {', '.join(missing)} "
              f"(fine if you haven't gotten to them yet).")

    citation_records = []
    for qid, q in queries.items():
        cited_urls = [canonicalize_url(u) for u in cited.get(qid, [])]
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

    if os.path.exists(args.out_citations) and not args.force:
        with open(args.out_citations, encoding="utf-8") as f:
            existing_records = json.load(f)
        existing_filled = sum(1 for r in existing_records if r.get("cited_urls"))
        new_filled = sum(1 for r in citation_records if r["cited_urls"])
        if new_filled < existing_filled:
            print(f"ERROR: refusing to overwrite {args.out_citations} ({existing_filled} queries "
                  f"with citations) with a less-complete parse of {args.in_path} ({new_filled} "
                  f"queries with citations). This usually means --in points at an incomplete "
                  f"worksheet. Pass --force to overwrite anyway.", file=sys.stderr)
            sys.exit(1)

    with open(args.out_citations, "w", encoding="utf-8") as f:
        json.dump(citation_records, f, indent=2, ensure_ascii=False)

    total_cited = sum(len(r["cited_urls"]) for r in citation_records)
    print(f"Wrote {len(citation_records)} query records ({total_cited} cited urls) to {args.out_citations}")
    print("collection_method='manual_web_ui' recorded in every record — real, human-collected "
          "data, not synthetic, and not from a paid API.")


if __name__ == "__main__":
    main()
