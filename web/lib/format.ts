// Ported verbatim from streamlit_app.py's get_tier_name/get_label/get_tier_badge
// helpers. Note: Python's round() is round-half-to-even; Math.round() is
// round-half-up. This only matters at exact X.5% boundaries (vanishingly
// rare with real probabilities) and is not worth reconciling further.

export const TIER_HIGH_THRESHOLD = 61;
export const TIER_MED_THRESHOLD = 31;

export type Tier = "High" | "Moderate" | "Low";

export function scorePct(prob: number): number {
  return Math.round(prob * 100);
}

export function getTierName(prob: number): Tier {
  const score = scorePct(prob);
  if (score >= TIER_HIGH_THRESHOLD) return "High";
  if (score >= TIER_MED_THRESHOLD) return "Moderate";
  return "Low";
}

export function getLabel(prob: number): string {
  const tier = getTierName(prob);
  if (tier === "High") return "Likely to be Cited";
  if (tier === "Moderate") return "Moderately Likely to be Cited";
  return "Less Likely to be Cited";
}

export function tierBadgeClass(tier: Tier): string {
  if (tier === "High") return "prob-badge prob-badge-high";
  if (tier === "Moderate") return "prob-badge prob-badge-med";
  return "prob-badge prob-badge-low";
}

export function tierBadgeLabel(tier: Tier): string {
  if (tier === "High") return "High Likelihood";
  if (tier === "Moderate") return "Moderate Likelihood";
  return "Low Likelihood";
}
