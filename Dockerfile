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

# Python fully buffers stdout when it isn't attached to a terminal (always
# true inside Docker), so a long-running script like pipeline.evaluate
# would print nothing at all until it finished or crashed -- indistinguishable
# from a genuine hang in the build log. Forces line-by-line flushing instead.
# Must be set before the pipeline.evaluate RUN step below, not after it --
# ENV only affects instructions that come after it in the file.
ENV PYTHONUNBUFFERED=1

# NumPy/SciPy's BLAS backend and OpenMP (used internally by XGBoost/sklearn)
# auto-detect the HOST machine's full CPU count via os.cpu_count(), not the
# container's actual cgroup CPU quota -- a classic Docker gotcha. On a
# constrained free-tier instance this causes massive thread oversubscription
# (every library independently spinning up a thread per host core, then
# fighting over a tiny real CPU slice), which can turn a model-training step
# that takes ~70s locally into something that looks hung for 10+ minutes.
# Caps every thread pool to 1 so training is CPU-bound but predictable
# instead of oversubscribed; also applies at runtime, since
# web/lib/pythonBridge.ts spawns this same python3 as a per-request
# subprocess on an equally constrained live instance.
ENV OMP_NUM_THREADS=1
ENV OPENBLAS_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV NUMEXPR_NUM_THREADS=1

# Copy only the requirement files first so this layer -- the slowest part
# of the build -- stays cached across any change that isn't to the Python
# dependency list. With the full `COPY . .` this used to live before, any
# edit to web/ or pipeline/ source forced a complete pip reinstall on every
# build for no reason (whether this actually helps depends on Render
# retaining Docker layer cache between deploys, but it's strictly better).
COPY requirements.txt requirements.txt
COPY citation-predictor/backend/requirements.txt citation-predictor/backend/requirements.txt

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

# Now bring in the rest of the repo (app code, data/dataset.csv, web/ source).
COPY . .

# Train/save artifacts/model.pkl + artifacts/metrics.json from the
# committed, already-scraped data/dataset.csv (deterministic, no network).
RUN /app/.venv/bin/python3 -m pipeline.evaluate

WORKDIR /app/web
RUN npm ci && npm run build

ENV NODE_ENV=production
EXPOSE 3000

CMD ["npm", "start"]
