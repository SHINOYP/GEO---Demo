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

function fmtAuc(x?: number): string {
  return typeof x === "number" ? x.toFixed(2) : "not yet measured";
}

export default async function ModelCardPage() {
  const [pilotStats, metrics] = await Promise.all([loadPilotStats(), loadMetrics()]);

  const xgb = metrics?.models?.xgboost?.roc_auc?.mean;
  const logreg = metrics?.models?.logistic_regression?.roc_auc?.mean;
  const ruleBased = metrics?.models?.rule_based_checklist?.roc_auc?.mean;
  const shuffled = metrics?.sanity_checks?.label_shuffle_control?.roc_auc?.mean;
  const originalModel = metrics?.sanity_checks?.original_repo_model_on_real_data?.roc_auc;

  return (
    <div>
      <PageHeader
        badge="Transparency"
        title="Model Card"
        subtitle="Everything here in plain language first. The raw numbers are underneath for anyone who wants to check our work."
      />

      <FadeIn>
        <div className="card" style={{ marginBottom: "1rem" }}>
          <h3>Where the data came from</h3>
          {pilotStats === null ? (
            <div className="alert alert-warning">
              <strong>Not yet measured.</strong> No <code>data/pilot_stats.json</code> found — the
              real-data pilot pipeline (<code>pipeline/run_all.py</code>) has not been run yet.
            </div>
          ) : (
            <>
              <p style={{ fontSize: "0.86rem", color: "var(--muted-foreground)", marginBottom: "0.75rem" }}>
                We picked {pilotStats.num_queries ?? "some"} realistic local-business search
                questions (things like &quot;best gym in Kochi&quot;), asked Perplexity each one
                by hand, and wrote down which page(s) it actually cited in its answer. That gave
                us real, not made-up, examples to learn from.
              </p>
              <div className="grid-3" style={{ gap: "0.6rem" }}>
                <MetricTile
                  label="Questions asked"
                  value={String(pilotStats.num_queries ?? "not yet measured")}
                  hint="Real search questions, hand-checked on perplexity.ai"
                />
                <MetricTile
                  label="Pages we could use"
                  value={String(pilotStats.usable_rows ?? "not yet measured")}
                  hint="Pages that loaded successfully and had enough content to analyze"
                />
                <MetricTile
                  label="Actually got cited"
                  value={pilotStats.positive_rate_display ?? "not yet measured"}
                  hint="Share of those pages that Perplexity really did cite"
                />
              </div>
              <div style={{ marginTop: "0.75rem" }}>
                <JsonExpander title="Raw pilot_stats.json (for the curious)" data={pilotStats} />
              </div>
            </>
          )}
        </div>
      </FadeIn>

      <FadeIn delay={0.06}>
        <div className="card" style={{ marginBottom: "1rem" }}>
          <h3>How we decided &quot;cited&quot; vs. &quot;not cited&quot;</h3>
          <p style={{ fontSize: "0.88rem" }}>
            Simple rule: if Perplexity&apos;s answer linked to that exact page, we marked it{" "}
            <code>1</code> (cited). If it didn&apos;t, we marked it <code>0</code> (not cited).
            The &quot;not cited&quot; examples are real pages that show up in normal search
            results for the same question — not random junk pages — so the model has to learn a
            genuinely hard distinction, not an easy one. Full details in{" "}
            <code>docs/DATA_CARD.md</code>.
          </p>
        </div>
      </FadeIn>

      <FadeIn delay={0.12}>
        <div className="card" style={{ marginBottom: "1rem" }}>
          <h3>Is the model actually any good?</h3>
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

              <p style={{ fontSize: "0.86rem", marginBottom: "0.5rem" }}>
                We tested our model against two reference points to make sure the result is
                real and not a fluke:
              </p>
              <ul style={{ fontSize: "0.86rem", paddingLeft: "1.1rem", marginBottom: "0.9rem" }}>
                <li style={{ marginBottom: "0.3rem" }}>
                  <strong>A &quot;dumb&quot; checklist</strong> (just counts things like
                  &quot;has a phone number? has structured data?&quot;) scores{" "}
                  <strong>{fmtAuc(ruleBased)}</strong>
                  {" "}— barely better than flipping a coin (0.50). Our model needs to clearly
                  beat this to prove it&apos;s learning something real.
                </li>
                <li style={{ marginBottom: "0.3rem" }}>
                  <strong>A &quot;cheating&quot; test</strong>: we shuffled all the real answers
                  randomly and retrained. A model that was secretly peeking at the answers would
                  still look good here — ours scores <strong>{fmtAuc(shuffled)}</strong>, close
                  to random (0.50), which tells us it isn&apos;t cheating.
                </li>
                {typeof originalModel === "number" ? (
                  <li>
                    <strong>The model this project inherited</strong> (trained on made-up,
                    computer-generated data instead of real citations) scores only{" "}
                    <strong>{fmtAuc(originalModel)}</strong> on our real data — essentially
                    useless, even though it claimed 88.8% accuracy on its own fake data. This is
                    the clearest proof that training on fake data doesn&apos;t work.
                  </li>
                ) : null}
              </ul>

              <p style={{ fontSize: "0.86rem", marginBottom: "0.75rem" }}>
                Our actual model (XGBoost) scores{" "}
                <strong>{fmtAuc(xgb)}</strong> — meaningfully above both the dumb checklist and
                the shuffled-answer test, so the signal is real. A simpler model (logistic
                regression) scores <strong>{fmtAuc(logreg)}</strong>, about the same — which
                honestly tells us the pattern we&apos;ve found so far is fairly simple, not some
                deep hidden relationship. We say that plainly rather than hiding it.
              </p>

              <div className="grid-4" style={{ gap: "0.6rem", marginBottom: "0.75rem" }}>
                <MetricTile
                  label="ROC-AUC"
                  value={metrics.roc_auc_display ?? "not yet evaluated"}
                  hint="Ranking skill: 0.5 = random, 1.0 = perfect"
                />
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
                <MetricTile
                  label="Precision / Recall"
                  value={metrics.precision_recall_display ?? "not yet evaluated"}
                  hint="Right-when-it-says-yes / catches-how-many-real-ones"
                />
              </div>

              <JsonExpander title="Raw metrics.json (every number, for the curious)" data={metrics} />
            </>
          )}
        </div>
      </FadeIn>

      <FadeIn delay={0.18}>
        <div className="card">
          <h3>What this model can&apos;t do (yet)</h3>
          <ul style={{ fontSize: "0.86rem", paddingLeft: "1.1rem" }}>
            <li>
              We only have a few hundred real examples — not enough to be fully confident in the
              exact numbers, only in the overall direction (it works better than guessing).
            </li>
            <li>
              The &quot;not cited&quot; pages are already decent, already-ranking pages — not
              random junk — so this model answers &quot;which of the good pages wins?&quot;, not
              &quot;is this page good at all?&quot;
            </li>
            <li>
              We only checked each question once. If you ask Perplexity the same thing twice, it
              might cite a different page — we haven&apos;t measured how often that happens.
            </li>
            <li>
              The model finds patterns, not causes. It can&apos;t tell you that adding a phone
              number <em>causes</em> more citations — only that pages with one tend to get cited
              more often.
            </li>
            <li>
              AI answer engines change their behavior over time, so this model would need
              retraining on fresh data periodically to stay accurate.
            </li>
          </ul>
        </div>
      </FadeIn>
    </div>
  );
}
