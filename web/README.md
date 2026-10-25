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

## Error contract with `cli.py`

Every CLI invocation prints exactly one thing to stdout: on success, the JSON
result (or raw PDF bytes for `report`); on failure, non-zero exit +
`{"error": true, "kind": "scraping"|"validation"|"internal", "message": "..."}`.
`lib/pythonBridge.ts` always parses stdout and never trusts exit code alone.
All Python logging goes to stderr.
