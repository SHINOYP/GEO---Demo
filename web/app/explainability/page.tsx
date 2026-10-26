import PageHeader from "@/components/PageHeader";
import MetricTile from "@/components/MetricTile";
import FadeIn from "@/components/FadeIn";
import { loadMetrics } from "@/lib/serverData";

// Reads artifacts/metrics.json from disk on every request (not at build
// time) -- it changes whenever `pipeline.evaluate` is re-run, and the page
// must always reflect its current contents, never a stale build-time
// snapshot.
export const instant = false;

export default async function ExplainabilityPage() {
  const metrics = await loadMetrics();

  return (
    <div>
      <PageHeader badge="How it works" title="Explainability" />

      <div className="grid-2">
        <FadeIn>
          <div className="card" style={{ marginBottom: "1rem" }}>
            <h3>SEO vs. GEO</h3>
            <p style={{ fontSize: "0.88rem", marginBottom: "0.4rem" }}>
              <strong>Traditional search (SEO)</strong> ranks pages against a query, optimizing
              for click-through from a results list.
            </p>
            <p style={{ fontSize: "0.88rem", marginBottom: "0.4rem" }}>
              <strong>Generative engines (GEO)</strong> synthesize an answer and cite a handful of
              sources — being ranked isn&apos;t enough, you have to be chosen as a citation.
            </p>
            <p style={{ fontSize: "0.88rem" }}>
              <strong>Core hypothesis:</strong> citation likelihood is predictable from a page&apos;s
              content, structure, and schema markup — independent of its organic rank.
            </p>
          </div>
          <div className="card">
            <h3>Pipeline</h3>
            <ol style={{ fontSize: "0.88rem", paddingLeft: "1.1rem" }}>
              <li>Ingestion — SSRF-safe scraper with robots.txt compliance</li>
              <li>Feature engineering — 45 features across macro/meso/micro structure</li>
              <li>Classifier — XGBoost, P(cited = 1)</li>
              <li>Explainability — SHAP, per-URL</li>
            </ol>
          </div>
        </FadeIn>

        <FadeIn delay={0.08}>
          <div className="card" style={{ marginBottom: "1rem" }}>
            <h3>Validation metrics</h3>
            {metrics === null ? (
              <div className="alert alert-warning">
                <strong>Not yet evaluated.</strong> No <code>artifacts/metrics.json</code> was
                found. Run <code>python -m pipeline.evaluate</code> to produce real, reproducible
                metrics from the pilot dataset before any number is shown here.
              </div>
            ) : (
              <>
                {metrics.underpowered ? (
                  <div className="alert alert-warning">
                    The pilot dataset is marked <strong>underpowered</strong> — these metrics are
                    reported for transparency but should not be read as strong evidence. See the
                    Model Card page.
                  </div>
                ) : null}
                <div className="grid-2" style={{ gap: "0.6rem" }}>
                  <MetricTile label="ROC-AUC" value={metrics.roc_auc_display ?? "not yet evaluated"} />
                  <MetricTile label="F1" value={metrics.f1_display ?? "not yet evaluated"} />
                  <MetricTile
                    label="Accuracy"
                    value={metrics.accuracy_display ?? "not yet evaluated"}
                  />
                  <MetricTile
                    label="Precision / Recall"
                    value={metrics.precision_recall_display ?? "not yet evaluated"}
                  />
                </div>
                <div className="kpi-sub" style={{ marginTop: "0.6rem" }}>
                  Source: artifacts/metrics.json (generated {metrics.generated_at ?? "unknown date"})
                </div>
              </>
            )}
          </div>
          <div className="card">
            <h3>Feature groups (45 total)</h3>
            <ul style={{ fontSize: "0.86rem", paddingLeft: "1.1rem" }}>
              <li>
                <strong>Macro-structure</strong> — headings, hierarchy, word count
              </li>
              <li>
                <strong>Meso-structure</strong> — paragraphs, lists, tables
              </li>
              <li>
                <strong>Micro-structure</strong> — factual density, numbers, emphasis
              </li>
              <li>
                <strong>Schema</strong> — JSON-LD types present
              </li>
              <li>
                <strong>Local authority</strong> — phone, address, hours, rating
              </li>
            </ul>
          </div>
        </FadeIn>
      </div>
    </div>
  );
}
