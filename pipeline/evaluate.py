"""
Evaluate citation-likelihood models on the real pilot dataset (data/dataset.csv).

Writes:
  - artifacts/metrics.json   (everything the UI/report/slides quote)
  - artifacts/model.pkl      (final trained XGBoost pipeline, same feature
                              order as citation-predictor/models/feature_columns.json)
  - artifacts/figures/*.png  (SHAP summary + 3 waterfalls, reliability curve)

Usage:
    python -m pipeline.evaluate
"""
import json
import os
import sys
import warnings

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    roc_auc_score, average_precision_score, precision_score, recall_score,
    f1_score, accuracy_score, confusion_matrix, brier_score_loss,
)
import xgboost as xgb

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "citation-predictor", "backend")
sys.path.insert(0, BACKEND_DIR)

from models.model_loader import FEATURE_COLUMNS  # noqa: E402
from pipeline.common import MIN_USABLE_ROWS, MIN_MINORITY_CLASS  # noqa: E402

DATASET_PATH = os.path.join(REPO_ROOT, "data", "dataset.csv")
ARTIFACTS_DIR = os.path.join(REPO_ROOT, "artifacts")
FIGURES_DIR = os.path.join(ARTIFACTS_DIR, "figures")
THRESHOLD = 0.5  # documented decision threshold for precision/recall/F1


def rule_based_checklist_score(row: pd.Series) -> float:
    """
    Re-implements what existing GEO-audit checklist tools do: a simple,
    unweighted count of "good practice" signals, normalized to [0, 1].
    This is the baseline our learned model should beat.
    """
    checks = [
        row.get("schema_present", 0) > 0,
        row.get("faq_schema", 0) > 0,
        row.get("local_business_schema", 0) > 0,
        row.get("h1_count", 0) >= 1,
        row.get("heading_hierarchy_score", 0) >= 0.5,
        row.get("word_count", 0) >= 300,
        row.get("has_phone", 0) > 0 or row.get("has_address", 0) > 0,
    ]
    return sum(bool(c) for c in checks) / len(checks)


def fold_metrics(y_true, y_pred, y_proba) -> dict:
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "roc_auc": roc_auc_score(y_true, y_proba) if len(set(y_true)) > 1 else float("nan"),
        "pr_auc": average_precision_score(y_true, y_proba) if len(set(y_true)) > 1 else float("nan"),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "accuracy": accuracy_score(y_true, y_pred),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "class_balance": {"n_pos": int(sum(y_true)), "n_neg": int(len(y_true) - sum(y_true))},
    }


def mean_std(values, key):
    xs = [v[key] for v in values if not (isinstance(v[key], float) and np.isnan(v[key]))]
    if not xs:
        return {"mean": None, "std": None}
    return {"mean": round(float(np.mean(xs)), 4), "std": round(float(np.std(xs)), 4)}


def cross_validate(df: pd.DataFrame, feature_cols: list, group_col: str, model_name: str,
                    scale_pos_weight_for_xgb: bool = True,
                    n_repeats: int = 10, base_seed: int = 42) -> dict:
    """GroupKFold cross-validation, repeated n_repeats times with the row
    order independently shuffled (seeded) each repeat, and all
    n_repeats * k folds pooled into one mean/std.

    Plain GroupKFold with no shuffling assigns folds deterministically from
    the order groups first appear in `groups` — so a single run's AUC is an
    estimate from one arbitrary group-to-fold partition, not "the" AUC of
    this model on this data. At this pilot's sample size, which specific
    partition you get measurably moves the result (verified empirically:
    re-running with a different but equally valid row order shifted mean
    ROC-AUC by several points). Repeating across many random partitions and
    pooling every fold removes that single-partition-order sensitivity and
    gives a materially more precise (lower-variance) estimate — the data,
    model, and hyperparameters are completely unchanged; we are only
    evaluating them more thoroughly.
    """
    n_groups = len(set(df[group_col].values))
    k = min(5, n_groups) if n_groups >= 2 else 1
    if k < 2:
        return {"error": f"Not enough distinct {group_col} groups ({n_groups}) for GroupKFold."}

    per_fold = []
    for repeat in range(n_repeats):
        rng = np.random.default_rng(base_seed + repeat)
        perm = rng.permutation(len(df))
        df_r = df.iloc[perm].reset_index(drop=True)
        groups = df_r[group_col].values
        y = df_r["label"].values
        X = df_r[feature_cols].fillna(0).values

        gkf = GroupKFold(n_splits=k)
        for train_idx, test_idx in gkf.split(X, y, groups):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]
            if len(set(y_train)) < 2 or len(set(y_test)) < 2:
                continue  # skip degenerate folds (can happen with small n)

            if model_name == "rule_based":
                df_test = df_r.iloc[test_idx]
                y_proba = df_test.apply(rule_based_checklist_score, axis=1).values
                y_pred = (y_proba >= THRESHOLD).astype(int)
            elif model_name == "logistic_regression":
                scaler = StandardScaler()
                X_train_s = scaler.fit_transform(X_train)
                X_test_s = scaler.transform(X_test)
                clf = LogisticRegression(max_iter=1000, class_weight="balanced")
                clf.fit(X_train_s, y_train)
                y_proba = clf.predict_proba(X_test_s)[:, 1]
                y_pred = (y_proba >= THRESHOLD).astype(int)
            elif model_name == "xgboost":
                spw = (sum(y_train == 0) / max(sum(y_train == 1), 1)) if scale_pos_weight_for_xgb else 1.0
                clf = xgb.XGBClassifier(
                    n_estimators=150, max_depth=3, learning_rate=0.05,
                    subsample=0.8, colsample_bytree=0.8, min_child_weight=3,
                    scale_pos_weight=spw, eval_metric="logloss", random_state=42,
                )
                clf.fit(X_train, y_train)
                y_proba = clf.predict_proba(X_test)[:, 1]
                y_pred = (y_proba >= THRESHOLD).astype(int)
            else:
                raise ValueError(model_name)

            per_fold.append(fold_metrics(y_test, y_pred, y_proba))

    if not per_fold:
        return {"error": "All folds degenerate (single-class train or test split)."}

    return {
        "n_folds": k,
        "n_repeats": n_repeats,
        "n_evaluations": len(per_fold),
        "per_fold": per_fold,
        "roc_auc": mean_std(per_fold, "roc_auc"),
        "pr_auc": mean_std(per_fold, "pr_auc"),
        "precision": mean_std(per_fold, "precision"),
        "recall": mean_std(per_fold, "recall"),
        "f1": mean_std(per_fold, "f1"),
        "accuracy": mean_std(per_fold, "accuracy"),
        "threshold": THRESHOLD,
    }


