# AUDIT — Citelytics (Student Project Component)

Scope: this audit covers only the student's own work inside
`geo-demo` — `app.py`, `streamlit_app.py`, `run_streamlit.bat`,
`requirements.txt`, and `citation-predictor/`. The repo root
(`apps/`, `packages/`, `e2e/`, `brand/`, etc.) is the unrelated
upstream "Getcito" project (a fork of "Elmo") and is out of scope.

Every claim below is backed by a file:line citation observed directly
in this checkout (branch `final-review`). Where something could not be
verified by running code, it is marked **unverifiable** or
**NOT YET MEASURED** rather than assumed.

---

## Baseline

**Canonical entry point.** `run_streamlit.bat:6` runs
`python -m streamlit run streamlit_app.py`, so `streamlit_app.py` is
the canonical launcher, not `app.py`. A byte-for-byte `diff app.py
streamlit_app.py` in this checkout produced **no output** — the two
files are identical. `app.py` appears to be a duplicate/backup of
`streamlit_app.py`.

**Syntax check.**
```
python3 -c "import ast; ast.parse(open('app.py').read()); ast.parse(open('streamlit_app.py').read())"
```
Result: **both parse cleanly** (no syntax errors).

**Runtime check.** `python3 -c "import streamlit"` →
`ModuleNotFoundError: No module named 'streamlit'`. The repo ships a
`.venv/` directory, but it only contains `pip`/`setuptools`
(`.venv/lib/python3.9/site-packages/` has no `numpy`, `pandas`,
`sklearn`, `xgboost`, `shap`, or `streamlit`). So in this environment
`streamlit run streamlit_app.py` cannot actually be started — it would
fail at `import streamlit as st` (`streamlit_app.py:14`). This was not
forced further because the task explicitly allows for streamlit being
absent; the syntax-validity check above is the furthest this
environment lets us go. **NOT YET MEASURED**: actual runtime behavior
(whether the model trains, whether scraping/analysis works end-to-end)
— no dependencies are installed to exercise it.

**Tests.** No test files exist for the student's own code. A
repo-wide `find . -iname "*test*"` (excluding `.venv`, `node_modules`,
`apps/`, `packages/`, `e2e/`, `.git`) returned nothing under
`citation-predictor/` or at the repo root for the student's files —
only hits inside `.venv`'s third-party packages (pip/setuptools
internals), which are not the student's tests.
`python3 -m pytest -q` → `No module named pytest`. **Conclusion: there
is no automated test suite for this project at all.**

---

## File tree of our work

