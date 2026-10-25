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

export interface Metrics {
  generated_at?: string;
  underpowered?: boolean;
  roc_auc_display?: string;
  f1_display?: string;
  accuracy_display?: string;
  precision_recall_display?: string;
  models?: Record<string, unknown>;
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
