# Data Card — Real-Data Pilot

## Queries

`pipeline/queries.csv` — 20 realistic local-business queries, 5 per category
across 4 categories: gyms (Kerala cities), chauffeur/limo services (GCC
cities), kayaking/tour operators, dental clinics. Editable by the team.

## Collection

Two collection methods are supported, producing the identical
`data/citations.json` / `data/candidates.json` shape so every downstream
script (`build_dataset.py`, `pilot_stats.py`, `evaluate.py`) works
unchanged either way.

### Method A — automated (requires paid API keys)

1. **Citations** (`pipeline/collect_citations.py`): for each query, call
   Perplexity's search-enabled chat completions API (`model="sonar"`).
   Default 1 run per query; `--repeats N` runs it N times per query to
   measure label stability (citations are not always identical run to run).
   Raw JSON responses are cached per `(query, repeat)` under
   `data/raw/perplexity/`.
2. **Candidates** (`pipeline/collect_candidates.py`): for the same queries,
   get the top 10-15 organic results via SerpAPI if `SERPAPI_KEY` is set.
   **If no SerpAPI key is configured**, the candidate pool falls back to the
   `search_results` already embedded in the cached Perplexity response —
   this is a real limitation: that pool is narrower and biased toward
   whatever the answer engine itself already surfaced, not an independent
   organic-ranking sample.

### Method B — manual (free, no API keys)

Used for this project's actual pilot run, since a paid Perplexity API key
was not available to the team. A team member manually searched each of
the 20 queries on the free `perplexity.ai` website (recording the cited
source URLs) and on `google.com` (recording the top organic result URLs,
to serve as real "not cited" comparison examples). Those results were
typed into `data/manual_citations_template.txt` and converted to the
standard format with `python -m pipeline.import_manual_citations`.

This is genuinely real, human-collected data — not synthetic — just
gathered by a person using the public websites instead of a script
calling a paid API. Every record from this path is tagged
`"collection_method": "manual_web_ui"` in `data/citations.json` so this
is never ambiguous later, and the limitations are the same as Method A
plus: a human's reading of "which sources were cited" can occasionally
miss or misread a source compared to parsing raw API JSON, and only 1
observation per query was collected (no `--repeats` equivalent for
measuring citation stability under the manual method).

## Label rule

For a given query:

- `label = 1` if the page's **canonical URL** (scheme/host lowercased,
  trailing slash stripped, tracking query params like `utm_*`/`gclid`
  removed, fragment dropped — see `pipeline/common.py: canonicalize_url`)
  appears among that query's cited URLs returned by Perplexity.
- `label = 0` otherwise.
- A secondary analysis may instead match on **domain** rather than exact
  URL, since the same business's citation sometimes lands on a slightly
  different path.

**Candidate pool** for a query = `cited_urls ∪ organic_results`. Every URL
in that union gets one row in `data/dataset.csv` (scraped, feature-extracted,
labeled), so the dataset contains both positive (cited) and negative
(not-cited-but-ranking) examples per query.

## Known limitations of this label rule

- **Negatives are not a random sample of the web.** They are pages that
  already rank organically (or were otherwise surfaced by the answer
  engine) for the query — i.e. already "good enough" pages by classical
  search standards. The model therefore learns to distinguish *cited vs.
  not-cited among already-competitive pages*, not *citable vs. the entire
  web*.
- **Citation is non-deterministic.** Re-running the same query can return a
  different citation set. A single observation per query (the default,
  `--repeats 1`) is a noisy label; `--repeats 3+` measures this noise
  directly by checking how often the same URL is cited across repeats.
- **Domain-level vs URL-level matching** can disagree (e.g. a business's
  homepage is cited in one run, a specific service page in another) —
  reported separately as a sensitivity check in `artifacts/metrics.json`.
- **Small n.** Twenty queries is a pilot, not a representative sample of
  local-business search behavior; see `data/pilot_stats.json` for the
  actual counts and `underpowered` flag.
