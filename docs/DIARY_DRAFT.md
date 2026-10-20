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

## Week of [TODO] -- Real data collection and evaluation
TODO (team): fill in once `PERPLEXITY_API_KEY` is provided and
`python -m pipeline.run_all` / `pipeline.evaluate` have actually been run
against real data. Record: how many queries/API calls were made, what the
scrape success rate was, and the real model metrics.

## Week of [TODO] -- Slides, report, and viva prep
TODO (team): fill in with actual rehearsal sessions, guide feedback on the
handout, and report-writing sessions.
