# Citelytics — single-container deploy (e.g. Render).
#
# Builds a real Python venv (ML: scraping/features/model/SHAP via
# citation-predictor/backend/cli.py) and the Next.js web app (web/) in one
# image, matching the local two-terminal dev setup exactly — no serverless
# functions, since web/lib/pythonBridge.ts spawns a real `python3` subprocess
# per request, which only works with a real persistent filesystem/venv.
#
# artifacts/model.pkl is NOT committed to git (regenerable, kept out on
# purpose — see .gitignore) so the build retrains it here from the already-
# committed, already-scraped data/dataset.csv via `pipeline.evaluate`. No
# network access or re-scraping needed at build time; fully reproducible.

FROM node:20-bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# Real venv at the exact path web/lib/paths.ts resolves by default
# (repoRoot/.venv/bin/python3) — no env var overrides needed at runtime.
RUN python3 -m venv /app/.venv \
    && /app/.venv/bin/pip install --no-cache-dir --upgrade pip \
    && /app/.venv/bin/pip install --no-cache-dir \
       -r requirements.txt -r citation-predictor/backend/requirements.txt

# Train/save artifacts/model.pkl + artifacts/metrics.json from the
# committed, already-scraped data/dataset.csv (deterministic, no network).
RUN /app/.venv/bin/python3 -m pipeline.evaluate

WORKDIR /app/web
RUN npm ci && npm run build

ENV NODE_ENV=production
EXPOSE 3000

CMD ["npm", "start"]
