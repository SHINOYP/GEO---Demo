"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ShapDriver } from "@/lib/types";

const POSITIVE_COLOR = "#10B981";
const NEGATIVE_COLOR = "#EF4444";

export default function ShapBarChart({
  topPositive,
  topNegative,
}: {
  topPositive: ShapDriver[];
  topNegative: ShapDriver[];
}) {
  const data = [...topPositive, ...topNegative]
    .map((d) => ({
      feature: d.feature.replace(/_/g, " "),
      shapImpact: d.shap_value,
      measuredValue: d.value,
      type: d.shap_value > 0 ? "Positive (Boosts Citation)" : "Negative (Hampers Citation)",
    }))
    .sort((a, b) => b.shapImpact - a.shapImpact);

  if (data.length === 0) return null;

  return (
    <div style={{ width: "100%", height: 340 }}>
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical" margin={{ left: 24, right: 24 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" dataKey="shapImpact" />
          <YAxis type="category" dataKey="feature" width={160} tick={{ fontSize: 12 }} />
          <Tooltip
            formatter={(value, _name, item) => [
              `${Number(value).toFixed(4)} (value: ${(item.payload as { measuredValue: unknown }).measuredValue})`,
              "SHAP impact",
            ]}
          />
          <Bar
            dataKey="shapImpact"
            radius={[0, 4, 4, 0]}
            animationDuration={1800}
            animationEasing="ease-out"
          >
            {data.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.shapImpact > 0 ? POSITIVE_COLOR : NEGATIVE_COLOR}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
