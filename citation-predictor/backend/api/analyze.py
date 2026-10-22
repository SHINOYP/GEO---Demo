"""Main /api/analyze endpoint — full pipeline."""

import logging
from datetime import datetime, timezone

import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from scraping.scraper import scrape, ScrapingError
from features.extractor import extract_features
from models.model_loader import get_model, FEATURE_COLUMNS
from explainability.shap_explainer import explain
from services.recommendations import generate_recommendations
from services.pdf_report import generate_pdf
from database.db import save_analysis

logger = logging.getLogger("citelytics.api.analyze")
router = APIRouter()


class AnalyzeRequest(BaseModel):
    url: str


def _label(score: int) -> str:
    """Map an already-rounded 0-100 score to a human-readable prediction label."""
    if score >= 61:
        return "Likely to be cited"
    if score >= 31:
        return "Moderately likely to be cited"
    return "Less likely to be cited"


def _interpret(score: int) -> str:
    """Map an already-rounded 0-100 score to a likelihood level."""
    if score >= 81:
        return "Very High"
    if score >= 61:
        return "High"
    if score >= 31:
        return "Moderate"
    return "Low"


@router.post("/analyze")
async def analyze_url(req: AnalyzeRequest):
    url = str(req.url).strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(400, "URL must start with http:// or https://")

    # ── 1. Scrape ─────────────────────────────────────────────
    try:
        scrape_result = await run_in_threadpool(scrape, url)
    except ScrapingError as exc:
        raise HTTPException(422, str(exc))
    except Exception as exc:
        logger.error("Unexpected scrape error: %s", exc)
        raise HTTPException(500, "An unexpected error occurred while fetching the page.")

    soup = scrape_result["soup"]

    # ── 2. Extract features ────────────────────────────────────
    features = extract_features(soup, url)
    mf       = features["model_features"]

    # ── 3. Predict ────────────────────────────────────────────
    model, feat_cols = get_model()
    row  = pd.DataFrame([{col: mf.get(col, 0) for col in feat_cols}])
    prob = float(model.predict_proba(row)[0, 1])

    # ── 4. SHAP ───────────────────────────────────────────────
    try:
        shap_data = explain(model, feat_cols, mf)
    except Exception as exc:
        logger.warning("SHAP failed: %s", exc)
        shap_data = {"shap_values": {}, "top_positive": [], "top_negative": [], "base_value": 0.0}

    # ── 5. Recommendations ─────────────────────────────────────
    recs = generate_recommendations(features, shap_data)

    timestamp = datetime.now(timezone.utc).isoformat()
    score = int(round(prob * 100))

    result = {
        "url":                  url,
        "final_url":            scrape_result["final_url"],
        "timestamp":            timestamp,
        "citation_probability": round(prob, 4),
        "citation_score":       score,
        "prediction":           _label(score),
        "likelihood_level":     _interpret(score),
        "features":             features,
        "shap_data":            shap_data,
        "recommendations":      recs,
        "model_note":           "Demo model / Research prototype — trained on synthetic data.",
    }

    # ── 6. Persist ────────────────────────────────────────────
    try:
        rec_id = await save_analysis(
            url=url, timestamp=timestamp, score=prob,
            prediction=result["prediction"],
            features=features, shap_values=shap_data,
            recommendations=recs,
        )
        result["history_id"] = rec_id
    except Exception as exc:
        logger.warning("Could not save to DB: %s", exc)
        result["history_id"] = None

    return result


class ReportRequest(BaseModel):
    analysis: dict


@router.post("/report")
async def download_report(req: ReportRequest):
    pdf_bytes = generate_pdf(req.analysis)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=citelytics_report.pdf"},
    )