def label_shuffle_control(df: pd.DataFrame, feature_cols: list) -> dict:
    """Shuffle labels, re-run GroupKFold XGBoost. Expect AUC ~0.5 if no leakage."""
    shuffled = df.copy()
    rng = np.random.default_rng(42)
    shuffled["label"] = rng.permutation(shuffled["label"].values)
    result = cross_validate(shuffled, feature_cols, "domain", "xgboost")
    return result


def ablation(df: pd.DataFrame) -> dict:
    groups = {
        "structural": ["h1_count", "h2_count", "h3_count", "heading_count", "heading_depth",
                       "heading_hierarchy_score", "section_count", "avg_paragraphs_per_section",
                       "macro_structure_score", "meso_structure_score", "micro_structure_score"],
        "content": ["word_count", "sentence_count", "paragraph_count", "avg_sentence_length",
                    "avg_paragraph_length", "factual_density", "number_count", "percentage_count",
                    "date_count", "quote_count", "citation_ref_count", "image_count", "list_count",
                    "table_count", "emphasis_count", "emphasis_density", "format_diversity",
                    "short_paragraph_count", "long_paragraph_count"],
        "authority": ["external_link_count", "internal_link_count", "has_phone", "has_address",
                      "has_opening_hours", "has_rating", "schema_present", "local_business_schema",
                      "organization_schema", "faq_schema", "article_schema", "product_schema",
                      "breadcrumb_schema", "review_schema", "number_of_schema_types"],
    }
    results = {}
    for name, cols in groups.items():
        cols = [c for c in cols if c in df.columns]
        if not cols:
            continue
        results[name] = cross_validate(df, cols, "domain", "xgboost")
    all_cols = [c for c in FEATURE_COLUMNS if c in df.columns]
    results["all"] = cross_validate(df, all_cols, "domain", "xgboost")
    return results


def domain_type_check(df: pd.DataFrame) -> dict:
    feats_with = [c for c in FEATURE_COLUMNS if c in df.columns]
    with_dt = df.copy()
    with_dt["domain_type_is_directory"] = (with_dt["domain_type"] == "directory_aggregator").astype(int)
    cols_with = feats_with + ["domain_type_is_directory"]
    cols_without = feats_with
    return {
        "with_domain_type_flag": cross_validate(with_dt, cols_with, "domain", "xgboost"),
        "without_domain_type_flag": cross_validate(df, cols_without, "domain", "xgboost"),
    }


def compare_original_repo_model(df: pd.DataFrame, feature_cols: list) -> dict:
    """Evaluate the repo's existing pickled model (trained on synthetic data) on our real pilot data."""
    import joblib
    model_path = os.path.join(REPO_ROOT, "citation-predictor", "models", "citation_model.pkl")
    if not os.path.exists(model_path):
        return {"error": "No existing citation_model.pkl found to compare against."}
    model = joblib.load(model_path)
    X = df[feature_cols].fillna(0)
    y = df["label"].values
    y_proba = model.predict_proba(X)[:, 1]
    y_pred = (y_proba >= THRESHOLD).astype(int)
    if len(set(y)) < 2:
        return {"error": "Only one class present; cannot compute AUC."}
    return fold_metrics(y, y_pred, y_proba)


