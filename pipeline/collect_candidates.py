"""
Collect the candidate pool of organic search results for each query.

If SERPAPI_KEY is set, fetches top 10-15 organic results per query from
SerpAPI's Google Search API. If no key is set, falls back to the
search_results already returned inside the cached Perplexity responses
from collect_citations.py (data/raw/perplexity/*.json) — documented as a
limitation (narrower, engine-biased candidate pool) rather than silently
pretended away.

Usage:
    python -m pipeline.collect_candidates --dry-run
    python -m pipeline.collect_candidates --yes --max-calls 20
"""
import argparse
import csv
import glob
import json
import os
import sys

from pipeline.common import (
    REPO_ROOT, RAW_DIR, load_env, read_cache, write_cache, CallBudget,
    get_json_with_retry, canonicalize_url, domain_of,
)

ESTIMATED_COST_PER_CALL_USD = 0.015  # SerpAPI list pricing varies by plan; verify before a real run.


def load_queries(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# city -> a reasonable gl/hl pair for SerpAPI localization. Defaults to India.
CITY_LOCALE = {
    "Dubai": ("ae", "en"), "Abu Dhabi": ("ae", "en"), "Doha": ("qa", "en"),
    "Riyadh": ("sa", "en"), "Muscat": ("om", "en"),
}


def serpapi_url(query_text: str, city: str, api_key: str) -> str:
    gl, hl = CITY_LOCALE.get(city, ("in", "en"))
    from urllib.parse import quote
    return (
        f"https://serpapi.com/search.json?engine=google&q={quote(query_text)}"
        f"&num=15&gl={gl}&hl={hl}&location={quote(city)}&api_key={api_key}"
    )


def candidates_from_serpapi(raw: dict) -> list[str]:
    out = []
    for item in raw.get("organic_results", []):
        if "link" in item:
            out.append(canonicalize_url(item["link"]))
    return out


def candidates_from_perplexity_fallback(query_id: str) -> list[str]:
    out = []
    for path in glob.glob(os.path.join(RAW_DIR, "perplexity", "*.json")):
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        for item in raw.get("search_results", []):
            if isinstance(item, dict) and "url" in item:
                out.append(canonicalize_url(item["url"]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--max-calls", type=int, default=60)
    ap.add_argument("--queries", default=os.path.join(REPO_ROOT, "pipeline", "queries.csv"))
    args = ap.parse_args()

    queries = load_queries(args.queries)
    print(f"Plan: up to {len(queries)} SerpAPI calls (1 per query).")
    print(f"Rough cost estimate: ~${len(queries) * ESTIMATED_COST_PER_CALL_USD:.2f} "
          f"(verify current SerpAPI pricing before a real paid run).")

    if args.dry_run:
        print("--dry-run: no API calls will be made.")
        return

    load_env()
    api_key = os.environ.get("SERPAPI_KEY")
    results = {}

    if not api_key:
        print("SERPAPI_KEY not set — falling back to search_results embedded in cached "
              "Perplexity responses. LIMITATION: this candidate pool is narrower and "
              "biased toward whatever the answer engine itself already surfaced; it is "
              "not an independent organic-ranking sample. Documented in docs/DATA_CARD.md.")
        for q in queries:
            results[q["query_id"]] = candidates_from_perplexity_fallback(q["query_id"])
    else:
        if not args.yes:
            print("Refusing to make real API calls without --yes. Re-run with --yes to proceed.")
            sys.exit(1)
        budget = CallBudget(args.max_calls)
        for q in queries:
            cache_key = q["query_id"]
            cached = read_cache("serpapi", cache_key)
            if cached is not None:
                raw = cached
                print(f"[cache] {q['query_id']}")
            else:
                url = serpapi_url(q["query_text"], q["city"], api_key)
                try:
                    raw = get_json_with_retry(url, budget)
                except RuntimeError as e:
                    print(f"[FAILED] {q['query_id']}: {e}", file=sys.stderr)
                    continue
                write_cache("serpapi", cache_key, raw)
                print(f"[live]  {q['query_id']} (calls made so far: {budget.calls_made})")
            results[q["query_id"]] = candidates_from_serpapi(raw)
        print(f"\nReal API calls made this run: {budget.calls_made}")

    out_path = os.path.join(REPO_ROOT, "data", "candidates.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Wrote candidate pools for {len(results)} queries to {out_path}")


if __name__ == "__main__":
    main()