- `app.py` — Streamlit UI; byte-identical duplicate of `streamlit_app.py` (see Baseline). Not referenced by `run_streamlit.bat`.
- `streamlit_app.py` — The actual, launched Streamlit app: 3 pages (Analyze Webpage, Model Architecture & XAI, College Project Overview), sidebar nav, hardcoded sample URLs/HTML fixtures, calls into `citation-predictor/backend/*` modules via `sys.path` injection (`streamlit_app.py:20-30`).
- `run_streamlit.bat` — Windows launcher: `python -m streamlit run streamlit_app.py` (`run_streamlit.bat:6`).
- `requirements.txt` — Root-level pinned deps for the Streamlit Cloud deployment path (streamlit, xgboost, scikit-learn, shap, bs4, requests, lxml, pandas, numpy, altair, matplotlib, reportlab, joblib).
- `citation-predictor/README.md` — Project README; candidly documents the architecture and explicitly states the model is trained on synthetic data (`citation-predictor/README.md:160`, `:169-171`).
- `citation-predictor/backend/main.py` — FastAPI app entry point; wires up CORS, routers, and a lifespan hook that inits the DB and trains/loads the model on startup.
- `citation-predictor/backend/api/analyze.py` — `/api/analyze` and `/api/report` endpoints: scrape → extract features → predict → SHAP → recommendations → persist to SQLite.
- `citation-predictor/backend/api/health.py` — `/api/health` liveness endpoint.
- `citation-predictor/backend/api/history.py` — `/api/history` list/detail endpoints backed by SQLite.
- `citation-predictor/backend/data/citelytics.db` — Tracked SQLite DB file (analysis history), checked into git despite `citation-predictor/.gitignore:24` (`data/citelytics.db`) supposedly ignoring it — the ignore pattern doesn't match because the file lives at `backend/data/citelytics.db`, not `data/citelytics.db`.
- `citation-predictor/backend/database/db.py` — aiosqlite schema (`analysis_history` table) and `save_analysis`/init helpers.
- `citation-predictor/backend/explainability/shap_explainer.py` — Real `shap.TreeExplainer` wrapper that returns top positive/negative SHAP contributions for one prediction.
- `citation-predictor/backend/features/extractor.py` — The feature-extraction pipeline (regex + BeautifulSoup based); computes all 45 model features plus informational/derived fields.
- `citation-predictor/backend/models/model_loader.py` — Loads a pickled XGBoost pipeline if present, else generates a synthetic dataset and trains one in-process (`load_or_train_model`, `_generate_demo_data`, `_train`).
- `citation-predictor/backend/scraping/scraper.py` — `requests`-based scraper with an SSRF guard (`_check_ssrf`), timeout, size cap, and header spoofing.
- `citation-predictor/backend/services/citation_engine.py` — A **mock** citation-labeling engine (`MockCitationEngine`) with a `RealCitationEngine` stub that raises `NotImplementedError`; not wired into the actual prediction pipeline, only an abstraction for future ground-truth collection.
- `citation-predictor/backend/services/pdf_report.py` — ReportLab-based PDF export of an analysis result.
- `citation-predictor/backend/services/recommendations.py` — Rule-based recommendation generator driven by feature thresholds (schema presence, content quality, etc.).
- `citation-predictor/ml/training/train.py` — Standalone CLI script that regenerates the synthetic dataset, retrains, and prints a classification report to stdout (not persisted anywhere).
- `citation-predictor/models/citation_model.pkl` — The committed trained XGBoost pipeline artifact (309 KB).
- `citation-predictor/models/feature_columns.json` — The 45 ordered feature-column names used by the model.
- `citation-predictor/frontend/` — A separate React + Vite single-page app (`AnalyzePage.jsx`, `DashboardPage.jsx`, `HistoryPage.jsx`, `HomePage.jsx`, `AboutPage.jsx`) that talks to the FastAPI backend; this is the "dual-deployment" UI referenced in the Streamlit "College Project Overview" page.
- `citation-predictor/*.bat` (`start_all.bat`, `start_backend.bat`, `start_frontend.bat`, `push_to_github.bat`) — Windows convenience launchers/scripts.

---

## Numbered questions

### 1. Training data and labels — real or synthetic? Is the AUC circular?

`load_or_train_model()` (`citation-predictor/backend/models/model_loader.py:183-196`) only loads a pickle if one exists on disk; otherwise it calls `_generate_demo_data()` (`model_loader.py:59-139`), which:

- Draws every one of the 45 feature columns from `numpy` random distributions (`rng.integers`/`rng.uniform`, lines 68-114) — **no real webpage is ever scraped to build this dataset.**
- Computes the binary label as a **hand-written linear weighted sum of those same feature columns** plus Gaussian noise (`model_loader.py:117-132`): e.g. `factual_density*8 + schema_present*2 + format_diversity*2 + heading_hierarchy_score*2 + macro_structure_score*2 + ... + rng.normal(0,0.5,n_samples)`, then thresholds at the median (`model_loader.py:133-134`).
- The module's own docstring admits this (`model_loader.py:5-9`: "generates a synthetic demo dataset... THIS IS NOT REAL CITATION DATA" repeated at line 64).

**This means the label is a deterministic (plus noise) function of the exact same features the XGBoost model is trained and evaluated on.** Any reported accuracy/F1/ROC-AUC from this pipeline is measuring how well XGBoost can re-derive a linear formula from its own inputs, not whether the features predict real-world LLM citation behavior. **The AUC/F1/accuracy figures are circular and have no evidentiary value about actual citation prediction.**

