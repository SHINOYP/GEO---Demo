"use client";

import { motion } from "motion/react";
import type { ReactNode } from "react";

export interface Step {
  icon: string;
  title: string;
  description: ReactNode;
}

export default function Stepper({ steps }: { steps: Step[] }) {
  return (
    <div>
      {steps.map((step, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3, delay: i * 0.08 }}
          style={{ display: "flex", gap: "0.85rem" }}
        >
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0 }}>
            <div
              style={{
                width: 34,
                height: 34,
                borderRadius: "50%",
                background: "var(--muted)",
                border: "1px solid var(--border)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "0.95rem",
              }}
            >
              {step.icon}
            </div>
            {i < steps.length - 1 ? (
              <div style={{ width: 2, flex: 1, background: "var(--border)", minHeight: 18 }} />
            ) : null}
          </div>
          <div style={{ paddingBottom: "1.1rem" }}>
            <div style={{ fontWeight: 600, fontSize: "0.9rem", marginBottom: "0.2rem" }}>
              {step.title}
            </div>
            <div style={{ fontSize: "0.85rem", color: "var(--muted-foreground)", lineHeight: 1.5 }}>
              {step.description}
            </div>
          </div>
        </motion.div>
      ))}
    </div>
  );
}
