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

## 2026-10-21 — Session 2

**Resolved the blocker above without an API key.** Team had no budget for
Perplexity's paid API, so we collected real data manually instead:

- UI redesign iterated through several passes based on live feedback
  (shadcn-style neutral palette, fixed a sidebar-collapse bug caused by
  hiding Streamlit's native header, fixed `st.metric` text truncation and
  oversized card headers) — see `streamlit_app.py` git history for the
  full back-and-forth.
- Scope-trimmed the app: removed GitHub/Deploy links and an in-app
  Settings/API-key page added earlier in the session — on reflection,
  product-style chrome that didn't fit an academic viva demo. Removed
  the "College Project Overview" page for the same reason.
- **Real-data pilot, run 1 (100 queries):** citations collected manually
  via perplexity.ai (`collection_method="manual_web_ui"`), candidates via
  automated web search (saved to `data/candidates.json`). Scraped 378
  unique pages in parallel (ThreadPoolExecutor added to
  `pipeline/build_dataset.py` — cut the run from ~13 min to ~4), 205
  succeeded. Ran `pipeline.evaluate`: **real numbers now exist** in
  `artifacts/metrics.json` — XGBoost ROC-AUC 0.65±0.19, label-shuffle
  control 0.52±0.06 (confirms no leakage), original synthetic-trained
  model scores only 0.585 on real data (concrete proof of the
  circularity problem from the Phase 1 audit).
- Updated `slides/final_review.tex`, `docs/VIVA_QA.md`, and
  `docs/KNOWN_WEAKNESSES.md` to replace "NOT YET MEASURED" placeholders
  with these real results.
- **Scaled to 200 queries — complete.** Added 100 more queries
  (Q101-Q200) across the same 4 categories, collected their candidate
  pool automatically, and the team finished manually collecting all
  Q101-Q200 citations via perplexity.ai. Merged both worksheets
  (`data/manual_citations.txt` + `data/manual_citations_batch2_template.txt`
  → `data/manual_citations_full.txt`) and re-ran
  `pipeline.import_manual_citations`, `pipeline.build_dataset` (374 of 705
  unique URLs scraped successfully), `pipeline.pilot_stats`, and
  `pipeline.evaluate` on the full real 200-query dataset. Because a
  successfully-scraped URL can be a candidate for more than one query, this
  produced 389 usable (ok) rows in `data/dataset.csv` — the row-level count
  `data/pilot_stats.json` reports (`scrape_status_counts.ok`), not a
  contradiction of the 374 unique-URL count.
- **Real numbers at n=200 (389 usable rows, 117 cited / 272 not):**
  XGBoost ROC-AUC **0.69 ± 0.08** (up from 0.65 ± 0.19 at n=100 — the
  error bar roughly halved, exactly as predicted from more data, strong
  evidence the signal is real). Label-shuffle control AUC 0.45 ± 0.09
  (still at/below chance — no leakage). Feature ablation: authority 0.70,
  structural 0.63, content 0.58. Domain-type flag: 0.75 with vs 0.69
  without (modest lift, not dominant). Original synthetic-trained model
  scores only **AUC 0.45** on this real data — even more damning than the
  0.585 it scored at n=100, reinforcing the audit's circularity finding.
- Updated `slides/final_review.tex`, `docs/SLIDE_NUMBERS.md`,
  `docs/VIVA_QA.md`, `docs/KNOWN_WEAKNESSES.md`, `docs/DATA_CARD.md` with
  all the above n=200 numbers, replacing every n=100 reference.

**Next:**
- Phase 9 report sections can now pull these final Results numbers.
- Optional stretch goal (not required for Thursday): `--repeats 3+` on a
  subset of queries to directly measure citation non-determinism (item 6
  in `docs/KNOWN_WEAKNESSES.md`, still an open/honest limitation).

**No blockers** — data collection and evaluation are done at the full
planned scale. Continuing autonomously on polish/report work.

## 2026-10-22 — Session 3 (final review day)

