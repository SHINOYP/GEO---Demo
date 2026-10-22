# Citelytics

**AI Citation Intelligence — Citation Likelihood Prediction in Generative Answer Engines**

> A research prototype using XGBoost + SHAP to predict and explain whether a webpage is likely to be cited by generative AI answer engines.

---

## Research Problem

Traditional SEO tools optimise for search-engine rankings. Modern AI answer engines (ChatGPT-style systems) directly answer user queries and cite only a small number of sources. This project addresses the research gap:

> *"How likely is a webpage to be cited by a generative AI answer engine, and why?"*

## Architecture

```
  Webpage URL
      ↓
  Scraping (requests + BeautifulSoup)
      ↓
  Feature Extraction (45+ features)
  ├── Content Features (macro/meso/micro)
  ├── Structural Features (headings, sections)
  ├── Schema Detection (JSON-LD / Microdata)
  └── Local Business Signals
      ↓
  XGBoost Binary Classifier
      ↓
  Citation Probability (0–1)
      ↓
  SHAP TreeExplainer → Feature Impact
      ↓
  Recommendation Engine
      ↓
  Dashboard + PDF Report
```

## Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | React, Vite, Tailwind CSS, Recharts, Framer Motion |
| Backend | Python 3.10+, FastAPI, uvicorn |
| Scraping | requests, BeautifulSoup4, lxml |
| ML | XGBoost, scikit-learn, SHAP, pandas, numpy |
| Database | SQLite (aiosqlite) |
| Reports | ReportLab |

## Project Structure

```
citation-predictor/
├── frontend/          # React + Vite UI
│   └── src/
│       ├── pages/     # HomePage, AnalyzePage, DashboardPage, HistoryPage, AboutPage
│       └── components/
├── backend/
│   ├── main.py        # FastAPI app entry point
│   ├── api/           # Route handlers
│   ├── scraping/      # SSRF-safe scraper
│   ├── features/      # Feature extraction pipeline
│   ├── models/        # Model loader (XGBoost)
│   ├── explainability/# SHAP explainer
│   ├── services/      # Recommendations, PDF report
│   └── database/      # SQLite (aiosqlite)
├── ml/
│   ├── data/          # webpage_features.csv (generated)
│   └── training/      # train.py (standalone)
├── models/            # citation_model.pkl, feature_columns.json
└── reports/           # generated PDFs
```

## Installation

### Prerequisites

- Python 3.10+
- Node.js 18+
- pip

### Backend Setup

```bash
cd citation-predictor/backend
pip install -r requirements.txt
```

### Frontend Setup

```bash
cd citation-predictor/frontend
npm install
```

## Running Locally

### Start Backend

```bash
cd citation-predictor/backend
uvicorn main:app --reload --port 8000
```

The backend auto-trains a demo model on first startup if no saved model is found.

### Start Frontend

```bash
cd citation-predictor/frontend
npm run dev
```

Open: http://localhost:5173

### API health check

```
GET http://localhost:8000/api/health
```

## Training the Model

```bash
cd citation-predictor
python ml/training/train.py
```

This generates `ml/data/webpage_features.csv` (synthetic demo dataset) and saves the model to `models/citation_model.pkl`.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/analyze` | Full analysis pipeline |
| POST | `/api/report` | Generate PDF report |
| GET | `/api/history` | List analysis history |
| GET | `/api/history/{id}` | Get specific history record |
| GET | `/api/health` | Service health check |

## Dataset Format

`ml/data/webpage_features.csv` columns:

| Column | Description |
|---|---|
| `word_count` | Total word count |
| `factual_density` | Estimated factual density (heuristic) |
| `schema_present` | 0/1 — schema markup detected |
| `local_business_schema` | 0/1 — LocalBusiness schema |
| `format_diversity` | 0–1 content variety score |
| `macro_structure_score` | 0–1 overall page organisation |
| `meso_structure_score` | 0–1 section-level organisation |
| `micro_structure_score` | 0–1 local content quality |
| `label` | **1** = cited, **0** = not cited |
| … | 45 total features |

## Limitations

- Demo model trained on **synthetic data** — replace with real citation observations for research
- Scraper cannot execute JavaScript (static HTML only)
- Factual density is a heuristic estimate, not a scientific measurement
- Citation score is an estimate, not a guarantee

## What to Replace for Real Research

| File | What to replace |
|---|---|
| `ml/data/webpage_features.csv` | Synthetic labels → real citation labels |
| `backend/models/model_loader.py` | `_generate_demo_data()` → real data loader |
| `backend/scraping/scraper.py` | Add JS rendering (Playwright/Selenium) if needed |

## Author

**Stephin Arnold**  
GitHub: [@stephinarnold](https://github.com/stephinarnold)  
Project: Citation Likelihood Prediction in Generative Answer Engines

## License

Research prototype — not for commercial use.