There is also `citation-predictor/backend/services/citation_engine.py`, a `MockCitationEngine` (lines 17-33) that returns a hash-based pseudo-label and a `RealCitationEngine` stub that `raise NotImplementedError` (lines 36-57) — confirming no real LLM-citation ground truth has ever been collected, and this engine isn't even wired into `model_loader.py`'s training path.

### 2. Hard-coded UI numbers — reproducible?

Found in both `app.py` and `streamlit_app.py` (identical, lines 502-509):
```
streamlit_app.py:502   m_c1.metric("ROC-AUC Score", "0.888", "+0.388 vs random")
streamlit_app.py:503   m_c2.metric("Classification F1", "0.784", "Balanced")
streamlit_app.py:506   m_c3.metric("Test Accuracy", "79.0%", "Evaluation set")
streamlit_app.py:507   m_c4.metric("Precision / Recall", "80.8% / 76.0%")
streamlit_app.py:509   st.subheader("4. Extracted Feature Dimensions (45 Total)")
```
and "45+ features" language at `streamlit_app.py:277`, `:494`, `:534`, and `citation-predictor/README.md:22`.

A repo-wide search (`grep -rn "0.888\|0.784"`) finds these numbers **only** in `app.py`/`streamlit_app.py` — nowhere else in the repo (no log file, no notebook, no saved metrics JSON, no CI artifact). `citation-predictor/ml/training/train.py:48-52` does print a classification report and ROC-AUC to stdout when run, but that output is never captured/persisted anywhere in the repo, and no `.log`/`.ipynb` files exist anywhere (`find . -iname "*.log" -o -iname "*.ipynb"` returned nothing outside `.venv`/`node_modules`). This environment also cannot install `numpy`/`xgboost`/`sklearn` to re-run `train.py` and check whether 0.888 is even reproducible from the fixed `random_state=42` seeds.

**Verdict: unverifiable.** These four metrics are presented in the UI as "Model Validation & Benchmark Metrics" (`streamlit_app.py:500`) with no accompanying script output, log, or artifact in the repo that reproduces them — and per finding #1, even if they were reproduced exactly, they would be circular, not meaningful validation.

### 3. Every feature the extractor computes

All computed in `citation-predictor/backend/features/extractor.py`; the 45 columns fed to the model are enumerated at `model_loader.py:39-56` / built in `extractor.py:353-404`.

