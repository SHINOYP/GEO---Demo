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
import time
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
}
SOCIAL_DOMAINS = {"facebook.com", "instagram.com", "twitter.com", "x.com", "linkedin.com", "youtube.com"}
NEWS_HINTS = ("news", "blog", "magazine", "times", "post", "herald", "medium.com")


def classify_domain_type(domain: str) -> str:
    """Simple, transparent rule list — not an ML classifier, so it's easy to audit."""
    bare = domain.replace("www.", "")
    if any(bare.endswith(d) for d in SOCIAL_DOMAINS):
        return "social"
    if any(bare.endswith(d) for d in DIRECTORY_DOMAINS):
        return "directory_aggregator"
    if any(hint in bare for hint in NEWS_HINTS):
        return "news_blog"
    return "business_site"


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

    # Build per-query union of cited URLs and candidate URLs, plus which
    # query/category/city a URL belongs to (a URL can appear under multiple
    # queries; we keep one row per (query_id, url)).
    rows_to_scrape = []  # (query_id, category, city, url, label)
    for rec in citations:
        qid, category, city = rec["query_id"], rec["category"], rec["city"]
        cited = set(rec.get("cited_urls", []))
        cands = set(canonicalize_url(u) for u in candidates.get(qid, []))
        pool = cited | cands
        for url in pool:
            rows_to_scrape.append((qid, category, city, url, 1 if url in cited else 0))

    print(f"Candidate pool across all queries: {len(rows_to_scrape)} (query_id, url) pairs, "
          f"{len(set(r[3] for r in rows_to_scrape))} unique URLs.")

    last_fetch_by_host = {}
    html_cache_dir = os.path.join(REPO_ROOT, "data", "html_cache")
    os.makedirs(html_cache_dir, exist_ok=True)

    seen_fingerprints = {}
    duplicate_count = 0
    status_counts = {}
    out_rows = []

    scraped_cache = {}  # url -> (status, reason, features_dict or None, fingerprint or None)

    for qid, category, city, url, label in rows_to_scrape:
        if url not in scraped_cache:
            host = domain_of(url)
            delay_needed = args.delay - (time.time() - last_fetch_by_host.get(host, 0))
            if delay_needed > 0:
                time.sleep(delay_needed)

            html_path = os.path.join(html_cache_dir, hashlib.sha256(url.encode()).hexdigest()[:24] + ".html")
            status, reason, feats, fingerprint = "unknown", "", None, None
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
                last_fetch_by_host[host] = time.time()

                fingerprint = html_fingerprint(raw_html)
                if fingerprint in seen_fingerprints and seen_fingerprints[fingerprint] != url:
                    duplicate_count += 1

                feats = extract_features(soup, url)["model_features"]
                status, reason = "ok", ""
            except ScrapingError as e:
                status, reason = "failed", f"ScrapingError: {e}"
                last_fetch_by_host[host] = time.time()
            except Exception as e:
                status, reason = "failed", f"{type(e).__name__}: {e}"
                last_fetch_by_host[host] = time.time()

            status_counts[status] = status_counts.get(status, 0) + 1
            if fingerprint:
                seen_fingerprints.setdefault(fingerprint, url)
            scraped_cache[url] = (status, reason, feats, fingerprint)
            print(f"[{status}] {url} ({reason[:60] if reason else 'ok'})")

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
