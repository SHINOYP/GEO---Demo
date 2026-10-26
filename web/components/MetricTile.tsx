export default function MetricTile({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="card">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value" style={{ fontSize: "1.2rem" }}>
        {value}
      </div>
      {hint ? <div className="kpi-sub">{hint}</div> : null}
    </div>
  );
}
