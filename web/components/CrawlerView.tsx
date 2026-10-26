import type { CrawlerView as CrawlerViewData } from "@/lib/types";

export default function CrawlerView({ crawlerView }: { crawlerView: CrawlerViewData }) {
  return (
    <div>
      <p style={{ fontSize: "0.88rem", color: "var(--muted-foreground)", marginBottom: "0.75rem" }}>
        An AI answer engine doesn&apos;t see colors, layout, or images — it reads text. This is
        the exact text our scraper pulled from the page (scripts, styles, and markup already
        stripped out) — the same text every one of the 45 measurements above was computed from.
        If something you care about isn&apos;t in here, it&apos;s invisible to the model too.
      </p>
      <div className="card" style={{ marginBottom: "1rem" }}>
        <div className="kpi-label">Visible word count</div>
        <div className="kpi-value">{crawlerView.word_count.toLocaleString()}</div>
      </div>
      <div
        className="card"
        style={{
          fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
          fontSize: "0.8rem",
          lineHeight: 1.6,
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          maxHeight: 420,
          overflowY: "auto",
          color: "var(--foreground)",
          background: "var(--muted)",
        }}
      >
        {crawlerView.visible_text || (
          <span style={{ color: "var(--muted-foreground)" }}>No readable text found on this page.</span>
        )}
        {crawlerView.truncated ? (
          <span style={{ color: "var(--muted-foreground)" }}>
            {"\n\n… truncated for display ("}
            {crawlerView.full_char_count.toLocaleString()} characters total)
          </span>
        ) : null}
      </div>
    </div>
  );
}
