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
#
# xgboost's PyPI wheel unconditionally pulls in nvidia-nccl-cu12 (~350MB,
# GPU-only multi-device training support) even though we only ever run CPU
# inference here. On a free-tier build that extra weight is enough to blow
# the disk/memory budget and kill the build with no clean error message.
# Install everything except xgboost normally, then install xgboost with
# --no-deps (its real runtime need, numpy, is already pulled in by pandas
# and scikit-learn above).
RUN python3 -m venv /app/.venv \
    && /app/.venv/bin/pip install --no-cache-dir --upgrade pip \
    && grep -hv '^xgboost' requirements.txt citation-predictor/backend/requirements.txt > /tmp/reqs-no-xgb.txt \
    && /app/.venv/bin/pip install --no-cache-dir -r /tmp/reqs-no-xgb.txt \
    && /app/.venv/bin/pip install --no-cache-dir --no-deps "xgboost>=2.0.0" \
    && rm -f /tmp/reqs-no-xgb.txt

# Train/save artifacts/model.pkl + artifacts/metrics.json from the
# committed, already-scraped data/dataset.csv (deterministic, no network).
RUN /app/.venv/bin/python3 -m pipeline.evaluate

WORKDIR /app/web
RUN npm ci && npm run build

ENV NODE_ENV=production
EXPOSE 3000

CMD ["npm", "start"]
