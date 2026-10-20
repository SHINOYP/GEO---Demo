"""
Collect real citations from Perplexity's search-enabled chat completions API
("sonar" model) for each query in pipeline/queries.csv.

Usage:
    python -m pipeline.collect_citations --dry-run
    python -m pipeline.collect_citations --yes --max-calls 20
    python -m pipeline.collect_citations --yes --repeats 3 --max-calls 60

Requires PERPLEXITY_API_KEY in a local .env (never committed). Caches the
raw JSON response per (query, repeat) under data/raw/perplexity/, so
re-running costs nothing once cached.
"""
import argparse
import csv
import json
import os
import sys

from pipeline.common import (
    REPO_ROOT, load_env, read_cache, write_cache, CallBudget,
    post_json_with_retry, canonicalize_url, domain_of,
)

PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"
PERPLEXITY_MODEL = "sonar"
# Perplexity's pricing changes over time; this is a conservative per-request
# estimate for the "sonar" model used purely to size --max-calls, not a
# billed cost claim. Verify against https://docs.perplexity.ai/guides/pricing
# before a real paid run.
ESTIMATED_COST_PER_CALL_USD = 0.005


def load_queries(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_payload(query_text: str) -> dict:
    return {
        "model": PERPLEXITY_MODEL,
        "messages": [{"role": "user", "content": query_text}],
    }


def extract_citations(raw_response: dict) -> list[str]:
    """
    Pull cited URLs out of whatever shape the Perplexity response actually
    has. Perplexity has shipped citations under different keys over time
    (top-level "citations" list of URL strings, and/or "search_results"
    list of {title, url, ...} dicts). We check both and log whichever keys
    were actually present to docs/API_NOTES.md on first real call.
    """
    urls = []
    if "citations" in raw_response and isinstance(raw_response["citations"], list):
        for item in raw_response["citations"]:
            if isinstance(item, str):
                urls.append(item)
            elif isinstance(item, dict) and "url" in item:
                urls.append(item["url"])
    if "search_results" in raw_response and isinstance(raw_response["search_results"], list):
        for item in raw_response["search_results"]:
            if isinstance(item, dict) and "url" in item:
                urls.append(item["url"])
    # dedupe, preserve order
    seen = set()
    out = []
    for u in urls:
        cu = canonicalize_url(u)
        if cu not in seen:
            seen.add(cu)
            out.append(cu)
    return out


def log_schema_once(raw_response: dict):
    note_path = os.path.join(REPO_ROOT, "docs", "API_NOTES.md")
    if os.path.exists(note_path):
        return
    os.makedirs(os.path.dirname(note_path), exist_ok=True)
    keys = sorted(raw_response.keys())
    with open(note_path, "w", encoding="utf-8") as f:
        f.write("# API Notes — Perplexity response schema (observed)\n\n")
        f.write("Logged automatically from the first real API response.\n\n")
        f.write(f"Top-level keys observed: `{keys}`\n\n")
        f.write("```json\n")
        f.write(json.dumps(raw_response, indent=2)[:4000])
        f.write("\n```\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true", help="Required to make real (non-cached) API calls.")
    ap.add_argument("--max-calls", type=int, default=60)
    ap.add_argument("--repeats", type=int, default=1, help="Repeats per query, to measure label stability later.")
    ap.add_argument("--queries", default=os.path.join(REPO_ROOT, "pipeline", "queries.csv"))
    args = ap.parse_args()

    queries = load_queries(args.queries)
    total_planned_calls = len(queries) * args.repeats
    print(f"Plan: {len(queries)} queries x {args.repeats} repeat(s) = {total_planned_calls} potential API calls.")
    print(f"Rough cost estimate: ~${total_planned_calls * ESTIMATED_COST_PER_CALL_USD:.2f} "
          f"(very approximate — verify current Perplexity pricing before a real paid run).")

    if args.dry_run:
        print("--dry-run: no API calls will be made.")
        return

    load_env()
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        print("ERROR: PERPLEXITY_API_KEY not set in environment / .env. "
              "Add it to a local .env (gitignored) and re-run.", file=sys.stderr)
        sys.exit(1)

    if not args.yes:
        print("Refusing to make real API calls without --yes (this is a paid external API). "
              "Re-run with --yes once you've confirmed the cost estimate above.")
        sys.exit(1)

    budget = CallBudget(args.max_calls)
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    results = []
    for q in queries:
        for rep in range(args.repeats):
            cache_key = f"{q['query_id']}::rep{rep}"
            cached = read_cache("perplexity", cache_key)
            if cached is not None:
                raw = cached
                print(f"[cache] {q['query_id']} rep{rep}")
            else:
                payload = build_payload(q["query_text"])
                try:
                    raw = post_json_with_retry(PERPLEXITY_URL, headers, payload, budget)
                except RuntimeError as e:
                    print(f"[FAILED] {q['query_id']} rep{rep}: {e}", file=sys.stderr)
                    continue
                write_cache("perplexity", cache_key, raw)
                log_schema_once(raw)
                print(f"[live]  {q['query_id']} rep{rep} (calls made so far: {budget.calls_made})")

            citations = extract_citations(raw)
            results.append({
                "query_id": q["query_id"],
                "category": q["category"],
                "city": q["city"],
                "query_text": q["query_text"],
                "repeat": rep,
                "cited_urls": citations,
                "cited_domains": sorted({domain_of(u) for u in citations}),
            })

    out_path = os.path.join(REPO_ROOT, "data", "citations.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nReal API calls made this run: {budget.calls_made}")
    print(f"Wrote {len(results)} query-repeat records to {out_path}")


if __name__ == "__main__":
    main()
