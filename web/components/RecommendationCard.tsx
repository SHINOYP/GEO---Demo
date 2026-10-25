import type { Recommendation } from "@/lib/types";

export default function RecommendationCard({ rec }: { rec: Recommendation }) {
  return (
    <div className={`rec-card rec-${rec.priority}`}>
      <div style={{ fontWeight: 600, marginBottom: "0.2rem" }}>
        [{rec.priority.toUpperCase()}] {rec.title}
      </div>
      <div className="kpi-sub" style={{ marginBottom: "0.4rem" }}>
        Category: {rec.category} • Potential Impact: {rec.impact.charAt(0).toUpperCase() + rec.impact.slice(1)}
      </div>
      <div style={{ fontSize: "0.88rem" }}>{rec.description}</div>
    </div>
  );
}
