"""
Standalone training script for the ORIGINAL SYNTHETIC baseline model.

This regenerates citation-predictor/models/citation_model.pkl — the
synthetic-data-trained model that pipeline/evaluate.py's
compare_original_repo_model check intentionally loads as a known-bad
comparison baseline (see docs/AUDIT.md and docs/KNOWN_WEAKNESSES.md item 1).
It is NOT the model served by the live app — that's artifacts/model.pkl,
trained on real pilot data by `python -m pipeline.evaluate`
(see citation-predictor/backend/models/model_loader.py).

Run from the project root:
    python citation-predictor/ml/training/train.py

Generates ml/data/webpage_features.csv (synthetic demo dataset), trains an
XGBoost model, evaluates it, and saves:
    models/citation_model.pkl
    models/feature_columns.json

This dataset is synthetic by design — that's the point: it's the circular,
label-from-features baseline this project's evaluation work compares the
real model against.
"""

import os
import sys

# Allow imports relative to backend (for FEATURE_COLUMNS, the shared feature list).
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

import json
import numpy as np
import pandas as pd
import joblib
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, roc_auc_score,
    classification_report, confusion_matrix,
)

from models.model_loader import FEATURE_COLUMNS

BASE_DIR = os.path.dirname(__file__)
MODELS_DIR = os.path.join(BASE_DIR, "..", "..", "models")
MODEL_PATH = os.path.join(MODELS_DIR, "citation_model.pkl")
COLS_PATH = os.path.join(MODELS_DIR, "feature_columns.json")
DATA_PATH = os.path.join(BASE_DIR, "..", "data", "webpage_features.csv")


def generate_demo_data(n_samples: int = 500) -> pd.DataFrame:
    """
    Synthetic demo dataset. Labels are assigned by a hand-crafted rule that
    approximates what features might predict citation likelihood.
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

    # Rule-based labels (transparent heuristic) — this is what makes the
    # model "circular": the label is a formula of the same features it's
    # later scored on.
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
    return df


def train_model(df: pd.DataFrame) -> xgb.XGBClassifier:
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

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy":  round(accuracy_score(y_test, y_pred), 4),
        "precision": round(precision_score(y_test, y_pred, zero_division=0), 4),
        "recall":    round(recall_score(y_test, y_pred, zero_division=0), 4),
        "f1":        round(f1_score(y_test, y_pred, zero_division=0), 4),
        "roc_auc":   round(roc_auc_score(y_test, y_proba), 4),
    }
    print(f"      Metrics: {metrics}")

    os.makedirs(MODELS_DIR, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    with open(COLS_PATH, "w") as f:
        json.dump(FEATURE_COLUMNS, f, indent=2)

    return model, X_test, y_test


if __name__ == "__main__":
    print("=" * 60)
    print("Citelytics — Synthetic Baseline Training Script")
    print("(regenerates the KNOWN-BAD comparison model, not the live-served one)")
    print("=" * 60)

    print("\n[1/3] Generating synthetic demo dataset …")
    df = generate_demo_data(n_samples=500)
    print(f"      Dataset: {len(df)} rows, {len(FEATURE_COLUMNS)} features, label distribution:")
    print(f"      cited=1: {df['label'].sum()}  |  not-cited=0: {(df['label'] == 0).sum()}")

    print("\n[2/3] Training XGBoost model …")
    model, X_te, y_te = train_model(df)

    print("\n[3/3] Evaluation …")
    y_pred = model.predict(X_te)
    y_proba = model.predict_proba(X_te)[:, 1]
    print("\nClassification Report:")
    print(classification_report(y_te, y_pred, target_names=["Not Cited", "Cited"]))
    print("Confusion Matrix:")
    print(confusion_matrix(y_te, y_pred))
    print(f"ROC-AUC: {roc_auc_score(y_te, y_proba):.4f}")

    print("\nFiles saved:")
    print(f"      {MODEL_PATH}")
    print(f"      {COLS_PATH}")
    print(f"      {DATA_PATH}")
    print("\nIMPORTANT: This model is trained on SYNTHETIC data and is used only")
    print("as the known-bad comparison baseline in pipeline/evaluate.py. The")
    print("live app serves artifacts/model.pkl instead (real pilot data).")
