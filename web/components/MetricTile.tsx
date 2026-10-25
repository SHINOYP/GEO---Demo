export default function MetricTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="card">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value" style={{ fontSize: "1.2rem" }}>
        {value}
      </div>
    </div>
  );
}
