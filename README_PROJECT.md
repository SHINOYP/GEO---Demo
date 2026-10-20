# Citation Likelihood Prediction in Generative Answer Engines

**CSD 415 Project Phase I — NSS College of Engineering, Group 18**
Team: Shino (76), Stephin Arnold Raj S (66), Simranjeet Kour (56)
Guide: Reshma Sudhakaran

An explainable ML approach (XGBoost + SHAP) that predicts the probability
a webpage will be cited by a generative AI answer engine (Perplexity,
ChatGPT-style search), and explains which page features raised or lowered
that probability — positioned against existing post-hoc citation trackers
and static SEO checklists.

## What is "our work" vs the upstream repo

This repository was cloned from `StephinArnold/GEO---Demo`, whose root is
itself a fork of an **unrelated open-source AI-visibility tracker called
Getcito** (itself forked from a project called Elmo), a TypeScript/pnpm
monorepo (`apps/`, `packages/`, `e2e/`, `brand/`, `turbo.json`,
`pnpm-workspace.yaml`, etc.). **That monorepo is not our work.** It is MIT
licensed; its `LICENSE.md` and copyright notices must not be touched, and
it is never built or run as part of this project.

**Our work** is everything else:

- `app.py`, `streamlit_app.py`, `run_streamlit.bat` — the Streamlit
  demo application.
- `citation-predictor/` — the backend (FastAPI), the ML model/feature
  extractor, and a separate React frontend.
- `pipeline/` — the real-data pilot collection and evaluation pipeline
  (new, built for this review).
- `docs/` — all project documentation (new).
- `tests/` — the pytest suite (new).
- `STATUS.md` — running log of what's been done.

## Python version

Developed and tested against **Python 3.9** (also compatible with 3.10+;
`citation-predictor/README.md` recommends 3.10+ for the FastAPI backend,
but the Streamlit app and pipeline run fine on 3.9). Pin your exact
interpreter version by running `python --version` after creating your
venv and recording it here once confirmed in your own environment.

## Install & run

### macOS / Linux (bash)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

### Windows (PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run streamlit_app.py
```

(`run_streamlit.bat` wraps the same command for double-click launching.)

## Running the real-data pilot pipeline

The pipeline collects real citation data from Perplexity's `sonar` API and
organic search results, builds a labeled dataset by scraping candidate
pages, and evaluates models on it. It costs money and makes external API
calls, so every step is cost-safe by default.

1. Copy `pipeline/.env.example` to `.env` at the repo root and fill in
   `PERPLEXITY_API_KEY` (required) and `SERPAPI_KEY` (optional — without
   it, the candidate pool falls back to a narrower set, see
   `docs/DATA_CARD.md`). **Never commit `.env`.**
2. Dry-run first (no API calls, just the cost estimate and plan):

   ```bash
   python -m pipeline.run_all --dry-run
   ```

3. Once you've reviewed the printed cost estimate, run for real with an
   explicit call cap:

   ```bash
   python -m pipeline.run_all --yes --max-calls 60
   ```

4. Evaluate the resulting dataset:

   ```bash
   python -m pipeline.evaluate
   ```

Re-running any step is free once responses are cached under
`data/raw/` (gitignored) — only new, uncached queries spend real API calls,
and the number of real calls made is always printed.

## Running tests

```bash
python -m pytest -q
```

Runs fully offline (no network, no API keys needed) against golden-HTML
feature fixtures, the URL/SSRF validation rules, the label-canonicalization
rule, the GroupKFold-by-domain split logic, and the app/model
feature-column match.

## How to reproduce every number

**No number should ever be hand-typed into the UI, slides, or report.**
Every number traces to one of these generated files:

| File | Produced by | Contains |
|---|---|---|
| `data/pilot_stats.json` | `python -m pipeline.pilot_stats` | dataset size, scrape success rate, class balance, citations-per-query stats |
| `artifacts/metrics.json` | `python -m pipeline.evaluate` | ROC-AUC/PR-AUC/F1/precision/recall (mean ± std, GroupKFold), baseline comparisons, sanity checks (label-shuffle, ablation, domain-type leakage check), SHAP stability, calibration |
| `artifacts/figures/*.png` | `python -m pipeline.evaluate` | SHAP summary plot, 3 SHAP waterfall examples, reliability curve |

If a number is needed before these scripts have been run with real data
(e.g. API keys not yet configured), the UI and docs must show
**"not yet evaluated" / "NOT YET MEASURED"** rather than a placeholder
figure. As of this writing, real pilot data collection has **not yet
been run** (blocked on the team providing `PERPLEXITY_API_KEY`) — see
`STATUS.md` for current status.

## Project structure (our work only)

```
app.py                     # Streamlit Cloud entrypoint (delegates to streamlit_app.py)
streamlit_app.py           # The actual Streamlit UI
run_streamlit.bat          # Windows launcher
requirements.txt           # Python deps for the Streamlit app + pipeline
pipeline/                  # Real-data collection + evaluation (see docs/DATA_CARD.md)
citation-predictor/
  backend/
    scraping/              # SSRF + robots.txt safe scraper
    features/              # Feature extraction (45 model features)
    models/                # Model loader/trainer
    explainability/        # SHAP wrapper
    services/              # Recommendations, PDF export, citation engine (mock)
    api/                   # FastAPI endpoints
  frontend/                # React + Vite UI (talks to the FastAPI backend)
  ml/training/             # Standalone training CLI
  models/                  # Committed model artifact + feature column list
docs/                      # All project documentation
tests/                     # pytest suite
STATUS.md                  # Running log
```
