import fs from "node:fs/promises";
import path from "node:path";
import { repoRoot } from "./paths";

export async function readJsonOrNull<T>(relativePath: string): Promise<T | null> {
  try {
    const raw = await fs.readFile(path.join(repoRoot(), relativePath), "utf-8");
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

interface ModelResult {
  roc_auc?: { mean?: number; std?: number };
}

export interface Metrics {
  generated_at?: string;
  underpowered?: boolean;
  n_usable_rows?: number;
  class_balance?: { n_pos?: number; n_neg?: number };
  roc_auc_display?: string;
  f1_display?: string;
  accuracy_display?: string;
  precision_recall_display?: string;
  models?: {
    xgboost?: ModelResult;
    logistic_regression?: ModelResult;
    rule_based_checklist?: ModelResult;
    [key: string]: unknown;
  };
  sanity_checks?: {
    label_shuffle_control?: ModelResult;
    original_repo_model_on_real_data?: { roc_auc?: number };
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

export interface PilotStats {
  num_queries?: number;
  usable_rows?: number;
  positive_rate_display?: string;
  [key: string]: unknown;
}

export function loadMetrics() {
  return readJsonOrNull<Metrics>("artifacts/metrics.json");
}

export function loadPilotStats() {
  return readJsonOrNull<PilotStats>("data/pilot_stats.json");
}
