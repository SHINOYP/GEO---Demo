"use client";

import { useEffect, useState } from "react";
import { motion } from "motion/react";

/**
 * Animated circular gauge, 0-1 scale (e.g. ROC-AUC, where 0.5 = chance and
 * 1.0 = perfect). Purely a visual aid — the underlying number is unchanged.
 */
export default function ScoreGauge({
  value,
  label,
  sublabel,
}: {
  value: number;
  label: string;
  sublabel: string;
}) {
  const size = 140;
  const stroke = 10;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.max(0, Math.min(1, value));
  const color = clamped >= 0.7 ? "var(--success)" : clamped >= 0.55 ? "var(--warning)" : "var(--danger)";

  const [displayValue, setDisplayValue] = useState(0);
  useEffect(() => {
    const duration = 1000;
    const start = performance.now();
    let raf: number;
    function tick(now: number) {
      const t = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      setDisplayValue(clamped * eased);
      if (t < 1) raf = requestAnimationFrame(tick);
    }
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [clamped]);

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "0.5rem" }}>
      <div style={{ position: "relative", width: size, height: size }}>
        <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="var(--muted)"
            strokeWidth={stroke}
          />
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: circumference * (1 - clamped) }}
            transition={{ duration: 1, ease: "easeOut" }}
          />
        </svg>
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "1.5rem",
            fontWeight: 700,
            color: "var(--foreground)",
          }}
        >
          {displayValue.toFixed(2)}
        </div>
      </div>
      <div style={{ textAlign: "center" }}>
        <div style={{ fontSize: "0.82rem", fontWeight: 600 }}>{label}</div>
        <div className="kpi-sub">{sublabel}</div>
      </div>
    </div>
  );
}
