import PageHeader from "@/components/PageHeader";
import MetricTile from "@/components/MetricTile";
import FadeIn from "@/components/FadeIn";
import ArchitectureDiagram from "@/components/ArchitectureDiagram";
import ScoreGauge from "@/components/ScoreGauge";
import Stepper, { type Step } from "@/components/Stepper";
import { loadMetrics } from "@/lib/serverData";

// Reads artifacts/metrics.json from disk on every request (not at build
// time) -- it changes whenever `pipeline.evaluate` is re-run, and the page
// must always reflect its current contents, never a stale build-time
// snapshot.
export const instant = false;

const FEATURE_GROUPS: { name: string; color: string; desc: string }[] = [
  { name: "Overall layout", color: "var(--accent)", desc: "headings, hierarchy, word count" },
  { name: "Section formatting", color: "var(--success)", desc: "paragraphs, lists, tables" },
  { name: "Fine detail", color: "var(--warning)", desc: "fact density, numbers, emphasis" },
  { name: "Structured data", color: "var(--primary)", desc: "schema.org tags present" },
  { name: "Local signals", color: "var(--danger)", desc: "phone, address, hours, rating" },
];

const PIPELINE_STEPS: Step[] = [
  {
    title: "We fetch the page, safely",
    description:
      "We check the URL isn't a private/internal address and respect the site's robots.txt rules before downloading anything.",
  },
  {
    title: "We measure 45 things about it",
    description:
      "Word count, headings, whether it has structured data tags, visible phone/address info, and more.",
  },
  {
    title: "A trained model scores it",
    description: (
      <>
        It&apos;s seen hundreds of real examples of pages that did and didn&apos;t get cited, and
        learned which combinations of those 45 signals tend to go with a citation. (The model
        itself is <strong>XGBoost</strong>, a common type of ML model for this kind of data.)
      </>
    ),
  },
  {
    title: "We explain the score",
    description: (
      <>
        A technique called <strong>SHAP</strong> tells us exactly which of the 45 things pushed
        this page&apos;s score up or down, and by how much — no guessing.
      </>
    ),
  },
];

export default async function ExplainabilityPage() {
  const metrics = await loadMetrics();
  const xgbAuc = metrics?.models?.xgboost?.roc_auc?.mean;

  return (
    <div>
      <PageHeader
        badge="How it works"
        title="Explainability"
        subtitle="Plain-language explanations first — the technical term is always shown too, for anyone who wants it."
      />

      <FadeIn>
        <div className="card" style={{ marginBottom: "1.5rem", padding: "0.75rem" }}>
          <h3 style={{ marginLeft: "0.5rem" }}>The whole pipeline, end to end</h3>
          <p style={{ fontSize: "0.82rem", color: "var(--muted-foreground)", margin: "0 0 0.75rem 0.5rem" }}>
            Drag to pan around — this is the real request path, not a simplified cartoon.
          </p>
          <ArchitectureDiagram />
        </div>
      </FadeIn>

      <div className="grid-2">
        <FadeIn delay={0.06}>
          <div className="card" style={{ marginBottom: "1rem" }}>
            <h3>Search vs. AI answers — what&apos;s different</h3>
            <p style={{ fontSize: "0.88rem", marginBottom: "0.4rem" }}>
              <strong>Regular search (SEO)</strong> shows a list of links and lets you pick one.
              Being #1 or #10 still gets you a click eventually.
            </p>
            <p style={{ fontSize: "0.88rem", marginBottom: "0.4rem" }}>
              <strong>AI answer engines (GEO)</strong> — like Perplexity — write one answer and
              only mention a handful of sources. Not being one of those few means zero
              visibility, even if you&apos;d have ranked well in regular search.
            </p>
            <p style={{ fontSize: "0.88rem" }}>
              <strong>Our bet:</strong> whether a page gets mentioned is predictable from things
              you can see on the page itself — not just luck.
            </p>
          </div>
          <div className="card">
            <h3>What happens when you click Analyze</h3>
            <Stepper steps={PIPELINE_STEPS} />
          </div>
        </FadeIn>

        <FadeIn delay={0.12}>
          <div className="card" style={{ marginBottom: "1rem" }}>
            <h3>How good is the model, really?</h3>
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

                {typeof xgbAuc === "number" ? (
                  <div style={{ display: "flex", justifyContent: "center", margin: "0.5rem 0 1rem" }}>
                    <ScoreGauge
                      value={xgbAuc}
                      label="ROC-AUC (ranking skill)"
                      sublabel="0.5 = random guess · 1.0 = perfect"
                    />
                  </div>
                ) : null}

                <div className="grid-2" style={{ gap: "0.6rem" }}>
                  <MetricTile
                    label="Accuracy"
                    value={metrics.accuracy_display ?? "not yet evaluated"}
                    hint="Correct guesses out of 100 pages"
                  />
                  <MetricTile
                    label="F1 score"
                    value={metrics.f1_display ?? "not yet evaluated"}
                    hint="Balances false alarms vs. missed citations"
                  />
                </div>
                <div className="kpi-sub" style={{ marginTop: "0.6rem" }}>
                  Precision / Recall: {metrics.precision_recall_display ?? "not yet evaluated"} ·
                  Source: artifacts/metrics.json (generated{" "}
                  {metrics.generated_at ?? "unknown date"})
                </div>
              </>
            )}
          </div>

          <div className="card">
            <h3>The 45 things we measure, grouped</h3>
            <p style={{ fontSize: "0.82rem", color: "var(--muted-foreground)", marginBottom: "0.75rem" }}>
              Every one of these is something you could check by eye on the page itself.
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              {FEATURE_GROUPS.map((g) => (
                <div
                  key={g.name}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.6rem",
                    padding: "0.5rem 0.65rem",
                    borderRadius: "var(--radius)",
                    background: "var(--muted)",
                  }}
                >
                  <span
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      background: g.color,
                      flexShrink: 0,
                    }}
                  />
                  <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>{g.name}</span>
                  <span style={{ fontSize: "0.8rem", color: "var(--muted-foreground)" }}>
                    — {g.desc}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </FadeIn>
      </div>
    </div>
  );
}