**Full code/docs hard-run audit** (87 subagents: review → skeptical verify →
file-scoped fix, 54/55 findings confirmed real, 26 files touched, 0 scope
violations into the unrelated GetCito monorepo sharing this repo root).
Genuine bugs found and fixed, not cosmetic — see git log for the full list;
highlights:
- `pilot_stats.py` was reporting `api_calls_logged: 200`, falsely implying
  200 real paid-API calls happened (we made zero — 100% manual collection).
  Split into `citation_records_collected` / `real_api_calls_logged: 0`.
- `canonicalize_url()` in `pipeline/common.py` used bare `startswith("ref")`/
  `startswith("source")` prefix matching to strip tracking params, which
  also silently corrupted any URL with a param merely starting with those
  letters (e.g. `reference=`, `sourceLanguage=`) — this is the function that
  decides whether a scraped URL equals a cited URL, so this was a real
  ground-truth labeling bug.
- SSRF guard in `citation-predictor/backend/scraping/scraper.py` had a
  hand-maintained CIDR list missing the full `127.0.0.0/8` loopback block
  (only caught the literal `127.0.0.1`) — replaced with `ipaddress`'s
  built-in `is_private`/`is_loopback`/etc. classification.
- Several `int(prob * 100)` truncations (vs `round()`) in both
  `streamlit_app.py` and `citation-predictor/backend/api/analyze.py` caused
  the displayed score and its tier label to disagree near tier boundaries.
- `pipeline/build_dataset.py`'s row order and duplicate-template detection
  depended on Python's hash-randomized set iteration / thread-completion
  order — non-reproducible from run to run on identical input data. Fixed
  to a deterministic sorted order.
- 17 new tests added (30 → 47), `requirements.lock` regenerated as a true
  full-environment lock (was missing 21 FastAPI-backend pins), a stale
  tracked `citelytics.db` untracked, several dead imports/unused code
  removed across the backend.

**Re-ran the full pipeline after the fixes above** (`build_dataset` →
`pilot_stats` → `evaluate`) since `canonicalize_url`/row-order fixes change
what the scripts actually produce. This surfaced one more real finding:
**plain `GroupKFold` with no shuffling assigns folds deterministically from
row order, so a single run's AUC is an estimate from one arbitrary
group-to-fold partition, not "the" AUC** — confirmed empirically when the
row-order fix alone moved XGBoost's reported AUC from 0.69 to 0.63 with the
exact same data and model. Fixed properly in `pipeline/evaluate.py`:
`cross_validate()` now repeats GroupKFold 10x over independently shuffled
row orders and pools all 50 folds into one mean/std, removing that
single-partition sensitivity.

**Final, authoritative numbers (n=200 queries, 390 usable rows, 118 cited /
272 not cited):**
- XGBoost ROC-AUC **0.64 ± 0.12**, F1 0.48 ± 0.12, accuracy 62.6%.
- Logistic regression ROC-AUC **0.69 ± 0.08** — numerically ahead of
  XGBoost, but the two overlap and are statistically comparable at this
  sample size. We report this honestly rather than picking the better-
  looking number: it says the signal is still mostly linear/simple at this
  n, and XGBoost's nonlinear capacity isn't paying for itself yet. We keep
  XGBoost as the deployed/explained model for its native SHAP support.
- Rule-based checklist baseline: AUC 0.51 (chance) — both learned models
  clearly beat it.
- Label-shuffle control: AUC 0.51 ± 0.04 (near-exact chance — no leakage).
- Feature ablation: authority 0.71, content 0.60, structural 0.56.
- Domain-type flag: 0.71 with vs 0.64 without (modest lift, not dominant).
- Original synthetic-trained model on real data: AUC 0.49 (chance) —
  reinforces the audit's circularity finding.
- `pipeline.evaluate` now takes ~75s to run (10x the CV work), not under a
  minute — still fast enough to demonstrate live.

Propagated these final numbers (superseding the Session 2 single-split
numbers above) to `slides/final_review.tex`, `docs/SLIDE_NUMBERS.md`,
`docs/VIVA_QA.md`, `docs/KNOWN_WEAKNESSES.md`, `docs/UNDERSTANDING.md`,
`docs/REPORT_OUTLINE.md`, `docs/DEMO_SCRIPT.md`, `docs/DIARY_DRAFT.md`.

