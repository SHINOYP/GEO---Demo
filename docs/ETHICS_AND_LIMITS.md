# Ethics and Limits

This document states, plainly, what this project does and does not do when
collecting data, and what the resulting tool should and should not be used
for. It is written to be defensible in front of a review panel.

## Scraping policy

- **robots.txt is honored.** `citation-predictor/backend/scraping/scraper.py`
  (`_check_robots_txt`) fetches and caches each target domain's
  `robots.txt` and refuses to fetch a path disallowed for our user-agent.
  If `robots.txt` cannot be fetched or parsed, we default to allow (the
  common case of no robots.txt present), matching standard crawler
  behavior.
- **Identification.** Every request sends a descriptive `User-Agent`
  string identifying the tool and a contact URL
  (`scraper.py: HEADERS["User-Agent"]`), so a site operator can tell who is
  requesting pages and why.
- **Timeouts.** Every request has a 15-second timeout
  (`scraper.py: TIMEOUT`) so a slow or hanging server cannot block the
  pipeline indefinitely.
- **Response size cap.** Responses are streamed and capped at 5 MB
  (`scraper.py: MAX_BYTES`) to avoid pulling down unexpectedly large files.
- **SSRF protection.** Requests to localhost, private/reserved IP ranges,
  and cloud metadata endpoints are blocked, including on every redirect hop
  (`scraper.py: _check_ssrf`, re-checked per redirect in `scrape()`).
- **Polite delays in batch collection.** `pipeline/build_dataset.py` adds a
  delay between requests to the same host when scraping the candidate pool
  for the pilot dataset, instead of firing requests back-to-back.
- **Public pages only.** We only fetch publicly accessible pages returned
  by search/citation APIs or entered directly by a user. We do not attempt
  to bypass logins, paywalls, CAPTCHAs, or any other access control.
- **No personal data collection.** The feature extractor reads page
  *structure and content* (headings, word counts, schema markup, contact
  info *displayed on the business's own public page*, etc.) — it does not
  collect, store, or infer personal data about private individuals. Local
  business contact details (phone/address/hours) are business information
  the business itself has published publicly, not personal data about a
  private person.

## API usage policy

- **Perplexity API** (`pipeline/collect_citations.py`) and **SerpAPI**
  (`pipeline/collect_candidates.py`, optional) are used strictly within
  each provider's published terms of service and rate limits.
- **Cost and call safety.** Every API-calling script supports `--dry-run`
  (prints the plan and estimated cost without calling anything),
  `--max-calls` (hard cap, default 60), on-disk response caching (so
  re-running a script costs nothing once data is cached), and retries with
  exponential backoff on transient failures. The number of real API calls
  made is always printed and logged.
- **No key leakage.** API keys are read only from a local, gitignored
  `.env` file. Nothing in the repo logs, prints, or commits a key value.
  See `.env.example` for the variable names the pipeline expects.

## What this tool should be used for

- Helping a local business understand *correlational* patterns between
  observable page features (structure, schema markup, factual density,
  etc.) and whether similar pages were cited by an AI answer engine for
  similar queries, in a small pilot sample.
- Teaching/demonstrating an explainable-ML workflow (XGBoost + SHAP) on a
  real, if small and imperfect, pilot dataset.

## What this tool should NOT be used for

- **Not a guarantee of citation.** The output is an estimated likelihood
  from observed correlations in a small pilot sample, not a promise that
  any specific AI engine will cite a given page.
- **Not evidence of causation.** A feature correlating with citation in
  the pilot sample does not mean changing that feature *causes* citation.
- **Not a way to reverse-engineer or manipulate an LLM's internal
  reasoning.** We do not use prompt injection, adversarial inputs aimed at
  an answer engine's model weights, data poisoning, or any other technique
  intended to manipulate how an AI system behaves. Every feature the model
  uses is a legitimate, publicly-visible content/structure property of a
  webpage (headings, schema markup, word counts, factual density, contact
  info) — the same kind of signal classical SEO tools already surface.
  Improving a page on these dimensions is standard content-quality work,
  not manipulation.
- **Not for scraping at scale beyond the stated pilot.** The pipeline is
  built for a small, documented pilot (a fixed query list, capped API
  calls); it is not intended to be run as an unbounded crawler.
