# Citelytics web app

Next.js (App Router, TypeScript) UI for the citation-likelihood predictor. This
is the only web layer in the project — Python is used strictly for ML
(scraping, feature extraction, model inference, SHAP), invoked here as a
per-request subprocess via `citation-predictor/backend/cli.py`, not a
persistent server.

Own `package.json`/lockfile/`node_modules`, independent of the unrelated
upstream monorepo (`apps/`, `packages/`, `pnpm-workspace.yaml`) that happens to
share this repo root — this project is never added to that workspace.

## Running locally

Two terminals — Python for the ML model, Node for the web app.

**Terminal 1** (one-time, or whenever the model needs retraining):

```bash
cd ..                               # repo root
source .venv/bin/activate
python -m pipeline.evaluate         # produces artifacts/model.pkl + metrics.json
```

**Terminal 2:**

```bash
cd web
npm install
npm run dev                         # http://localhost:3000 (or next free port)
```

The dev server does **not** need the Python venv active in its own shell —
`lib/pythonBridge.ts` invokes the venv's Python binary directly by absolute
path (`.venv/bin/python3` on macOS/Linux, `.venv/Scripts/python.exe` on
Windows, picked automatically via `process.platform`). Override either path
if your layout differs:

```bash
# web/.env.local
CITELYTICS_REPO_ROOT=/path/to/geo-demo
CITELYTICS_PYTHON_BIN=/path/to/python3
```

## Architecture

```
Browser <--> Next.js (this app) <-- spawn --> citation-predictor/backend/cli.py
               /api/analyze                      analyze <url> [--html-stdin]
               /api/report                        report (stdin JSON -> stdout PDF)
               pages read artifacts/metrics.json,
               data/pilot_stats.json directly (fs)
```

Three pages (`app/analyze`, `app/explainability`, `app/model-card`) port the
original Streamlit app 1:1 — same design tokens (`app/globals.css`), same
tier thresholds (`lib/format.ts`), same demo-fixture HTML (`lib/fixtures.ts`).
The Analyze page also has a fifth tab, "Page Health" — a small secondary
checklist (meta tags, image alt-text, HTTPS, mobile viewport) computed from
the same scraped HTML, added after the original port. It's supporting
context only; it has no effect on `citation_probability` or the model.

## Deploying (Render, free tier)

This app needs a real, persistent server with a Python venv — it is **not**
deployable to Vercel/Netlify-style serverless functions, since
`lib/pythonBridge.ts` spawns a real `python3` subprocess (with `xgboost`,
`shap`, `pandas`, etc. installed) per request, and serverless sandboxes don't
provide that. [Render](https://render.com) supports Docker-based web services
with a real filesystem and process model, and has a genuinely free tier
(spins down after 15 min idle, ~30-60s cold start to wake — fine for a demo,
not for production traffic).

1. Push this repo to GitHub (already done if you're reading this on
   `origin/final-review`).
2. On Render: **New > Blueprint**, point it at the repo — `render.yaml` at
   the repo root already describes the service (Docker, free plan). Or
   **New > Web Service** manually and select "Docker" as the runtime; the
   root `Dockerfile` needs no configuration.
3. First build takes a few minutes: it builds a Python venv, **retrains the
   model from the already-committed `data/dataset.csv`** (via
   `pipeline.evaluate` — `artifacts/model.pkl` isn't committed to git since
   it's regenerable, so the build produces it fresh, deterministically, with
   no network access needed), then builds the Next.js app.
4. No environment variables are required — the Dockerfile puts the venv at
   the exact path `lib/paths.ts` looks for by default
   (`<repo-root>/.venv/bin/python3`).

Deploying anywhere else that supports Docker (Railway, Fly.io, a plain VM)
works the same way — just point it at the root `Dockerfile`.

## Error contract with `cli.py`

Every CLI invocation prints exactly one thing to stdout: on success, the JSON
result (or raw PDF bytes for `report`); on failure, non-zero exit +
`{"error": true, "kind": "scraping"|"validation"|"internal", "message": "..."}`.
`lib/pythonBridge.ts` always parses stdout and never trusts exit code alone.
All Python logging goes to stderr.
