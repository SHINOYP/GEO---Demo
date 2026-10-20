# STATUS

## 2026-10-20 — Session 1

**Done:**
- Phase 0: cloned repo to `geo-demo`, created `final-review` branch, venv
  setup in progress (slow network; large wheels like xgboost/pandas/shap
  taking a long time to download).
- Phase 1: wrote `docs/AUDIT.md` — full read-only audit. Headline finding:
  the UI's ROC-AUC 0.888 / F1 0.784 / 79.0% accuracy numbers are circular
  (synthetic labels are a linear formula of the same features the model is
  scored on) and unverifiable (never reproduced anywhere in the repo).
  Confirmed a silent mock-fallback that substitutes a fake dental-clinic
  page for ANY failed scrape of ANY user URL.
- Phase 2 (honesty fixes, committed):
  - Removed the silent scrape-failure mock fallback; fixtures now only
    load when explicitly selected from the demo dropdown, with a
    persistent "DEMO FIXTURE" banner.
  - Replaced hard-coded metrics in the UI with live reads from
    `artifacts/metrics.json` ("not yet evaluated" until the real pipeline
    runs).
  - Added a "Model Card / Limitations" page and a disclaimer on every
    prediction screen.
  - Untracked `.env.local` (upstream, placeholder values, no rotation
    needed) and a committed SQLite DB; fixed the `.gitignore` pattern that
    was supposed to exclude it.
  - Closed an SSRF redirect-bypass gap in the scraper and added robots.txt
    compliance.
  - Removed the dead duplicate `app.py`; it now delegates to
    `streamlit_app.py` so there's one source of truth.
  - Removed unused `matplotlib` dependency from `requirements.txt`.
- Phase 3 (pipeline, written, NOT yet run — see blocker):
  - `pipeline/queries.csv` (20 queries, 4 categories).
  - `pipeline/collect_citations.py`, `collect_candidates.py`,
    `build_dataset.py`, `pilot_stats.py`, `run_all.py`, `evaluate.py` — all
    with `--dry-run`, `--max-calls` cost caps, on-disk caching, retries.
  - `docs/DATA_CARD.md`, `docs/ETHICS_AND_LIMITS.md`.

**Blocker:** need `PERPLEXITY_API_KEY` (required) and optionally
`SERPAPI_KEY` (optional — falls back to a narrower candidate pool if
absent) to actually run the real-data pilot collection. Put them in a new
`.env` file at the repo root (see `pipeline/.env.example`) — never commit
it. Once provided, next step is `python -m pipeline.run_all --dry-run` to
sanity check, then a real run with `--yes --max-calls <n>`.

**Next (once keys are provided / pip install finishes):**
- Run `pipeline.run_all` for real, then `pipeline.evaluate`.
- Phase 5 app/model integration + demo-safety offline mode.
- Phase 6 pytest suite.
- Phase 7 viva prep docs (UNDERSTANDING, WHITEBOARD, VIVA_QA, red-team pass).
- Phase 8 slides, Phase 9 report/references/diary/contributions.

**No blockers on anything else** — continuing autonomously.
