import PageHeader from "@/components/PageHeader";
import MetricTile from "@/components/MetricTile";
import JsonExpander from "@/components/JsonExpander";
import FadeIn from "@/components/FadeIn";
import { loadMetrics, loadPilotStats } from "@/lib/serverData";

// Reads artifacts/metrics.json and data/pilot_stats.json from disk on every
// request (not at build time) -- these files change whenever
// `pipeline.evaluate`/`pipeline.pilot_stats` are re-run, and the page must
// always reflect their current contents, never a stale build-time snapshot.
export const instant = false;

export default async function ModelCardPage() {
  const [pilotStats, metrics] = await Promise.all([loadPilotStats(), loadMetrics()]);

  return (
    <div>
      <PageHeader badge="Transparency" title="Model Card" />

      <FadeIn>
        <div className="card" style={{ marginBottom: "1rem" }}>
          <h3>Dataset</h3>
          {pilotStats === null ? (
            <div className="alert alert-warning">
              <strong>Not yet measured.</strong> No <code>data/pilot_stats.json</code> found — the
              real-data pilot pipeline (<code>pipeline/run_all.py</code>) has not been run yet.
            </div>
          ) : (
            <>
              <div className="grid-3" style={{ gap: "0.6rem" }}>
                <MetricTile
                  label="Queries"
                  value={String(pilotStats.num_queries ?? "not yet measured")}
                />
                <MetricTile
                  label="Usable rows"
                  value={String(pilotStats.usable_rows ?? "not yet measured")}
                />
                <MetricTile
                  label="Positive rate"
                  value={pilotStats.positive_rate_display ?? "not yet measured"}
                />
              </div>
              <div style={{ marginTop: "0.75rem" }}>
                <JsonExpander title="Raw pilot_stats.json" data={pilotStats} />
              </div>
            </>
          )}
        </div>
      </FadeIn>

      <FadeIn delay={0.06}>
        <div className="card" style={{ marginBottom: "1rem" }}>
          <h3>How labels were made</h3>
          <p style={{ fontSize: "0.88rem" }}>
            A page&apos;s canonical URL is labeled <code>1</code> if cited by Perplexity&apos;s{" "}
            <code>sonar</code> model for that query, else <code>0</code>. Candidate pool = cited
            URLs ∪ organic results. See <code>docs/DATA_CARD.md</code> for the full methodology.
          </p>
        </div>
      </FadeIn>

      <FadeIn delay={0.12}>
        <div className="card" style={{ marginBottom: "1rem" }}>
          <h3>Cross-validated results (with uncertainty)</h3>
          {metrics === null ? (
            <div className="alert alert-warning">
              <strong>Not yet evaluated.</strong> Run <code>python -m pipeline.evaluate</code> to
              produce <code>artifacts/metrics.json</code>.
            </div>
          ) : (
            <>
              {metrics.underpowered ? (
                <div className="alert alert-error">
                  This dataset is flagged <strong>underpowered</strong> for strong conclusions —
                  treat all numbers below as preliminary.
                </div>
              ) : null}
              <JsonExpander title="Raw metrics.json" data={metrics} />
            </>
          )}
        </div>
      </FadeIn>

      <FadeIn delay={0.18}>
        <div className="card" style={{ marginBottom: "1rem" }}>
          <h3>Baseline comparison</h3>
          <p style={{ fontSize: "0.88rem" }}>
            See <code>artifacts/metrics.json → models.rule_based_checklist</code> for the naive
            checklist baseline that the learned models are compared against.
          </p>
        </div>

        <div className="card">
          <h3>Known limitations</h3>
          <ul style={{ fontSize: "0.86rem", paddingLeft: "1.1rem" }}>
            <li>Small sample size relative to 45 features — wide confidence intervals.</li>
            <li>Negatives are drawn from already-ranking pages, not a random web sample.</li>
            <li>Citation is non-deterministic; only one observation per query was collected.</li>
            <li>Results are correlational, not mechanistic — no causal claims.</li>
            <li>Answer-engine behavior drifts over time; the model needs periodic retraining.</li>
          </ul>
        </div>
      </FadeIn>
    </div>
  );
}
