# Project Diary -- DRAFT

DRAFT -- edit every entry to match what actually happened. Built only from
real git history (`git log --all --date=short --pretty=format:"%ad %s"` on
this repo). The real diary must be handwritten and guide-signed; this is a
starting point, not a substitute.

## Week of 2026-09-27 -- Upstream codebase received

- DRAFT -- edit to match what actually happened: Received the base
  "Citelytics" Streamlit application and full citation-predictor/ codebase
  (feat: add Streamlit app and complete Citelytics codebase).
- DRAFT: Added `run_streamlit.bat` Windows launcher.
- DRAFT: Fixed a blank-screen issue on Streamlit Cloud by making `app.py` a
  standalone entrypoint (later revisited -- see 2026-10-20 entry, this
  duplicate design was replaced with a delegating entrypoint).
- DRAFT: Fixed a missing `matplotlib` dependency and removed an unused
  import in requirements.
- DRAFT: Hardened feature-dictionary score extraction with safe clamping
  (robust to missing/out-of-range values).
- Dependabot bumped various JS/TS dependencies in the unrelated upstream
  Getcito monorepo (not our work; routine, no team action needed).

## Week of 2026-10-20 -- Final review preparation begins

- DRAFT: Cloned the project into a dedicated working branch
  (`final-review`) ahead of the CSD 415 Phase I final review.
- DRAFT: Completed a full read-only audit of the codebase
  (`docs/AUDIT.md`), identifying that the UI's headline model metrics
  (ROC-AUC 0.888, F1 0.784, etc.) were circular (computed from
  synthetically-labeled data where the label is a direct function of the
  same features scored) and unverifiable, and that a scrape failure
  silently substituted a fake demo page for any URL.
- DRAFT: Fixed the silent mock-fallback, replaced hard-coded metrics with
  live reads from a generated `artifacts/metrics.json` ("not yet
  evaluated" until real data exists), and added a Model Card /
  Limitations page to the app.
- DRAFT: Removed a committed secrets-capable file (`.env.local`, values
  were placeholder/localhost -- no rotation needed) and a committed
  runtime SQLite database from version control; fixed the `.gitignore`
  pattern that was supposed to exclude it.
- DRAFT: Closed an SSRF redirect-bypass gap in the scraper and added
  robots.txt compliance.
- DRAFT: Removed the dead duplicate `app.py` file, replacing it with a
  thin entrypoint that delegates to `streamlit_app.py`.
- DRAFT: Built the real-data pilot pipeline (`pipeline/`): query set (20
  local-business queries across 4 categories), Perplexity citation
  collection, SerpAPI/fallback candidate collection, dataset builder,
  pilot statistics, and a full evaluation script (GroupKFold-by-domain,
  rule-based/logistic-regression/XGBoost comparison, label-shuffle
  sanity check, feature-group ablation, SHAP explainability, calibration).
- DRAFT: Wrote supporting documentation -- `docs/DATA_CARD.md`,
  `docs/ETHICS_AND_LIMITS.md`, `STATUS.md`.
- DRAFT: Real API keys (Perplexity/SerpAPI) not yet available as of this
  entry -- real pilot data collection is pending the team providing them.
  Everything else (app fixes, pipeline code, tests, documentation)
  proceeded without needing real data.

## Week of 2026-10-21 -- Real data collection and evaluation
No Perplexity/SerpAPI budget was available, so this was done via the
manual-collection workaround (see `STATUS.md` Session 2) rather than
`PERPLEXITY_API_KEY` + `python -m pipeline.run_all`. Factual results below
are read directly from `data/pilot_stats.json` and `artifacts/metrics.json`
(no API calls logged -- `real_api_calls_logged: 0`):
- 300 queries, 300 citation records collected (one citation per query,
  via `collection_method="manual_web_ui"`), scaled up in three passes
  (100 -> 200 -> 300).
- 978 candidate rows scraped; scrape success rate 57.8% (592 usable rows:
  189 cited / 403 not cited).
- XGBoost ROC-AUC 0.69 +/- 0.06, logistic regression 0.70 +/- 0.08 --
  still numerically just ahead of XGBoost but the gap has narrowed as the
  dataset grew (it was 0.69 vs 0.64 at n=390); both clearly beat the
  rule-based baseline (0.47, at/below chance). (We also found and fixed a
  real bug in the evaluation itself: a single GroupKFold split's fold
  assignment depends on row order, so one run's AUC was really one
  arbitrary partition's estimate, not "the" AUC. Fixed by repeating
  GroupKFold 10x over shuffled row orders and pooling all 50 folds --
  the error bar has tightened at every scale: +/-0.19 (n=100) ->
  +/-0.12 (n=200) -> +/-0.06 (n=300).)
- Label-shuffle control: ROC-AUC 0.56 +/- 0.05 (close to chance, though a
  bit above the ideal 0.5 -- reported honestly rather than rounded down).
- Feature-group ablation: authority 0.69, structural 0.66, content 0.61
  (authority / local-business-legitimacy signals matter most, consistent
  across all three scales tested).
- Domain-type (directory/aggregator) flag: 0.77 with vs 0.69 without
  (a modest lift, not a dominant effect).
- Original synthetic-trained model scored on this real data: ROC-AUC
  0.49 (essentially chance, reinforcing the Phase 1 audit's circularity
  finding).
- Added a small "Page Health" checklist (meta title/description, image
  alt-text coverage, HTTPS, mobile viewport) as a secondary panel in the
  Analyze page -- supporting context only, not part of the citation model
  or its score.
TODO (team): add the narrative -- who ran which commands and when, how
long collection took, any blockers hit along the way, and team
reflections on the manual-collection workaround.

## Week of [TODO] -- Slides, report, and viva prep
TODO (team): fill in with actual rehearsal sessions, guide feedback on the
handout, and report-writing sessions.
