"use client";

import { useState } from "react";

export default function JsonExpander({ title, data }: { title: string; data: unknown }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="card">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          padding: 0,
          font: "inherit",
          fontWeight: 600,
          fontSize: "0.9rem",
        }}
      >
        {open ? "▾" : "▸"} {title}
      </button>
      {open ? (
        <pre
          style={{
            marginTop: "0.75rem",
            fontSize: "0.75rem",
            maxHeight: 360,
            overflow: "auto",
            background: "var(--muted)",
            padding: "0.75rem",
            borderRadius: "var(--radius)",
          }}
        >
          {JSON.stringify(data, null, 2)}
        </pre>
      ) : null}
    </div>
  );
}
