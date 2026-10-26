"use client";

import { useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import PageHeader from "@/components/PageHeader";
import KpiTile from "@/components/KpiTile";
import TierBadge from "@/components/TierBadge";
import ShapBarChart from "@/components/ShapBarChart";
import DriverList from "@/components/DriverList";
import StructureCard from "@/components/StructureCard";
import RecommendationCard from "@/components/RecommendationCard";
import PageHealthPanel from "@/components/PageHealthPanel";
import CrawlerView from "@/components/CrawlerView";
import FixtureBanner from "@/components/FixtureBanner";
import ShapErrorBanner from "@/components/ShapErrorBanner";
import { DEFAULT_URL, SAMPLE_HTML_FIXTURES, SAMPLE_PRESETS } from "@/lib/fixtures";
import { getTierName, scorePct } from "@/lib/format";
import { isErrorPayload, type AnalysisResult } from "@/lib/types";

type Tab = "shap" | "structure" | "recommendations" | "page-health" | "crawler-view" | "export";

const TABS: { id: Tab; label: string }[] = [
  { id: "shap", label: "Why this score" },
  { id: "structure", label: "Structure" },
  { id: "recommendations", label: "Recommendations" },
  { id: "page-health", label: "Page Health" },
  { id: "crawler-view", label: "What AI sees" },
  { id: "export", label: "Export PDF" },
];

const kpiContainerVariants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.1 } },
};

const kpiItemVariants = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.45, ease: [0.16, 1, 0.3, 1] as const } },
};

