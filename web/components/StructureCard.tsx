export default function StructureCard({
  title,
  score,
  bullets,
}: {
  title: string;
  score: number;
  bullets: string[];
}) {
  const pct = Math.round(Math.min(Math.max(score, 0), 1) * 100);
  return (
    <div className="card">
      <h3>{title}</h3>
      <div className="progress-track" style={{ marginBottom: "0.4rem" }}>
        <div className="progress-fill" style={{ width: `${pct}%` }} />
      </div>
      <div className="kpi-sub" style={{ marginBottom: "0.75rem" }}>
        Score: {pct}%
      </div>
      {bullets.map((b, i) => (
        <div key={i} style={{ fontSize: "0.86rem", marginBottom: "0.3rem" }}>
          {b}
        </div>
      ))}
    </div>
  );
}
