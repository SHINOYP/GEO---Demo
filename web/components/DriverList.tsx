import type { ShapDriver } from "@/lib/types";

export default function DriverList({
  title,
  drivers,
  emptyMessage,
  variant,
}: {
  title: string;
  drivers: ShapDriver[];
  emptyMessage: string;
  variant: "success" | "error";
}) {
  return (
    <div>
      <h4 style={{ fontSize: "0.95rem", fontWeight: 600, marginBottom: "0.5rem" }}>{title}</h4>
      {drivers.length === 0 ? (
        <div className="alert alert-info">{emptyMessage}</div>
      ) : (
        drivers.map((d, i) => (
          <div key={i} className={`alert alert-${variant}`} style={{ marginBottom: "0.4rem" }}>
            <strong>{d.feature}</strong> = <code>{String(d.value)}</code> (SHAP{" "}
            {d.shap_value > 0 ? "+" : ""}
            {d.shap_value.toFixed(4)})
          </div>
        ))
      )}
    </div>
  );
}
