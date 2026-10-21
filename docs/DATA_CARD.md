# Data Card — Real-Data Pilot

## Queries

`pipeline/queries.csv` — 200 realistic local-business queries, 50 per category
across 4 categories: gyms (Indian cities), chauffeur/limo services (GCC
cities), kayaking/tour operators (Indian destinations), dental clinics
(Indian cities). Editable by the team. (Started as a 100-query pilot,
25/category; scaled to 200 after the first real evaluation showed a
promising but wide-error-bar signal.)

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
was not available to the team. Two different sources fed the two halves
of the data, and they are NOT the same kind of source — this distinction
matters and should be stated plainly in the viva:

- **Citations** (`data/citations.json`, `cited_urls`): a team member
  manually searched each of the 200 queries on the free `perplexity.ai`
  website and copied down the URLs Perplexity's AI actually cited in its
  answer. This is the part that has to be a real AI answer engine's own
  behavior — nothing else can substitute for it, since the whole research
  question is "what does an AI engine choose to cite."
- **Candidate pool** (`data/candidates.json`, the "not necessarily cited"
  comparison set): built using an AI coding assistant's own web search
  tool, run once per query, NOT a human manually searching google.com.
  It is organic-style search results, used only to give the model real
  "not cited" examples to contrast against — it is not claimed to be
  Google's actual ranking, and its results may differ from what a human
  typing the same query into google.com would see (different backend,
  no personalization, no login).

Results were typed/compiled into `data/manual_citations_template.txt`
format and converted to the standard JSON shape with
`python -m pipeline.import_manual_citations`.

This is genuinely real, non-fabricated data for both halves — just
collected by a human using a website (citations) and a different search
tool (candidates) instead of the two paid APIs. Every citation record is
tagged `"collection_method": "manual_web_ui"` so this is never ambiguous
later. Limitations beyond Method A's: a human's reading of "which
sources were cited" can occasionally miss or misread a source compared
to parsing raw API JSON; only 1 observation per query was collected (no
`--repeats` equivalent for measuring citation stability); and the
candidate pool's search backend is not identified/guaranteed to match
Google's, so "organic ranking" here is approximate, not authoritative.

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
