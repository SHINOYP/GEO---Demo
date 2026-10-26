# Individual Contributions

Three modules, each assignable to one team member. Every member must still
answer overview-level questions about the other two modules -- the panel
questions every student on the whole project.

## Module 1 -- Data Collection, Labels, and Pilot Statistics

**Files:** `pipeline/queries.csv`, `pipeline/collect_citations.py`,
`pipeline/collect_candidates.py`, `pipeline/pilot_stats.py`,
`pipeline/common.py`, `docs/DATA_CARD.md`

**5 things this owner must explain on a whiteboard:**
1. The query set design: 300 queries, 4 categories (75 each:
   gyms/India, chauffeur/GCC, kayaking, dental), why these categories.
2. How citations are actually collected (Perplexity `sonar` API call,
   what "search-enabled chat completion" means, how cited URLs are
   extracted from the response).
3. The exact label rule: canonical-URL match against cited URLs; why
   canonicalization (strip tracking params/fragments/trailing slash,
   lowercase host) matters for correct matching.
4. Why the candidate pool is `cited_urls UNION organic_results`, and the
   documented limitation when SerpAPI is unavailable (falls back to a
   narrower engine-biased pool).
5. How cost-safety works: `--dry-run`, `--max-calls`, on-disk caching,
   exponential backoff -- and why these matter for a paid external API.

**5 likely panel questions:**
1. "How do you know a citation is real and not just the page ranking
   organically?" -- because the match is specifically against the
   citations field (or search_results) the API returns as justification
   for its answer, not against organic search rank.
2. "What if the same query returns different citations each time you run
   it?" -- `--repeats N` measures this directly; a single run (default)
   is a known noisy label, documented in `docs/DATA_CARD.md`.
3. "Why only 300 queries, and why that category mix?" -- scaled up in four
   passes (20 -> 100 -> 200 -> 300) each time the signal held and error
   bars kept tightening; the free manual-collection method's time cost
   (not a paid API's dollar cost) still bounds further scale-up (see
   Conclusion/Future Work).
4. "What happens if PERPLEXITY_API_KEY is missing?" -- the script fails
   loudly with a clear error, never silently fabricates data.
5. "Is this data collection ethical/compliant?" -- see
   `docs/ETHICS_AND_LIMITS.md`: public pages only, provider ToS respected,
   no personal data collected.

## Module 2 -- Scraping and Feature Extraction

**Files:** `citation-predictor/backend/scraping/scraper.py`,
`citation-predictor/backend/features/extractor.py`,
`pipeline/build_dataset.py`

**5 things this owner must explain on a whiteboard:**
1. The SSRF protection design: blocked hosts/ranges, DNS resolution before
   connecting, and why redirects must be re-validated on every hop (the
   bug that was fixed: `allow_redirects=True` did its own DNS resolution
   without re-checking).
2. robots.txt compliance: how it's fetched/cached per host and why default
   to "allow" when robots.txt itself can't be fetched.
3. The 45 model features: pick 5-6 by name and explain exactly how each is
   computed from the HTML (e.g. `factual_density`, `schema_present`,
   `heading_hierarchy_score`).
4. Why some "derived" scores (`macro_structure_score` etc.) are built from
   other raw features already in the feature set, and why that matters for
   avoiding double-counting.
5. How `build_dataset.py` detects near-duplicate templated pages (HTML
   structural fingerprinting) and classifies `domain_type` via a
   transparent rule list (not an ML classifier).

**5 likely panel questions:**
1. "Why BeautifulSoup/requests instead of a headless browser like
   Selenium/Playwright?" -- simpler, faster, no JS execution needed for
   the content/structure signals used; trade-off is missing JS-rendered
   content, a documented limitation.
2. "What stops someone from using this scraper to attack an internal
   service?" -- the SSRF guard (blocked ranges, redirect re-validation)
   and response size/timeout caps.
3. "Which feature is most likely to leak the label?" -- `factual_density`
   and the macro/meso/micro structure scores, since they're also the
   heaviest-weighted terms in the OLD synthetic label formula (see
   `docs/AUDIT.md` Q3) -- a key reason the real pilot label is built
   independently from citation data, not from a hand-written formula.
4. "How do you handle a page that returns 404 or times out?" -- recorded
   as `scrape_status=failed` with a reason, not silently dropped or
   faked.
5. "Why cache scraped HTML locally?" -- reruns of the pipeline cost zero
   additional requests to the target sites, respecting politeness and
   making the pipeline reproducible.

## Module 3 -- Model, SHAP, Evaluation, and App

**Files:** `citation-predictor/backend/models/model_loader.py`,
`citation-predictor/backend/explainability/shap_explainer.py`,
`pipeline/evaluate.py`, `streamlit_app.py`

**5 things this owner must explain on a whiteboard:**
1. Why XGBoost (gradient-boosted trees) was chosen over a neural network
   or transformer at this dataset size -- fewer parameters, handles
   tabular/mixed-type features well, less prone to overfitting on a small
   pilot, and SHAP's TreeExplainer gives exact (not approximate)
   attributions for tree models.
2. Why GroupKFold by domain, not a random split -- prevents the same
   business's pages appearing in both train and test, which would leak
   information and inflate apparent performance.
3. What SHAP actually explains: the contribution of each feature to this
   classifier's output for one page -- NOT how the underlying LLM decided
   to cite anything. Be ready to state this distinction unprompted.
4. The sanity checks built into `pipeline/evaluate.py`: label-shuffle
   control (expect AUC ~0.5), feature-group ablation, domain-type leakage
   check, and comparison against the old synthetic-trained model on real
   data.
5. The train/serve consistency guarantee: the app builds its feature row
   using the exact same `FEATURE_COLUMNS` order the model was trained on
   (`tests/test_feature_model_match.py` checks this automatically).

**5 likely panel questions:**
1. "Is 0.85 AUC good?" (or whatever the real number turns out to be) --
   answer relative to the rule-based baseline and the "underpowered" flag
   in `artifacts/metrics.json`, never in isolation.
2. "How do you know the model isn't just memorizing noise?" -- the
   label-shuffle control: if shuffled labels also got high AUC, that would
   indicate leakage; a result near 0.5 after shuffling is the sanity
   check passing.
3. "What does precision vs. recall mean here, concretely?" -- precision:
   of pages the model flagged as likely-cited, how many actually were;
   recall: of pages actually cited, how many the model flagged.
4. "Why is accuracy reported together with class balance?" -- accuracy
   alone is misleading under class imbalance; always paired with the
   positive/negative counts.
5. "What happens if the pilot data turns out to be too small?" --
   `artifacts/metrics.json["underpowered"]` is set true automatically
   below a minimum row/class-size threshold, and the UI/report must then
   present results as preliminary, not conclusive.