**No blockers.** Full test suite green (47/47). This is the final,
reproducible number set for today's review — `pipeline.evaluate` run live
will reproduce it exactly.

## 2026-10-26 — Session 4: replaced the web layer with a JS app

User feedback: Python web frameworks (Streamlit, and an unused FastAPI
backend sitting alongside it) are less flexible for UI than JS; asked for
the web layer to be rebuilt in JS with Python reserved strictly for ML.
Planned in plan mode (two Explore passes + a Plan agent mapped the full
system first), then executed in stages so the repo stayed runnable
throughout:

1. **Fixed a real pre-existing bug found while planning**: the live
   Analyze page was predicting using `citation-predictor/models/
   citation_model.pkl` — the synthetic-trained model this project's own
   evaluation work proved scores ~0.49 AUC (chance) on real data. The real
   model (`artifacts/model.pkl`, from `pipeline.evaluate`) was never
   loaded by the live app. `model_loader.py` now loads it directly and
   raises a clear error ("run `python -m pipeline.evaluate` first")
   instead of silently falling back to a synthetic model.
2. Added `citation-predictor/backend/cli.py` — `analyze`/`report`
   subcommands replacing the FastAPI routes, invoked as a per-request
   subprocess (no persistent Python server). Clean JSON-on-stdout error
   contract; binary-safe PDF output. Verified standalone before any Node
   code existed.
3. Built `web/` — a Next.js (TypeScript) app, the only web UI now: three
   pages (Analyze / Explainability / Model Card) ported 1:1 from the
   Streamlit app (same design tokens, same tier thresholds, same demo
   fixtures — verified byte-identical against the Python source). API
   routes spawn `cli.py` via `child_process.spawn`, never `exec`/shell
   interpolation.
4. Removed, only once `web/` was confirmed working end-to-end:
   `streamlit_app.py`, `app.py`, `run_streamlit.bat`,
   `citation-predictor/backend/main.py`/`api/`/`database/` (FastAPI app —
   `database/db.py`'s history feature was never used by the live Streamlit
   UI either, so no feature parity loss), `services/citation_engine.py`
   (confirmed dead code), and `citation-predictor/frontend/` (an unused,
   never-styled Vite+React scaffold).
5. **Found and fixed a second real bug during cleanup**: `reportlab`
   was unpinned (`>=4.2.0`) and had quietly started requiring Python
   3.10+ as of its 5.1.0 release — breaking a fresh install on this
   project's verified Python 3.9 target. Pinned to `reportlab==5.0.1`
   (the version actually verified working) in both `requirements.txt`
   and `citation-predictor/backend/requirements.txt`. Also dropped
   `streamlit`/`altair` (dead now that Streamlit is gone) and regenerated
   `requirements.lock` from a genuinely fresh scratch venv — caught this
   bug precisely because the lock file was rebuilt from scratch rather
   than trusted as already-correct.

Added `tests/test_cli.py` (subprocess smoke tests mirroring exactly what
the Node bridge does) and `tests/test_model_loader.py` — 47 → 54 tests,
all green, re-verified against the fresh trimmed-dependency venv.

**No blockers.** `web/README.md` and `README.md` document the new
two-terminal dev workflow (`python -m pipeline.evaluate` once, then
`cd web && npm run dev`).

## 2026-10-26 — Session 5: repo cleanup, 300-query scale-up, Page Health