| Feature | Type | Computation | Group | Leakage / proxy risk |
|---|---|---|---|---|
| `word_count` | int | `len(text.split())` (`extractor.py:162,186`) | Content | Low |
| `sentence_count` | int | regex sentence split, filtered to >2 words (`extractor.py:160-161,187`) | Content | Low |
| `paragraph_count` | int | count of non-empty `<p>` tags (`extractor.py:159,188`) | Content | Low |
| `avg_sentence_length` | float | mean words/sentence (`extractor.py:166-167`) | Content | Low |
| `avg_paragraph_length` | float | mean words/paragraph (`extractor.py:164-165`) | Content | Low |
| `factual_density` | float 0-1 | heuristic weighted sum of numbers/%/dates/citation-refs/ext-links/quotes ÷ word count, capped at 1 (`extractor.py:255-272`); docstring: "NOT a scientifically validated measure" | Content (derived) | High — same signals are directly re-used as label-construction weights in `model_loader.py:118` (`factual_density*8` is the single biggest weight in the synthetic label formula), so this one feature alone is almost entirely responsible for the label it's trained to predict |
| `number_count` | int | regex `\b\d+...\b` matches (`extractor.py:24,169,191`) | Content | Medium — directly weighted into synthetic label |
| `percentage_count` | int | regex `%` matches (`extractor.py:25,170`) | Content | Medium |
| `date_count` | int | regex date patterns (`extractor.py:34-38,171`) | Content | Low |
| `quote_count` | int | regex quoted-string pattern (`extractor.py:49,172`) | Content | Low |
| `citation_ref_count` | int | regex `[1]`/`[Smith, 2020]`/"ibid"/"et al." patterns (`extractor.py:50-53,173`) | Content | Medium — directly weighted into label |
| `external_link_count` | int | `<a href="http...">` count (`extractor.py:175,196`) | Content/Authority-proxy | Medium — external link count is also a classic domain-authority / backlink-style SEO proxy, not a page-quality signal |
| `internal_link_count` | int | `<a>` not matching `http`/`//` (`extractor.py:176,197`) | Content | Low |
| `image_count` | int | `<img>` count (`extractor.py:177,198`) | Content | Low |
| `list_count` | int | `<ul>`/`<ol>` count (`extractor.py:178,199`) | Content | Low |
| `table_count` | int | `<table>` count (`extractor.py:179,200`) | Content | Low |
| `emphasis_count` | int | `<strong>/<b>/<em>/<i>/<mark>` count (`extractor.py:180,201`) | Content | Low |
| `emphasis_density` | float | `emphasis_count / word_count`, capped at 1 (`extractor.py:291-293`) | Content (derived) | Low |
| `format_diversity` | float 0-1 | fraction of 7 binary "has this content type" signals present (`extractor.py:275-288`) | Content (derived) | Medium — directly weighted into label |
| `short_paragraph_count` | int | paragraphs <40 words (`extractor.py:182,202`) | Content | Low |
| `long_paragraph_count` | int | paragraphs ≥100 words (`extractor.py:183,203`) | Content | Medium — directly weighted (negatively) into label |
| `h1_count`/`h2_count`/`h3_count`/`h4_count` | int | heading tag counts (`extractor.py:212-217,239-242`) | Structural | Low |
| `heading_count` | int | sum of h1-h6 counts (`extractor.py:219,243`) | Structural | Low |
| `heading_depth` | int | number of distinct heading levels present (`extractor.py:220-223,244`) | Structural | Low |
| `heading_hierarchy_score` | float | hand-tuned formula: `h1_ok*0.5 + h2_ok*0.3 + h3_present*0.2` (`extractor.py:227-229,245`) | Structural (derived) | Medium — directly weighted into label |
| `section_count` | int | `max(h2_count, 1)` (`extractor.py:232,246`) | Structural | Low |
| `avg_paragraphs_per_section` | float | paragraphs ÷ section_count (`extractor.py:236,247`) | Structural | Low |
| `schema_present` | 0/1 | any JSON-LD/microdata `@type` found (`extractor.py:90`) | Schema | Medium — directly weighted into label |
| `local_business_schema`, `organization_schema`, `faq_schema`, `article_schema`, `product_schema`, `breadcrumb_schema`, `review_schema` | 0/1 each | keyword match against detected `@type` values (`extractor.py:91-99`) | Schema | Medium (`local_business_schema`, `faq_schema` are directly weighted into label at `model_loader.py:127-128`) |
| `number_of_schema_types` | int | count of distinct schema types (`extractor.py:100`) | Schema | Low |
| `has_phone`, `has_address`, `has_opening_hours`, `has_rating` | 0/1 each | regex detection on page text (`extractor.py:124-150`) | Authority-proxy (local business) | Low-Medium — these proxy "is this a real registered local business with contact info," not whether content is accurate/citable |
| `macro_structure_score` | float 0-1 | weighted mix of h1 presence, h2 ratio, section ratio, word-count ratio, heading-hierarchy score (`extractor.py:296-305`) | Structural (derived) | High — directly weighted into label at `model_loader.py:122`, and is itself built from other features already in the model (double-counting) |
| `meso_structure_score` | float 0-1 | weighted mix of paragraphs/section, list/table bonuses, h3 bonus (`extractor.py:308-315`) | Structural (derived) | Medium — same double-counting issue, also weighted into label |
| `micro_structure_score` | float 0-1 | weighted mix of 1-short_paragraph_ratio, number density, emphasis density, sentence-length-closeness-to-18-words (`extractor.py:318-325`) | Structural (derived) | Medium — same double-counting issue, also weighted into label |

**General leakage note:** several "derived" scores (`factual_density`, `format_diversity`, `macro/meso/micro_structure_score`, `heading_hierarchy_score`) are (a) built purely from other raw features already in the same feature set, and (b) are the *exact* terms used to hand-construct the synthetic label in `model_loader.py:117-132`. This is the core circularity problem described in Q1 — it is not just that labels are synthetic, but that the label formula and the feature set share the same handful of heavily-weighted terms.

