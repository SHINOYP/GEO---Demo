"""
ML model loader.

Loads the real, honestly-evaluated model produced by `python -m pipeline.evaluate`
(trained on the real citation pilot dataset — see artifacts/metrics.json for its
cross-validated metrics). There is no synthetic-data fallback: if the model hasn't
been trained yet, this fails loudly with instructions, rather than silently
serving a demo model trained on fabricated labels.

Note: citation-predictor/models/citation_model.pkl (the original synthetic-data-
trained model) is intentionally left untouched on disk — pipeline/evaluate.py's
compare_original_repo_model check still loads it directly as the known-bad
baseline for comparison. This module simply no longer serves it for live
predictions.
"""

import os
import logging

import joblib

logger = logging.getLogger("citelytics.model")

BASE_DIR = os.path.dirname(__file__)
REPO_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", "..", ".."))
MODEL_PATH = os.path.join(REPO_ROOT, "artifacts", "model.pkl")

_model = None       # XGBoost classifier (global singleton)
_feat_cols = None   # ordered list of feature column names

# ─────────────────────────────────────────────
# Feature columns (must match extractor.py and pipeline/evaluate.py)
# ─────────────────────────────────────────────
FEATURE_COLUMNS = [
    "word_count","sentence_count","paragraph_count",
    "avg_sentence_length","avg_paragraph_length",
    "factual_density","number_count","percentage_count",
    "date_count","quote_count","citation_ref_count",
    "external_link_count","internal_link_count",
    "image_count","list_count","table_count",
    "emphasis_count","emphasis_density","format_diversity",
    "short_paragraph_count","long_paragraph_count",
    "h1_count","h2_count","h3_count","heading_count",
    "heading_depth","heading_hierarchy_score",
    "section_count","avg_paragraphs_per_section",
    "schema_present","local_business_schema","organization_schema",
    "faq_schema","article_schema","product_schema",
    "breadcrumb_schema","review_schema","number_of_schema_types",
    "has_phone","has_address","has_opening_hours","has_rating",
    "macro_structure_score","meso_structure_score","micro_structure_score",
]


def load_model():
    """Load artifacts/model.pkl, caching it in a module-level singleton.

    Raises RuntimeError (never falls back to a synthetic model) if the real
    model hasn't been trained yet.
    """
    global _model, _feat_cols
    if _model is not None:
        return _model, _feat_cols

    if not os.path.exists(MODEL_PATH):
        raise RuntimeError(
            f"No trained model found at {MODEL_PATH}. "
            "Run `python -m pipeline.evaluate` first to train and save the model."
        )

    logger.info("Loading real pilot-trained model from %s", MODEL_PATH)
    _model = joblib.load(MODEL_PATH)
    _feat_cols = FEATURE_COLUMNS
    return _model, _feat_cols


def get_model():
    """Stable public entry point used by callers (cli.py, etc.)."""
    return load_model()