export default function AnalyzePage() {
  const [presetLabel, setPresetLabel] = useState(SAMPLE_PRESETS[0].label);
  const selectedPreset = SAMPLE_PRESETS.find((p) => p.label === presetLabel)!;
  const [url, setUrl] = useState(DEFAULT_URL);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [mockUsed, setMockUsed] = useState(false);
  const [tab, setTab] = useState<Tab>("shap");
  const [pdfDownloading, setPdfDownloading] = useState(false);
  const resultsRef = useRef<HTMLDivElement>(null);

  function handlePresetChange(label: string) {
    setPresetLabel(label);
    const preset = SAMPLE_PRESETS.find((p) => p.label === label);
    if (preset && preset.url) setUrl(preset.url);
  }

  async function handleAnalyze() {
    setLoading(true);
    setError(null);
    setResult(null);

    // Fixture mode triggers only when the typed URL exactly equals the
    // *currently selected* preset's URL — switching the dropdown back to the
    // placeholder then analyzing a leftover fixture URL does a real fetch.
    const usingFixture = Boolean(selectedPreset.url) && url === selectedPreset.url;
    const html = usingFixture ? SAMPLE_HTML_FIXTURES[url] : undefined;

    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, html }),
      });
      const body = await res.json();
      if (!res.ok || isErrorPayload(body)) {
        setError(isErrorPayload(body) ? body.message : "Could not analyze this page.");
      } else {
        setResult(body as AnalysisResult);
        setMockUsed(usingFixture);
        setTab("shap");
        // Wait two frames so the results section has actually mounted/laid
        // out before scrolling to it -- scrolling in the same tick as
        // setResult would still target the pre-update (empty) page.
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
          });
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not analyze this page.");
    } finally {
      setLoading(false);
    }
  }

  async function handleExportPdf() {
    if (!result) return;
    setPdfDownloading(true);
    try {
      const res = await fetch("/api/report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(result),
      });
      if (!res.ok) {
        const body = await res.json();
        throw new Error(isErrorPayload(body) ? body.message : "Could not generate PDF.");
      }
      const blob = await res.blob();
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `citelytics_report_${Date.now()}.pdf`;
      link.click();
      URL.revokeObjectURL(link.href);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not generate PDF.");
    } finally {
      setPdfDownloading(false);
    }
  }

  const mf = result?.features.model_features;
  const macroVal = result
    ? result.features.derived?.macro_score ?? mf?.macro_structure_score ?? 0.5
    : 0.5;
  const mesoVal = result
    ? result.features.derived?.meso_score ?? mf?.meso_structure_score ?? 0.5
    : 0.5;
  const microVal = result
    ? result.features.derived?.micro_score ?? mf?.micro_structure_score ?? 0.5
    : 0.5;

  return (
    <div>
      <PageHeader
        badge="Prediction"
        title="Analyze a webpage"
        subtitle="Estimate the likelihood an AI answer engine cites this page, with a feature-level explanation."
      />

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
          <div style={{ flex: "3 1 240px", minWidth: 0 }}>
            <label className="kpi-label" style={{ display: "block", marginBottom: "0.3rem" }}>
              Webpage URL
            </label>
            <input
              className="input"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com/page"
            />
          </div>
          <div style={{ flex: "2 1 200px", minWidth: 0 }}>
            <label className="kpi-label" style={{ display: "block", marginBottom: "0.3rem" }}>
              Try a sample page
            </label>
            <select
              className="select"
              value={presetLabel}
              onChange={(e) => handlePresetChange(e.target.value)}
            >
              {SAMPLE_PRESETS.map((p) => (
                <option key={p.label} value={p.label}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>
        </div>
        <motion.button
          className="btn btn-primary"
          style={{ marginTop: "1rem", width: "100%" }}
          onClick={handleAnalyze}
          disabled={loading || !url}
          whileHover={!loading && url ? { scale: 1.01 } : undefined}
          whileTap={!loading && url ? { scale: 0.98 } : undefined}
        >
          <AnimatePresence mode="wait" initial={false}>
            <motion.span
              key={loading ? "loading" : "idle"}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
              style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem" }}
            >
              {loading ? (
                <>
                  <motion.span
                    style={{
                      width: 12,
                      height: 12,
                      borderRadius: "50%",
                      border: "2px solid currentColor",
                      borderTopColor: "transparent",
                      display: "inline-block",
                    }}
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                  />
                  Analyzing…
                </>
              ) : (
                "Analyze"
              )}
            </motion.span>
          </AnimatePresence>
        </motion.button>
        <div className="kpi-sub" style={{ marginTop: "0.6rem" }}>
          Estimated likelihood from observed correlations, not a guarantee. See Model Card for
          details.
        </div>
      </div>

      <AnimatePresence>
        {error ? (
          <motion.div
            className="alert alert-error"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
          >
            Could not analyze this page: {error}
          </motion.div>
        ) : null}
      </AnimatePresence>

      <AnimatePresence>
        {result ? (
          <motion.div
            ref={resultsRef}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            style={{ scrollMarginTop: "1.5rem" }}
          >
            {mockUsed ? <FixtureBanner /> : null}
            <div className="kpi-sub" style={{ marginBottom: "1rem" }}>
              Estimated likelihood from observed correlations, not a guarantee.
            </div>

            <motion.div
              className="grid-4"
              style={{ marginBottom: "1rem" }}
              variants={kpiContainerVariants}
              initial="hidden"
              animate="show"
            >
              <motion.div variants={kpiItemVariants}>
                <KpiTile
                  label="Citation probability"
                  value={`${scorePct(result.citation_probability)}%`}
                  countTo={scorePct(result.citation_probability)}
                  formatCount={(n) => `${Math.round(n)}%`}
                  sub={`${scorePct(result.citation_probability) >= 50 ? "+" : ""}${
                    scorePct(result.citation_probability) - 50
                  }% vs. 50% baseline`}
                />
              </motion.div>
              <motion.div variants={kpiItemVariants}>
                <KpiTile
                  label="Citation tier"
                  value={`${getTierName(result.citation_probability)} likelihood`}
                />
              </motion.div>
              <motion.div variants={kpiItemVariants}>
                <KpiTile
                  label="Structural quality"
                  value={`${Math.round(macroVal * 100)}/100`}
                  countTo={Math.round(macroVal * 100)}
                  formatCount={(n) => `${Math.round(n)}/100`}
                />
              </motion.div>
              <motion.div variants={kpiItemVariants}>
                <KpiTile
                  label="Schema markup"
                  value={result.features.schema.schema_present ? "Active (JSON-LD)" : "Missing"}
                />
              </motion.div>
            </motion.div>

            <motion.div
              style={{ marginBottom: "1.5rem" }}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.45, duration: 0.45 }}
            >
              <strong>Verdict:</strong> <TierBadge probability={result.citation_probability} />
            </motion.div>

            <div className="tabs">
              {TABS.map((t) => (
                <button
                  key={t.id}
                  className={`tab-button${tab === t.id ? " active" : ""}`}
                  onClick={() => setTab(t.id)}
                >
                  {t.label}
                  {tab === t.id ? (
                    <motion.div
                      layoutId="tab-underline"
                      className="tab-underline"
                      transition={{ type: "spring", stiffness: 260, damping: 28 }}
                    />
                  ) : null}
                </button>
              ))}
            </div>

            <AnimatePresence mode="wait">
              <motion.div
                key={tab}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.32, ease: [0.16, 1, 0.3, 1] }}
              >
                {tab === "shap" ? (
                  <div>
                    {result.shap_error ? <ShapErrorBanner message={result.shap_error} /> : null}
                    <p style={{ fontSize: "0.88rem", color: "var(--muted-foreground)" }}>
                      Why did this page get this score? Each bar below is one thing we measured
                      about the page (like word count or whether it has a phone number). Green
                      bars pushed the score <strong>up</strong>, red bars pushed it{" "}
                      <strong>down</strong> — and the length of the bar shows how much it
                      mattered. (This technique is called SHAP.)
                    </p>
                    <ShapBarChart
                      topPositive={result.shap_data.top_positive.slice(0, 6)}
                      topNegative={result.shap_data.top_negative.slice(0, 6)}
                    />
                    <div className="grid-2" style={{ marginTop: "1rem" }}>
                      <DriverList
                        title="Positive drivers"
                        drivers={result.shap_data.top_positive.slice(0, 6)}
                        emptyMessage="No strong positive drivers detected."
                        variant="success"
                      />
                      <DriverList
                        title="Negative drivers"
                        drivers={result.shap_data.top_negative.slice(0, 6)}
                        emptyMessage="No major negative dragging factors detected."
                        variant="error"
                      />
                    </div>
                  </div>
                ) : null}

                {tab === "structure" ? (
                  <div className="grid-3">
                    <StructureCard
                      title="Macro-structure"
                      score={macroVal}
                      bullets={[
                        `Word count: ${result.features.content.word_count}`,
                        `Total headings: ${result.features.structure.heading_count}`,
                        `H1 headings: ${result.features.structure.h1_count}`,
                        `Heading hierarchy: ${result.features.structure.heading_hierarchy_score.toFixed(2)}`,
                      ]}
                    />
                    <StructureCard
                      title="Meso-structure"
                      score={mesoVal}
                      bullets={[
                        `Paragraphs: ${result.features.content.paragraph_count}`,
                        `Lists: ${result.features.content.list_count}`,
                        `Tables: ${result.features.content.table_count}`,
                        `Avg paragraph length: ${result.features.content.avg_paragraph_length.toFixed(1)} words`,
                      ]}
                    />
                    <StructureCard
                      title="Micro-structure & signals"
                      score={microVal}
                      bullets={[
                        `Factual density: ${(mf?.factual_density ?? 0).toFixed(3)}`,
                        `Numerical claims: ${result.features.content.number_count}`,
                        `Phone detected: ${result.features.local_business.has_phone ? "Yes" : "No"}`,
                        `Address detected: ${result.features.local_business.has_address ? "Yes" : "No"}`,
                      ]}
                    />
                  </div>
                ) : null}

                {tab === "recommendations" ? (
                  <div>
                    {result.recommendations.length === 0 ? (
                      <div className="alert alert-success">
                        Great job! No urgent optimization steps found.
                      </div>
                    ) : (
                      <motion.div
                        variants={kpiContainerVariants}
                        initial="hidden"
                        animate="show"
                      >
                        {result.recommendations.map((rec, i) => (
                          <motion.div key={i} variants={kpiItemVariants}>
                            <RecommendationCard rec={rec} />
                          </motion.div>
                        ))}
                      </motion.div>
                    )}
                  </div>
                ) : null}

                {tab === "page-health" ? <PageHealthPanel pageHealth={result.page_health} /> : null}

                {tab === "crawler-view" ? (
                  <CrawlerView crawlerView={result.features.crawler_view} />
                ) : null}

                {tab === "export" ? (
                  <div>
                    <motion.button
                      className="btn btn-primary"
                      onClick={handleExportPdf}
                      disabled={pdfDownloading}
                      whileHover={!pdfDownloading ? { scale: 1.02 } : undefined}
                      whileTap={!pdfDownloading ? { scale: 0.97 } : undefined}
                    >
                      {pdfDownloading ? "Generating…" : "Download PDF report"}
                    </motion.button>
                  </div>
                ) : null}
              </motion.div>
            </AnimatePresence>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