### 4. Claim vs evidence table

| Claim (UI/README) | Evidence | Status |
|---|---|---|
| SSRF protection | `citation-predictor/backend/scraping/scraper.py:51-82` blocks localhost/private ranges/cloud metadata IP and resolves DNS before fetching. **Gap:** `requests.get(..., allow_redirects=True)` (`scraper.py:96-102`) performs its own independent DNS resolution on any redirect target without re-running `_check_ssrf`, so a redirect to a private IP would bypass the guard (classic SSRF-via-redirect / TOCTOU-DNS-rebind gap). | Partial |
| FastAPI backend | `citation-predictor/backend/main.py` defines a real FastAPI app with lifespan, CORS, and 3 routers (`main.py:37-60`); `api/analyze.py`, `api/health.py`, `api/history.py` implement real endpoints. | Present |
| React frontend | `citation-predictor/frontend/src/` contains a real Vite+React app with 5 pages (`App.jsx`, `pages/*.jsx`) calling the backend. Not run/tested in this audit (no `npm install` performed). | Present (untested) |
| SHAP TreeExplainer | `citation-predictor/backend/explainability/shap_explainer.py:26` calls `shap.TreeExplainer(model)` for real, used from both `api/analyze.py:77` and `streamlit_app.py:288`. | Present |
| PDF report | `citation-predictor/backend/services/pdf_report.py` (185 lines, ReportLab) generates a PDF; wired into `/api/report` (`analyze.py:121-128`) and the Streamlit "Export Official PDF Report" tab (`streamlit_app.py:459-472`). | Present |
| CSV/JSON export | No CSV/JSON export of *analysis results* found anywhere in `app.py`, `streamlit_app.py`, or the FastAPI/React code (`grep` for csv/json/export/download across those files only turns up the PDF download button and the internal `to_csv` call in `model_loader.py:137`, which writes the *synthetic training dataset* to disk, not a user-facing export). History data is only exposed via the SQLite-backed `/api/history` JSON API (`api/history.py`), not a downloadable file. | Absent (for user-facing CSV/JSON report export) |
| Competitor comparison | No occurrence of "competitor" anywhere under `citation-predictor/`, `app.py`, or `streamlit_app.py`. The only "competitor" references in the whole checkout are in the unrelated root `README.md` (Getcito/Elmo upstream project, e.g. `README.md:80`), not the student's work. | Absent |

### 5. Mock/synthetic fallbacks (exact quotes)

- `streamlit_app.py:152` comment header: `# Mock Fallbacks for testing demo pages`, followed by `SAMPLE_PRESETS` (`streamlit_app.py:153-159`) and `SAMPLE_HTML_FIXTURES` (`streamlit_app.py:161-206`) — fully hand-written fake HTML for "Apex Dental Clinic" and a "Handyman" site.
- `streamlit_app.py:262-275`:
  ```python
  try:
      if target_url in SAMPLE_HTML_FIXTURES:
          from bs4 import BeautifulSoup
          soup = BeautifulSoup(SAMPLE_HTML_FIXTURES[target_url], "html.parser")
          mock_used = True
      else:
          scrape_res = scrape(target_url)
          soup = scrape_res["soup"]
  except Exception as e:
      # Fallback to sample if external scrape is blocked
      from bs4 import BeautifulSoup
      st.warning(f"Live web fetch blocked or unavailable ({str(e)[:60]}...). Using synthetic benchmark scraper for evaluation.")
      soup = BeautifulSoup(SAMPLE_HTML_FIXTURES.get("https://sample-dental-clinic.example.com"), "html.parser")
      mock_used = True
  ```
  **Any** scrape failure for **any** arbitrary user-entered URL silently substitutes the hardcoded "Apex Dental Clinic" fixture and still produces a confident citation-probability score, with only a small transient warning banner — the dashboard that follows gives no further indication the result is for a fake dental clinic page rather than the user's real URL.
