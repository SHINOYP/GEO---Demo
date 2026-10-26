"use client";

import { useState } from "react";
import PageHeader from "@/components/PageHeader";
import KpiTile from "@/components/KpiTile";
import TierBadge from "@/components/TierBadge";
import ShapBarChart from "@/components/ShapBarChart";
import DriverList from "@/components/DriverList";
import StructureCard from "@/components/StructureCard";
import RecommendationCard from "@/components/RecommendationCard";
import PageHealthPanel from "@/components/PageHealthPanel";
import FixtureBanner from "@/components/FixtureBanner";
import ShapErrorBanner from "@/components/ShapErrorBanner";
import { DEFAULT_URL, SAMPLE_HTML_FIXTURES, SAMPLE_PRESETS } from "@/lib/fixtures";
import { getTierName, scorePct } from "@/lib/format";
import { isErrorPayload, type AnalysisResult } from "@/lib/types";

type Tab = "shap" | "structure" | "recommendations" | "page-health" | "export";

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
          <div style={{ flex: "3 1 280px" }}>
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
          <div style={{ flex: "2 1 220px" }}>
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
        <button
          className="btn btn-primary"
          style={{ marginTop: "1rem", width: "100%" }}
          onClick={handleAnalyze}
          disabled={loading || !url}
        >
          {loading ? "Analyzing…" : "Analyze"}
        </button>
        <div className="kpi-sub" style={{ marginTop: "0.6rem" }}>
          Estimated likelihood from observed correlations, not a guarantee. See Model Card for
          details.
        </div>
      </div>

      {error ? <div className="alert alert-error">Could not analyze this page: {error}</div> : null}

      {result ? (
        <div>
          {mockUsed ? <FixtureBanner /> : null}
          <div className="kpi-sub" style={{ marginBottom: "1rem" }}>
            Estimated likelihood from observed correlations, not a guarantee.
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4, 1fr)",
              gap: "0.75rem",
              marginBottom: "1rem",
            }}
          >
            <KpiTile
              label="Citation probability"
              value={`${scorePct(result.citation_probability)}%`}
              sub={`${scorePct(result.citation_probability) >= 50 ? "+" : ""}${
                scorePct(result.citation_probability) - 50
              }% vs. 50% baseline`}
            />
            <KpiTile
              label="Citation tier"
              value={`${getTierName(result.citation_probability)} likelihood`}
            />
            <KpiTile
              label="Structural quality"
              value={`${Math.round(macroVal * 100)}/100`}
            />
            <KpiTile
              label="Schema markup"
              value={result.features.schema.schema_present ? "Active (JSON-LD)" : "Missing"}
            />
          </div>

          <div style={{ marginBottom: "1.5rem" }}>
            <strong>Verdict:</strong> <TierBadge probability={result.citation_probability} />
          </div>

          <div className="tabs">
            <button
              className={`tab-button${tab === "shap" ? " active" : ""}`}
              onClick={() => setTab("shap")}
            >
              Why this score
            </button>
            <button
              className={`tab-button${tab === "structure" ? " active" : ""}`}
              onClick={() => setTab("structure")}
            >
              Structure
            </button>
            <button
              className={`tab-button${tab === "recommendations" ? " active" : ""}`}
              onClick={() => setTab("recommendations")}
            >
              Recommendations
            </button>
            <button
              className={`tab-button${tab === "page-health" ? " active" : ""}`}
              onClick={() => setTab("page-health")}
            >
              Page Health
            </button>
            <button
              className={`tab-button${tab === "export" ? " active" : ""}`}
              onClick={() => setTab("export")}
            >
              Export PDF
            </button>
          </div>

          {tab === "shap" ? (
            <div>
              {result.shap_error ? <ShapErrorBanner message={result.shap_error} /> : null}
              <p style={{ fontSize: "0.88rem", color: "var(--muted-foreground)" }}>
                Why did this page receive this score? SHAP calculates the exact marginal
                contribution of each webpage feature towards pushing the citation probability
                higher (green) or lower (red).
              </p>
              <ShapBarChart
                topPositive={result.shap_data.top_positive.slice(0, 6)}
                topNegative={result.shap_data.top_negative.slice(0, 6)}
              />
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "1.5rem",
                  marginTop: "1rem",
                }}
              >
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
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem" }}>
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
                result.recommendations.map((rec, i) => <RecommendationCard key={i} rec={rec} />)
              )}
            </div>
          ) : null}

          {tab === "page-health" ? <PageHealthPanel pageHealth={result.page_health} /> : null}

          {tab === "export" ? (
            <div>
              <button className="btn btn-primary" onClick={handleExportPdf} disabled={pdfDownloading}>
                {pdfDownloading ? "Generating…" : "Download PDF report"}
              </button>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
