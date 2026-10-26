import type { PageHealth } from "@/lib/types";

const STATUS_ICON: Record<string, string> = {
  pass: "✓",
  warn: "!",
  fail: "✕",
};

const STATUS_COLOR_VAR: Record<string, string> = {
  pass: "--success",
  warn: "--warning",
  fail: "--danger",
};

const STATUS_BG_VAR: Record<string, string> = {
  pass: "--success-bg",
  warn: "--warning-bg",
  fail: "--danger-bg",
};

export default function PageHealthPanel({ pageHealth }: { pageHealth: PageHealth }) {
  return (
    <div>
      <p style={{ fontSize: "0.88rem", color: "var(--muted-foreground)", marginBottom: "0.75rem" }}>
        A quick on-page health checklist — basic signals every general SEO audit tool checks
        (meta tags, image accessibility, HTTPS, mobile-friendliness). This is separate
        supporting context, not part of the citation-likelihood model or its score.
      </p>
      <div className="card" style={{ marginBottom: "1rem" }}>
        <div className="kpi-label">Checks passed</div>
        <div className="kpi-value">
          {pageHealth.passed} / {pageHealth.total}
        </div>
      </div>
      {pageHealth.checks.map((check) => (
        <div
          key={check.id}
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: "0.6rem",
            padding: "0.6rem 0.8rem",
            borderRadius: "var(--radius)",
            border: "1px solid var(--border)",
            marginBottom: "0.5rem",
            background: `var(${STATUS_BG_VAR[check.status]})`,
          }}
        >
          <span
            style={{
              color: `var(${STATUS_COLOR_VAR[check.status]})`,
              fontWeight: 700,
              lineHeight: 1.3,
            }}
          >
            {STATUS_ICON[check.status]}
          </span>
          <div>
            <div style={{ fontWeight: 600, fontSize: "0.9rem" }}>{check.label}</div>
            <div className="kpi-sub">{check.detail}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