- `citation-predictor/backend/services/citation_engine.py:17-33` — `MockCitationEngine.get_citation_label()` returns `1 if hash(url + query) % 100 < 45 else 0`, explicitly documented as `"NOT connected to any real AI system"` (line 23).
- `citation-predictor/backend/models/model_loader.py:59-139` — `_generate_demo_data()`, the only data source `load_or_train_model()` ever uses when no pickle exists, is 100% `numpy` random generation (see Q1).

### 6. Security/robustness

| Control | Evidence | Status |
|---|---|---|
| URL scheme validation | `scraper.py:55-56` rejects non-http(s) schemes; `api/analyze.py:52-53` requires `http://`/`https://` prefix | Present |
| SSRF blocklist (hosts/ranges) | `scraper.py:21-35,51-82` — localhost/loopback/RFC1918/link-local/metadata IP blocked, DNS-resolved before connecting | Present (see redirect gap in Q4) |
| Redirect-safe SSRF re-check | None found — `scraper.py:96-102` uses `allow_redirects=True` with no re-validation of the final/intermediate hosts | Absent |
| Request timeout | `scraper.py:17,99` — `TIMEOUT = 15` seconds passed to `requests.get` | Present |
| Response size cap | `scraper.py:18,113-118` — `MAX_BYTES = 5_000_000`, streamed and truncated | Present |
| Error handling (scrape) | `scraper.py:104-111` catches `Timeout`/`TooManyRedirects`/`ConnectionError`/`HTTPError` and raises a typed `ScrapingError`; `api/analyze.py:56-62` converts to HTTP 422/500 | Present |
| Error handling (SHAP/PDF) | `api/analyze.py:76-80` and `streamlit_app.py:287-290` wrap SHAP calls in try/except with a safe fallback dict; `streamlit_app.py:462-472` wraps PDF generation in try/except | Present |
| Custom User-Agent | `scraper.py:37-44` — descriptive UA string identifying the scraper | Present |
| robots.txt handling | No reference to `robots.txt`, `urllib.robotparser`, or any crawl-permission check anywhere in `citation-predictor/backend/scraping/scraper.py` or elsewhere in the repo (`grep -ri robots` over `citation-predictor` returns nothing) | Absent |
| Rate limiting / abuse protection on `/api/analyze` | No rate-limiter middleware found in `main.py` or `api/analyze.py` | Absent |

### 7. Secrets

`git ls-files | grep -i env` (run from repo root) lists:
```
.env.example
.env.local
apps/web/.env.example
apps/web/.env.local
apps/worker/.env.local
packages/config/src/env-registry.test.ts
packages/config/src/env-registry.ts
packages/config/src/env.ts
```
All of these are under the repo root / `apps/` / `packages/` — i.e. the unrelated upstream Getcito project, already noted by the requester as pre-checked, pointing at localhost with empty/placeholder values, no rotation needed.

**Under `citation-predictor/` specifically:** no `.env*` file, key, or token file is tracked. `find citation-predictor -iname "*.env*" -o -iname "*secret*" -o -iname "*key*"` returned nothing. The only "key" in that subtree is the unused `api_key` constructor parameter on the never-implemented `RealCitationEngine` stub (`citation-predictor/backend/services/citation_engine.py:53`), which holds no value in the repo. **No additional secrets found under `citation-predictor/`.**

### 8. Dead code, TODOs, unused dependencies, version conflicts

