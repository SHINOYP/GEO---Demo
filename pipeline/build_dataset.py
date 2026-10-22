"""
Build data/dataset.csv: scrape every unique candidate URL, extract features,
and attach the citation label.

Label rule (see docs/DATA_CARD.md): label=1 if the canonical URL appears
among that query's cited URLs (data/citations.json), else 0. The candidate
pool for a query is cited_urls UNION candidates (data/candidates.json).

Usage:
    python -m pipeline.build_dataset
    python -m pipeline.build_dataset --delay 1.0
"""
import argparse
import csv
import hashlib
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlsplit

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "citation-predictor", "backend")
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, REPO_ROOT)

from pipeline.common import canonicalize_url, domain_of  # noqa: E402

DIRECTORY_DOMAINS = {
    "yelp.com", "tripadvisor.com", "google.com", "facebook.com", "instagram.com",
    "yellowpages.com", "justdial.com", "sulekha.com", "practo.com", "zomato.com",
    "booking.com", "getyourguide.com", "viator.com", "linkedin.com",
    # Indian local-business / healthcare listing directories — common
    # citation targets when a business has no real website of its own.
    "magicpin.in", "magicpin.com", "yappe.in", "whatclinic.com",
    "docindia.org", "drlogy.com", "clinicspots.com", "credihealth.com",
    "apollo247.com", "bajajfinservhealth.in", "quickerala.com",
    "discover.lyfskills.com", "yellowpages-uae.com", "threebestrated.in",
    "wanderlog.com",
}
SOCIAL_DOMAINS = {"facebook.com", "instagram.com", "twitter.com", "x.com", "linkedin.com", "youtube.com"}
NEWS_HINTS = ("news", "blog", "magazine", "times", "post", "herald", "medium.com")


def classify_domain_type(domain: str) -> str:
    """Simple, transparent rule list — not an ML classifier, so it's easy to audit."""
    bare = domain[4:] if domain.startswith("www.") else domain
    if any(bare.endswith(d) for d in SOCIAL_DOMAINS):
        return "social"
    if any(bare.endswith(d) for d in DIRECTORY_DOMAINS):
        return "directory_aggregator"
    if any(hint in bare for hint in NEWS_HINTS):
        return "news_blog"
    return "business_site"


def build_rows_to_scrape(citations: list, candidates: dict) -> list:
    """For each query, build the candidate pool as cited_urls UNION candidates,
    and label each (query_id, url) pair 1 if the url was cited for that
    query, else 0. Returns a list of (query_id, category, city, url, label).

    The pool (a set union) is iterated via sorted() rather than directly, so
    row order is deterministic given the same inputs — CPython's set
    iteration order depends on hash randomization and is not stable across
    processes unless PYTHONHASHSEED is pinned.
    """
    rows_to_scrape = []
    for rec in citations:
        qid, category, city = rec["query_id"], rec["category"], rec["city"]
        cited = set(rec.get("cited_urls", []))
        cands = set(canonicalize_url(u) for u in candidates.get(qid, []))
        pool = cited | cands
        for url in sorted(pool):
            rows_to_scrape.append((qid, category, city, url, 1 if url in cited else 0))
    return rows_to_scrape


