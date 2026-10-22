"""
Shared cost-safety and caching helpers for every API-calling pipeline script.

Every script that spends money (Perplexity, SerpAPI) must:
  - support --dry-run (print the plan + cost estimate, make zero real calls)
  - support --max-calls (hard cap, default 60)
  - cache responses on disk so a re-run costs nothing
  - retry transient failures with exponential backoff
  - print exactly how many real calls were made
"""
import hashlib
import json
import os
import time
import random
import urllib.request
import urllib.error

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(REPO_ROOT, "data", "raw")

# Minimum viable pilot size, shared by pipeline.pilot_stats and pipeline.evaluate
# so the "underpowered" flag can never disagree between the two outputs.
# Below these thresholds, numbers are still computed and reported, but flagged
# clearly as preliminary rather than strong evidence.
MIN_USABLE_ROWS = 60
MIN_MINORITY_CLASS = 15


def load_env():
    """Load .env from repo root if python-dotenv is available; never prints values."""
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(REPO_ROOT, ".env"))
    except ImportError:
        pass


def cache_path(namespace: str, key: str) -> str:
    os.makedirs(os.path.join(RAW_DIR, namespace), exist_ok=True)
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return os.path.join(RAW_DIR, namespace, f"{digest}.json")


def read_cache(namespace: str, key: str):
    path = cache_path(namespace, key)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def write_cache(namespace: str, key: str, value) -> None:
    path = cache_path(namespace, key)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(value, f, indent=2, ensure_ascii=False)


class CallBudget:
    """Tracks and hard-caps the number of real (non-cached) API calls made in a run."""

    def __init__(self, max_calls: int):
        self.max_calls = max_calls
        self.calls_made = 0

    def spend(self, n: int = 1):
        if self.calls_made + n > self.max_calls:
            raise RuntimeError(
                f"--max-calls limit reached ({self.max_calls}). "
                f"Re-run with a higher --max-calls to continue, or rely on the cache."
            )
        self.calls_made += n


def post_json_with_retry(url: str, headers: dict, payload: dict, budget: CallBudget,
                          max_retries: int = 4, base_delay: float = 1.5, timeout: int = 30) -> dict:
    """POST JSON with exponential backoff retries. Spends exactly 1 call from budget."""
    budget.spend(1)
    data = json.dumps(payload).encode("utf-8")
    last_exc = None
    for attempt in range(max_retries):
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            if e.code in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                time.sleep(delay)
                last_exc = RuntimeError(f"HTTP {e.code}: {body[:300]}")
                continue
            raise RuntimeError(f"HTTP {e.code}: {body[:300]}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                time.sleep(delay)
                last_exc = e
                continue
            raise
    raise last_exc


def get_json_with_retry(url: str, budget: CallBudget, max_retries: int = 4,
                         base_delay: float = 1.5, timeout: int = 30) -> dict:
    budget.spend(1)
    last_exc = None
    for attempt in range(max_retries):
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            if e.code in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                time.sleep(delay)
                last_exc = RuntimeError(f"HTTP {e.code}: {body[:300]}")
                continue
            raise RuntimeError(f"HTTP {e.code}: {body[:300]}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                time.sleep(delay)
                last_exc = e
                continue
            raise
    raise last_exc


def canonicalize_url(url: str) -> str:
    """Strip tracking params, fragments, trailing slash; lowercase host."""
    from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

    parts = urlsplit(url.strip())
    host = parts.netloc.lower()
    path = parts.path.rstrip("/") or "/"
    tracking_prefixes = ("utm_",)
    tracking_exact = {"gclid", "fbclid", "msclkid", "ref", "source"}
    kept = [
        (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not (k.lower().startswith(tracking_prefixes) or k.lower() in tracking_exact)
    ]
    query = urlencode(kept)
    return urlunsplit((parts.scheme or "https", host, path, query, ""))


def domain_of(url: str) -> str:
    from urllib.parse import urlsplit
    return urlsplit(url).netloc.lower()