- **TODO/FIXME/XXX:** none found anywhere in `citation-predictor/`, `app.py`, or `streamlit_app.py` (`grep -rn "TODO\|FIXME\|XXX"` returned nothing).
- **Dead/unreachable code:** `app.py` is a complete, byte-identical duplicate of `streamlit_app.py` and is never invoked by `run_streamlit.bat` — effectively 26 KB of dead duplicate code sitting at the repo root.
- **Unimplemented stub shipped as "architecture":** `RealCitationEngine` (`citation-predictor/backend/services/citation_engine.py:49-63`) is dead code from the pipeline's point of view — `model_loader.py` never imports or calls anything from `citation_engine.py` at all; the whole module is unused by the actual training/inference path.
- **Tracked DB artifact:** `citation-predictor/backend/data/citelytics.db` is committed to git even though `citation-predictor/.gitignore:24` attempts to ignore `data/citelytics.db` (pattern doesn't match the actual `backend/data/` path) — a runtime-generated SQLite file with potentially prior analysis history is checked into version control.
- **requirements.txt vs actual imports:** Root `requirements.txt` lists `matplotlib>=3.8.0` and `altair>=5.0.0`; `streamlit_app.py` imports `altair as alt` (`streamlit_app.py:17`, used at line 372) but a repo-wide `grep -rn "import matplotlib"` over `app.py`/`streamlit_app.py`/`citation-predictor` found **no usage of matplotlib anywhere** — it's an unused dependency in `requirements.txt`. Root `requirements.txt` also omits `fastapi`, `uvicorn`, `pydantic`, `aiosqlite` (all needed by `citation-predictor/backend/`, listed separately in `citation-predictor/backend/requirements.txt`) — two separate, overlapping, never-reconciled requirements files (`requirements.txt` for the Streamlit path, `citation-predictor/backend/requirements.txt` for the FastAPI path).
- **Two dependency files, two Python targets:** `citation-predictor/README.md:78` says "Python 3.10+" while this machine's `.venv` was built against Python 3.9 (`.venv/lib/python3.9/...`), and neither venv nor either requirements file has actually been installed/verified end-to-end in this environment (**NOT YET MEASURED**: whether `pip install -r requirements.txt` succeeds cleanly).

---

## Ranked list — "things that would embarrass us in front of a panel"

1. **The headline ROC-AUC 0.888 / F1 0.784 / 79.0% accuracy numbers shown on the "Model Architecture & XAI" page are circular** — the synthetic label is a linear formula built directly from the same features the model is scored on (`citation-predictor/backend/models/model_loader.py:117-132` vs. `streamlit_app.py:502-507`), so these numbers measure nothing about real citation prediction and shouldn't be presented as validation metrics.
2. **No real citation ground truth exists anywhere in the project** — `citation_engine.py:17-33`'s `MockCitationEngine` is hash-based fake data, and `RealCitationEngine` (`citation_engine.py:49-63`) is an unimplemented stub that raises `NotImplementedError`; the entire "AI citation prediction" claim rests on zero observed LLM citations.
3. **Any failed scrape silently swaps in a fake "Apex Dental Clinic" page and still returns a confident score** for whatever URL the user typed, with only a brief warning toast (`streamlit_app.py:270-275`) — a panelist entering their own site could unknowingly be shown someone else's fabricated analysis.
4. **The 0.888/0.784/79.0%/80.8%/76.0% figures are unverifiable** — they appear nowhere else in the repo (no log, notebook, or saved metrics file), and this environment can't even install the ML stack to check if `train.py` reproduces them.
5. **SSRF protection has a redirect bypass** — `_check_ssrf` validates the initial host/IP but `requests.get(..., allow_redirects=True)` (`scraper.py:96-102`) never re-validates redirect targets, so a malicious URL could 302 to an internal IP.
6. **A runtime SQLite database with prior analysis history is committed to git** (`citation-predictor/backend/data/citelytics.db`) despite an `.gitignore` rule that was supposed to exclude it but doesn't match the real path.
7. **`app.py` is a dead, byte-identical duplicate** of the actually-used `streamlit_app.py`, suggesting incomplete cleanup before submission.
8. **No automated tests exist at all** for the student's code (`python3 -m pytest -q` → no module found; no test files under `citation-predictor/`), so none of the above has ever been machine-checked.
9. **No robots.txt handling and no rate limiting** on the scraper/API, despite "SSRF-safe scraper" being advertised as a security feature.
10. **"45+ features" and derived macro/meso/micro scores double-count raw features** (e.g. `macro_structure_score` is built from `h1_count`, `h2_count`, `section_count`, `word_count`, `heading_hierarchy_score` — all *also* separate model inputs) — inflates the apparent feature count and biases the synthetic-label formula toward structure, independent of question #1's labeling issue.