def assign_duplicate_templates(url_to_fingerprint: dict) -> tuple:
    """Deterministically pick one 'canonical' URL per structural fingerprint
    (the alphabetically-first URL sharing that HTML skeleton) and count the
    rest as duplicates.

    This must not depend on thread/completion order: scraping runs
    concurrently via ThreadPoolExecutor, and which worker finishes first for
    a given fingerprint is a race, not a stable ordering. Doing the
    canonical-vs-duplicate assignment in a separate, sorted pass (instead of
    inline as results arrive) keeps is_duplicate_template reproducible
    across runs of the exact same input data.
    """
    seen = {}
    duplicate_count = 0
    for url in sorted(url_to_fingerprint):
        fingerprint = url_to_fingerprint[url]
        if not fingerprint:
            continue
        if fingerprint in seen:
            duplicate_count += 1
        else:
            seen[fingerprint] = url
    return seen, duplicate_count


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def html_fingerprint(raw_html: str) -> str:
    """Crude template-dedup signature: structural skeleton with text stripped."""
    skeleton = re.sub(r">[^<]*<", "><", raw_html)
    skeleton = re.sub(r'"[^"]{0,80}"', '""', skeleton)
    return hashlib.sha256(skeleton.encode("utf-8", errors="ignore")).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--delay", type=float, default=1.0, help="Polite delay (s) between requests to the same host.")
    ap.add_argument("--workers", type=int, default=12, help="Concurrent scraper threads (I/O-bound, safe to parallelize).")
    ap.add_argument("--citations", default=os.path.join(REPO_ROOT, "data", "citations.json"))
    ap.add_argument("--candidates", default=os.path.join(REPO_ROOT, "data", "candidates.json"))
    ap.add_argument("--out", default=os.path.join(REPO_ROOT, "data", "dataset.csv"))
    args = ap.parse_args()

    from scraping.scraper import scrape, ScrapingError
    from features.extractor import extract_features
    from bs4 import BeautifulSoup

    citations = load_json(args.citations, [])
    candidates = load_json(args.candidates, {})

    if not citations:
        print("ERROR: data/citations.json not found or empty. Run "
              "`python -m pipeline.collect_citations --yes` first.", file=sys.stderr)
        sys.exit(1)

    # (query_id, category, city, url, label) rows: pool = cited_urls UNION candidates per query.
    rows_to_scrape = build_rows_to_scrape(citations, candidates)

    # A query whose citations+candidates collection both came up empty
    # contributes zero rows and would otherwise vanish from the dataset
    # with no trace, so flag it explicitly.
    queries_with_rows = {r[0] for r in rows_to_scrape}
    empty_queries = sorted(rec["query_id"] for rec in citations if rec["query_id"] not in queries_with_rows)
    if empty_queries:
        print(f"WARNING: {len(empty_queries)} quer{'y' if len(empty_queries) == 1 else 'ies'} "
              f"contributed zero rows (empty cited_urls and no candidates): {empty_queries}",
              file=sys.stderr)

    unique_urls = sorted(set(r[3] for r in rows_to_scrape))
    print(f"Candidate pool across all queries: {len(rows_to_scrape)} (query_id, url) pairs, "
          f"{len(unique_urls)} unique URLs. Scraping with {args.workers} concurrent threads "
          f"(I/O-bound waits; a per-host lock spaces out request *start* times by "
          f"--delay seconds, but does not guarantee two requests to the same host never "
          f"overlap in flight if a fetch takes longer than --delay).")

    html_cache_dir = os.path.join(REPO_ROOT, "data", "html_cache")
    os.makedirs(html_cache_dir, exist_ok=True)

    host_lock = threading.Lock()
    last_fetch_by_host = {}

    def fetch_one(url):
        """Runs in a worker thread. Returns (url, status, reason, feats, fingerprint)."""
        host = domain_of(url)
        with host_lock:
            wait = args.delay - (time.time() - last_fetch_by_host.get(host, 0))
            if wait > 0:
                time.sleep(wait)
            last_fetch_by_host[host] = time.time()

        html_path = os.path.join(html_cache_dir, hashlib.sha256(url.encode()).hexdigest()[:24] + ".html")
        try:
            if os.path.exists(html_path):
                with open(html_path, "r", encoding="utf-8") as f:
                    raw_html = f.read()
                soup = BeautifulSoup(raw_html, "lxml")
            else:
                res = scrape(url)
                raw_html = res["raw_html"]
                soup = res["soup"]
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(raw_html)

            fingerprint = html_fingerprint(raw_html)
            feats = extract_features(soup, url)["model_features"]
            return url, "ok", "", feats, fingerprint
        except ScrapingError as e:
            return url, "failed", f"ScrapingError: {e}", None, None
        except Exception as e:
            return url, "failed", f"{type(e).__name__}: {e}", None, None

    scraped_cache = {}  # url -> (status, reason, features_dict or None, fingerprint or None)
    status_counts = {}
    done = 0

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(fetch_one, url): url for url in unique_urls}
        for future in as_completed(futures):
            url, status, reason, feats, fingerprint = future.result()
            done += 1
            status_counts[status] = status_counts.get(status, 0) + 1
            scraped_cache[url] = (status, reason, feats, fingerprint)
            print(f"[{done}/{len(unique_urls)}] [{status}] {url} ({reason[:60] if reason else 'ok'})")

    # Decide which URL is "canonical" per structural fingerprint in a
    # separate, deterministic pass — not by thread-completion order, which
    # varies run to run even against byte-identical cached HTML.
    url_to_fingerprint = {url: scraped_cache[url][3] for url in unique_urls}
    seen_fingerprints, duplicate_count = assign_duplicate_templates(url_to_fingerprint)

    out_rows = []
    for qid, category, city, url, label in rows_to_scrape:
        status, reason, feats, fingerprint = scraped_cache[url]
        row = {
            "query_id": qid, "category": category, "city": city,
            "url": url, "domain": domain_of(url), "label": label,
            "scrape_status": status, "scrape_failure_reason": reason,
            "domain_type": classify_domain_type(domain_of(url)),
            "is_duplicate_template": fingerprint is not None and seen_fingerprints.get(fingerprint) != url,
        }
        if feats:
            row.update(feats)
        out_rows.append(row)

    fieldnames = sorted({k for r in out_rows for k in r.keys()})
    # keep identifying columns first
    front = ["query_id", "category", "city", "url", "domain", "label",
             "scrape_status", "scrape_failure_reason", "domain_type", "is_duplicate_template"]
    fieldnames = front + [f for f in fieldnames if f not in front]

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"\nScrape status counts: {status_counts}")
    print(f"Duplicate-template URLs detected: {duplicate_count}")
    print(f"Wrote {len(out_rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