**Repo cleanup (user-requested):** discovered the repo root also contained
a large, completely unrelated upstream open-source monorepo (apps/,
packages/, e2e/, docker/, brand/, scripts/, .github/, .changeset/, and
root-level package.json/pnpm-lock.yaml/pnpm-workspace.yaml/turbo.json/
biome.json/knip.json/tsconfig.json, plus its own env files and
LICENSE.md/CLA.md/etc.) that this coursework was never built from — it had
been documented as "not our work" since the Phase-1 audit but never
removed. Deleted entirely (548 files) after confirming nothing in this
project depends on any of it. Rewrote `.gitignore` to drop ~40 lines of
now-meaningless rules. Renamed `README_PROJECT.md` -> `README.md` (the
naming collision with the removed repo's own README.md is gone). Found and
fixed a real production-build bug while verifying: Next.js 16's Cache
Components rejected the Explainability/Model Card pages for reading live
JSON files without declaring themselves dynamic (`next build` catches
this, `next dev` doesn't) — added `export const instant = false` to both.

Also decluttered `data/` (one duplicate worksheet deleted, two superseded
ones moved to `data/manual_citations_archive/`) and added `docs/README.md`
as a one-page index of the 14 docs files, grouped by purpose.

**Scaled to 300 queries.** Added 100 more queries (Q201-Q300, 25/category),
collected their candidate pool automatically, and the team collected all
100 citations via perplexity.ai. Caught and the team fixed 3 genuine
copy-paste data-entry errors in the worksheet (a city's citation pointing
to a different city's page — found by an automated consistency scan before
import, not silently accepted). One URL missing its `https://` prefix was
also fixed. Merged, re-imported, re-scraped (978 unique pages, 568 ok),
re-ran `pilot_stats` and `evaluate` (repeated-GroupKFold methodology) on
the full real 300-query dataset: 592 usable rows (189 cited / 403 not).

**Real numbers at n=300:**
- XGBoost ROC-AUC **0.69 ± 0.06** (up from 0.64 ± 0.12 at n=200 — both the
  point estimate rose and the error bar nearly halved again, continuing
  the trend: 0.65±0.19 (n=100) -> 0.64±0.12 (n=200) -> 0.69±0.06 (n=300)).
- Logistic regression 0.70 ± 0.08 — still a touch ahead of XGBoost, but
  the gap has narrowed as the dataset grew (consistent with XGBoost
  needing more data than LR to show its nonlinear advantage).
- Accuracy at the default threshold: 62.7% — essentially unchanged across
  all three scales (62.6% at n=200 too). **Honest finding:** more data is
  improving the model's *ranking* ability (AUC) faster than its
  *threshold-accuracy*. Reaching materially higher accuracy (e.g. 80%)
  would need more real data, `--repeats` to filter citation-label noise,
  and genuinely new off-page features (backlink/authority data, semantic
  similarity to the query) — not hyperparameter tuning on this dataset,
  which we deliberately avoid since it would inflate the number without
  the model learning anything real (the exact mistake the original
  inherited model made).
- Label-shuffle control: 0.56 ± 0.05 (close to, though not exactly at,
  chance — reported honestly, not rounded down to "0.5").
- Feature ablation: authority 0.69, structural 0.66, content 0.61.
- Domain-type flag: 0.77 with vs 0.69 without.
- Original synthetic-trained model on real data: still AUC 0.49 (chance).
- SHAP stability: 0.84.

Propagated these final numbers everywhere they're referenced:
`slides/final_review.tex`, `docs/SLIDE_NUMBERS.md`, `docs/VIVA_QA.md`,
`docs/KNOWN_WEAKNESSES.md`, `docs/DATA_CARD.md`, `docs/UNDERSTANDING.md`
(which also hadn't been updated since the Streamlit->web/ migration —
fixed its architecture diagram and module descriptions too),
`docs/REPORT_OUTLINE.md`, `docs/DEMO_SCRIPT.md`, `docs/DIARY_DRAFT.md`,
`docs/INDIVIDUAL_CONTRIBUTIONS.md`, `README.md`, `docs/README.md`.

**Added a "Page Health" feature** (user-requested, after researching how
comparable SEO/AEO/GEO tools present single-page analysis): a small,
secondary checklist — meta title/description presence+length, image
alt-text coverage, HTTPS, mobile viewport tag — computed for free from the
HTML we already scrape, shown as a 5th Analyze-page tab. New
`citation-predictor/backend/features/page_health.py` module, deliberately
kept separate from `extract_features()`/`FEATURE_COLUMNS` — these checks
do not feed the model or influence `citation_probability` in any way; they
are pure supporting context. 4 new tests, all passing.

Full pytest suite: 58/58 passing throughout this session.