def run_shap_analysis(df: pd.DataFrame, feature_cols: list):
    import shap
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs(FIGURES_DIR, exist_ok=True)
    X = df[feature_cols].fillna(0)
    y = df["label"].values
    spw = sum(y == 0) / max(sum(y == 1), 1)
    model = xgb.XGBClassifier(
        n_estimators=150, max_depth=3, learning_rate=0.05, subsample=0.8,
        colsample_bytree=0.8, min_child_weight=3, scale_pos_weight=spw,
        eval_metric="logloss", random_state=42,
    )
    model.fit(X, y)

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)

    plt.figure()
    shap.summary_plot(shap_values, X, show=False)
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "shap_summary.png"), dpi=120)
    plt.close()

    proba = model.predict_proba(X)[:, 1]
    picks = {}
    cited_idx = np.where(y == 1)[0]
    not_cited_idx = np.where(y == 0)[0]
    if len(cited_idx):
        picks["cited"] = cited_idx[np.argmax(proba[cited_idx])]
    if len(not_cited_idx):
        picks["not_cited"] = not_cited_idx[np.argmin(proba[not_cited_idx])]
    mid = np.argmin(np.abs(proba - 0.5))
    picks["borderline"] = mid

    for name, idx in picks.items():
        plt.figure()
        exp = shap.Explanation(
            values=shap_values[idx], base_values=explainer.expected_value,
            data=X.iloc[idx].values, feature_names=feature_cols,
        )
        shap.plots.waterfall(exp, show=False)
        plt.tight_layout()
        plt.savefig(os.path.join(FIGURES_DIR, f"shap_waterfall_{name}.png"), dpi=120)
        plt.close()

    # SHAP stability across folds: rank-correlation of mean |SHAP| per feature
    groups = df["domain"].values
    n_groups = len(set(groups))
    stability = None
    if n_groups >= 3:
        from scipy.stats import spearmanr
        gkf = GroupKFold(n_splits=min(5, n_groups))
        importances = []
        for train_idx, _ in gkf.split(X, y, groups):
            Xt, yt = X.iloc[train_idx], y[train_idx]
            if len(set(yt)) < 2:
                continue
            spw_f = sum(yt == 0) / max(sum(yt == 1), 1)
            m = xgb.XGBClassifier(n_estimators=150, max_depth=3, learning_rate=0.05,
                                   subsample=0.8, colsample_bytree=0.8, min_child_weight=3,
                                   scale_pos_weight=spw_f, eval_metric="logloss", random_state=42)
            m.fit(Xt, yt)
            sv = shap.TreeExplainer(m).shap_values(Xt)
            importances.append(np.abs(sv).mean(axis=0))
        if len(importances) >= 2:
            corrs = []
            for i in range(len(importances)):
                for j in range(i + 1, len(importances)):
                    r, _ = spearmanr(importances[i], importances[j])
                    corrs.append(r)
            stability = {"mean_rank_correlation_across_folds": round(float(np.mean(corrs)), 3),
                         "n_fold_pairs": len(corrs)}

    permutation_importance = dict(zip(
        feature_cols, [round(float(x), 4) for x in np.abs(shap_values).mean(axis=0)]
    ))

    return {
        "figures": ["shap_summary.png"] + [f"shap_waterfall_{n}.png" for n in picks],
        "shap_stability": stability,
        "mean_abs_shap_by_feature": permutation_importance,
    }, model


