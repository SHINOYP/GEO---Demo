"""
ML model loader.

On startup, tries to load a pre-trained model from models/citation_model.pkl.
If not found, generates a synthetic demo dataset and trains one.

IMPORTANT:  The demo dataset is clearly documented as synthetic.
            Replace it with real citation labels for production research.
"""

import os
import json
import logging
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score,
)
import xgboost as xgb

logger = logging.getLogger("citelytics.model")

BASE_DIR    = os.path.dirname(__file__)
MODEL_PATH  = os.path.join(BASE_DIR, "..", "..", "models", "citation_model.pkl")
COLS_PATH   = os.path.join(BASE_DIR, "..", "..", "models", "feature_columns.json")
DATA_PATH   = os.path.join(BASE_DIR, "..", "..", "ml", "data", "webpage_features.csv")

_model      = None   # XGBoost classifier (global singleton)
_feat_cols  = None   # ordered list of feature column names

# ─────────────────────────────────────────────
# Feature columns (must match extractor.py)
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


def _generate_demo_data(n_samples: int = 500) -> pd.DataFrame:
    """
    Synthetic demo dataset.
    Labels are assigned by a hand-crafted rule that approximates
    what features might predict citation likelihood.
    THIS IS NOT REAL CITATION DATA.
    """
    rng = np.random.default_rng(42)

    df = pd.DataFrame({
        "word_count":              rng.integers(100, 3000, n_samples),
        "sentence_count":          rng.integers(5, 150, n_samples),
        "paragraph_count":         rng.integers(1, 50, n_samples),
        "avg_sentence_length":     rng.uniform(8, 35, n_samples),
        "avg_paragraph_length":    rng.uniform(20, 200, n_samples),
        "factual_density":         rng.uniform(0, 0.3, n_samples),
        "number_count":            rng.integers(0, 60, n_samples),
        "percentage_count":        rng.integers(0, 15, n_samples),
        "date_count":              rng.integers(0, 10, n_samples),
        "quote_count":             rng.integers(0, 10, n_samples),
        "citation_ref_count":      rng.integers(0, 20, n_samples),
        "external_link_count":     rng.integers(0, 30, n_samples),
        "internal_link_count":     rng.integers(0, 50, n_samples),
        "image_count":             rng.integers(0, 20, n_samples),
        "list_count":              rng.integers(0, 15, n_samples),
        "table_count":             rng.integers(0, 5, n_samples),
        "emphasis_count":          rng.integers(0, 40, n_samples),
        "emphasis_density":        rng.uniform(0, 0.05, n_samples),
        "format_diversity":        rng.uniform(0, 1, n_samples),
        "short_paragraph_count":   rng.integers(0, 20, n_samples),
        "long_paragraph_count":    rng.integers(0, 10, n_samples),
        "h1_count":                rng.integers(0, 3, n_samples),
        "h2_count":                rng.integers(0, 10, n_samples),
        "h3_count":                rng.integers(0, 10, n_samples),
        "heading_count":           rng.integers(0, 20, n_samples),
        "heading_depth":           rng.integers(0, 6, n_samples),
        "heading_hierarchy_score": rng.uniform(0, 1, n_samples),
        "section_count":           rng.integers(1, 12, n_samples),
        "avg_paragraphs_per_section": rng.uniform(1, 8, n_samples),
        "schema_present":          rng.integers(0, 2, n_samples),
        "local_business_schema":   rng.integers(0, 2, n_samples),
        "organization_schema":     rng.integers(0, 2, n_samples),
        "faq_schema":              rng.integers(0, 2, n_samples),
        "article_schema":          rng.integers(0, 2, n_samples),
        "product_schema":          rng.integers(0, 2, n_samples),
        "breadcrumb_schema":       rng.integers(0, 2, n_samples),
        "review_schema":           rng.integers(0, 2, n_samples),
        "number_of_schema_types":  rng.integers(0, 5, n_samples),
        "has_phone":               rng.integers(0, 2, n_samples),
        "has_address":             rng.integers(0, 2, n_samples),
        "has_opening_hours":       rng.integers(0, 2, n_samples),
        "has_rating":              rng.integers(0, 2, n_samples),
        "macro_structure_score":   rng.uniform(0, 1, n_samples),
        "meso_structure_score":    rng.uniform(0, 1, n_samples),
        "micro_structure_score":   rng.uniform(0, 1, n_samples),
    })

    # Rule-based labels (transparent heuristic)
    score = (
          df["factual_density"] * 8
        + df["schema_present"] * 2
        + df["format_diversity"] * 2
        + df["heading_hierarchy_score"] * 2
        + df["macro_structure_score"] * 2
        + df["meso_structure_score"] * 1.5
        + df["micro_structure_score"] * 1.5
        + df["citation_ref_count"] * 0.15
        + df["external_link_count"] * 0.05
        + df["faq_schema"] * 1.5
        + df["local_business_schema"] * 1.0
        + np.log1p(df["word_count"]) * 0.3
        - df["long_paragraph_count"] * 0.2
        + rng.normal(0, 0.5, n_samples)          # noise
    )
    threshold = np.percentile(score, 50)
    df["label"] = (score > threshold).astype(int)

    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    df.to_csv(DATA_PATH, index=False)
    logger.info("Demo dataset written to %s (%d rows)", DATA_PATH, len(df))
    return df


def _train(df: pd.DataFrame) -> xgb.XGBClassifier:
    X = df[FEATURE_COLUMNS]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss",
        random_state=42,
    )
    model.fit(X_train, y_train)

    y_pred  = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy":  round(accuracy_score(y_test, y_pred), 4),
        "precision": round(precision_score(y_test, y_pred, zero_division=0), 4),
        "recall":    round(recall_score(y_test, y_pred, zero_division=0), 4),
        "f1":        round(f1_score(y_test, y_pred, zero_division=0), 4),
        "roc_auc":   round(roc_auc_score(y_test, y_proba), 4),
    }
    logger.info("Model metrics: %s", metrics)

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    with open(COLS_PATH, "w") as f:
        json.dump(FEATURE_COLUMNS, f, indent=2)

    logger.info("Model saved to %s", MODEL_PATH)
    return model


def load_or_train_model():
    global _model, _feat_cols
    if os.path.exists(MODEL_PATH) and os.path.exists(COLS_PATH):
        logger.info("Loading pre-trained model from %s", MODEL_PATH)
        _model = joblib.load(MODEL_PATH)
        with open(COLS_PATH) as f:
            _feat_cols = json.load(f)
    else:
        logger.info("No saved model found — generating demo data and training …")
        df = _generate_demo_data()
        _model = _train(df)
        _feat_cols = FEATURE_COLUMNS

    return _model


def get_model():
    global _model
    if _model is None:
        load_or_train_model()
    return _model, _feat_cols
