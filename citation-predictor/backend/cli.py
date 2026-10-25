"""
CLI entrypoint for the ML pipeline — replaces the old FastAPI app.

Invoked by the Next.js web app (web/lib/pythonBridge.ts) as a per-request
subprocess, not a persistent server. Two subcommands:

    analyze <url> [--html-stdin]
        Scrapes (or, with --html-stdin, parses HTML piped in on stdin —
        used for the web app's local demo-fixture pages) the given URL,
        extracts features, predicts citation likelihood, computes SHAP
        explanations, and generates recommendations. Prints exactly one
        JSON document to stdout.

    report
        Reads an analysis JSON object (the exact shape `analyze` prints)
        from stdin, generates a PDF report, and writes the raw PDF bytes
        to stdout in binary mode.

Contract: on success, exit 0 with the payload (JSON text or PDF bytes) as
the ONLY thing on stdout. On failure, exit non-zero with exactly
{"error": true, "kind": "scraping"|"validation"|"internal", "message": "..."}
as the only thing on stdout. All logging/diagnostic output goes to stderr —
never stdout — so callers can always safely parse stdout.
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone

# Log to stderr only, configured before any other import that might log.
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger("citelytics.cli")

import pandas as pd
from bs4 import BeautifulSoup

from scraping.scraper import scrape, ScrapingError
from features.extractor import extract_features
from models.model_loader import get_model
from explainability.shap_explainer import explain
from services.recommendations import generate_recommendations
from services.pdf_report import generate_pdf


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


def _error(kind: str, message: str) -> dict:
    return {"error": True, "kind": kind, "message": message}


def cmd_analyze(args) -> int:
    url = (args.url or "").strip()
    if not url.startswith(("http://", "https://")):
        print(json.dumps(_error("validation", "URL must start with http:// or https://")))
        return 1

    if args.html_stdin:
        html = sys.stdin.read()
        soup = BeautifulSoup(html, "html.parser")
        final_url = url
    else:
        try:
            scrape_result = scrape(url)
        except ScrapingError as exc:
            print(json.dumps(_error("scraping", str(exc))))
            return 1
        except Exception as exc:
            logger.exception("Unexpected scrape error")
            print(json.dumps(_error("internal", f"An unexpected error occurred while fetching the page: {exc}")))
            return 1
        soup = scrape_result["soup"]
        final_url = scrape_result["final_url"]

    features = extract_features(soup, url)
    mf = features["model_features"]

    try:
        model, feat_cols = get_model()
    except RuntimeError as exc:
        print(json.dumps(_error("internal", str(exc))))
        return 1

    row = pd.DataFrame([{col: mf.get(col, 0) for col in feat_cols}])
    prob = float(model.predict_proba(row)[0, 1])

    shap_error = None
    try:
        shap_data = explain(model, feat_cols, mf)
    except Exception as exc:
        logger.warning("SHAP failed: %s", exc)
        shap_data = {"shap_values": {}, "top_positive": [], "top_negative": [], "base_value": 0.0}
        shap_error = str(exc)

    recommendations = generate_recommendations(features, shap_data)

    timestamp = datetime.now(timezone.utc).isoformat()
    score = int(round(prob * 100))

    result = {
        "url": url,
        "final_url": final_url,
        "timestamp": timestamp,
        "citation_probability": round(prob, 4),
        "citation_score": score,
        "prediction": _label(score),
        "likelihood_level": _interpret(score),
        "features": features,
        "shap_data": shap_data,
        "shap_error": shap_error,
        "recommendations": recommendations,
        "model_note": "Trained on real pilot data (200 queries, 390 rows) — "
                       "see artifacts/metrics.json for cross-validated metrics.",
    }
    print(json.dumps(result))
    return 0


def cmd_report(args) -> int:
    raw = sys.stdin.read()
    try:
        analysis = json.loads(raw)
    except json.JSONDecodeError:
        print(json.dumps(_error("validation", "Invalid analysis JSON on stdin")))
        return 1

    try:
        pdf_bytes = generate_pdf(analysis)
    except Exception as exc:
        logger.exception("PDF generation failed")
        print(json.dumps(_error("internal", f"Could not generate PDF: {exc}")))
        return 1

    sys.stdout.buffer.write(pdf_bytes)
    sys.stdout.buffer.flush()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="cli.py")
    sub = parser.add_subparsers(dest="command", required=True)

    analyze_parser = sub.add_parser("analyze")
    analyze_parser.add_argument("url")
    analyze_parser.add_argument("--html-stdin", action="store_true")
    analyze_parser.set_defaults(func=cmd_analyze)

    report_parser = sub.add_parser("report")
    report_parser.set_defaults(func=cmd_report)

    args = parser.parse_args()
    try:
        return args.func(args)
    except Exception as exc:
        logger.exception("Uncaught error in %s", args.command)
        print(json.dumps(_error("internal", str(exc))))
        return 1


if __name__ == "__main__":
    sys.exit(main())