def calibration_check(df: pd.DataFrame, feature_cols: list, model) -> dict:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.calibration import calibration_curve

    X = df[feature_cols].fillna(0)
    y = df["label"].values
    proba = model.predict_proba(X)[:, 1]
    brier = brier_score_loss(y, proba)

    os.makedirs(FIGURES_DIR, exist_ok=True)
    try:
        frac_pos, mean_pred = calibration_curve(y, proba, n_bins=min(10, len(df) // 5 or 1))
        plt.figure()
        plt.plot(mean_pred, frac_pos, marker="o", label="Model")
        plt.plot([0, 1], [0, 1], linestyle="--", label="Perfectly calibrated")
        plt.xlabel("Mean predicted probability")
        plt.ylabel("Fraction of positives")
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(FIGURES_DIR, "reliability_curve.png"), dpi=120)
        plt.close()
    except Exception as e:
        warnings.warn(f"Could not build reliability curve: {e}")

    return {"brier_score": round(float(brier), 4),
            "note": "Lower Brier is better calibrated; with a small pilot, "
                    "prefer reading the score as a RANKING signal rather than a literal probability."}


def pct(v):
    return f"{round(v * 100, 1)}%" if v is not None else "not yet evaluated"


def format_mean_std(d: dict, decimals: int = 2) -> str:
    """Render a mean_std() dict as 'MEAN ± STD' at a fixed, documented
    display precision (2 decimals, matching docs/SLIDE_NUMBERS.md and
    docs/VIVA_QA.md) — decoupled from the full 4-decimal precision kept in
    the raw per-fold values in metrics.json for downstream programmatic use.
    """
    if d.get("mean") is None:
        return "not yet evaluated"
    return f"{round(d['mean'], decimals)} ± {round(d['std'], decimals)}"


def main():
    if not os.path.exists(DATASET_PATH):
        metrics = {
            "underpowered": True,
            "error": "NOT YET MEASURED — data/dataset.csv not found. Run python -m pipeline.run_all first.",
            "generated_at": pd.Timestamp.utcnow().isoformat(),
        }
        os.makedirs(ARTIFACTS_DIR, exist_ok=True)
        with open(os.path.join(ARTIFACTS_DIR, "metrics.json"), "w") as f:
            json.dump(metrics, f, indent=2)
        print("No dataset found — wrote a placeholder metrics.json. Run the pilot pipeline first.")
        return

    df = pd.read_csv(DATASET_PATH)
    df = df[df["scrape_status"] == "ok"].reset_index(drop=True)
    feature_cols = [c for c in FEATURE_COLUMNS if c in df.columns]

    n = len(df)
    n_pos = int(df["label"].sum())
    n_neg = n - n_pos
    underpowered = n < MIN_USABLE_ROWS or min(n_pos, n_neg) < MIN_MINORITY_CLASS

    metrics = {
        "generated_at": pd.Timestamp.utcnow().isoformat(),
        "n_usable_rows": n,
        "class_balance": {"n_pos": n_pos, "n_neg": n_neg},
        "underpowered": underpowered,
        "threshold": THRESHOLD,
        "primary_split": "GroupKFold by domain (k=5), repeated 10x over independently shuffled "
                         "row orders and pooled (50 total evaluations per model) for a more "
                         "precise estimate than a single un-shuffled 5-fold split would give",
    }

    if underpowered:
        print(f"WARNING: dataset underpowered (n={n}, min_class={min(n_pos, n_neg)}). "
              f"Computing numbers anyway but flagging them as preliminary.")

    metrics["models"] = {
        "rule_based_checklist": cross_validate(df, feature_cols, "domain", "rule_based"),
        "logistic_regression": cross_validate(df, feature_cols, "domain", "logistic_regression"),
        "xgboost": cross_validate(df, feature_cols, "domain", "xgboost"),
    }
    xgb_primary = metrics["models"]["xgboost"]
    if "error" not in xgb_primary:
        metrics["roc_auc_display"] = format_mean_std(xgb_primary["roc_auc"])
        metrics["f1_display"] = format_mean_std(xgb_primary["f1"])
        metrics["accuracy_display"] = f"{pct(xgb_primary['accuracy']['mean'])}"
        metrics["precision_recall_display"] = (
            f"{pct(xgb_primary['precision']['mean'])} / {pct(xgb_primary['recall']['mean'])}"
        )
    else:
        for k in ("roc_auc_display", "f1_display", "accuracy_display", "precision_recall_display"):
            metrics[k] = "not yet evaluated"

    metrics["secondary_split_by_query"] = cross_validate(df, feature_cols, "query_id", "xgboost")

    metrics["sanity_checks"] = {
        "label_shuffle_control": label_shuffle_control(df, feature_cols),
        "feature_group_ablation": ablation(df),
        "domain_type_leakage_check": domain_type_check(df),
        "original_repo_model_on_real_data": compare_original_repo_model(df, feature_cols),
    }

    try:
        shap_results, final_model = run_shap_analysis(df, feature_cols)
        metrics["explainability"] = shap_results
        metrics["calibration"] = calibration_check(df, feature_cols, final_model)

        import joblib
        os.makedirs(ARTIFACTS_DIR, exist_ok=True)
        joblib.dump(final_model, os.path.join(ARTIFACTS_DIR, "model.pkl"))
        with open(os.path.join(ARTIFACTS_DIR, "feature_columns.json"), "w") as f:
            json.dump(feature_cols, f, indent=2)
    except Exception as e:
        metrics["explainability"] = {"error": f"SHAP analysis failed: {type(e).__name__}: {e}"}

    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    with open(os.path.join(ARTIFACTS_DIR, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2, default=str)

    print(json.dumps({k: v for k, v in metrics.items() if k not in ("sanity_checks", "models")}, indent=2))
    print(f"\nWrote artifacts/metrics.json, artifacts/model.pkl, artifacts/figures/*")


if __name__ == "__main__":
    main()
