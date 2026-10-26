"use client";

import { useMemo } from "react";
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  Handle,
  Position,
  type Node,
  type Edge,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

type PipelineNodeData = {
  icon: string;
  label: string;
  sub: string;
  accent: string;
};

function PipelineNode({ data }: NodeProps) {
  const { icon, label, sub, accent } = data as PipelineNodeData;
  return (
    <div
      style={{
        background: "var(--bg)",
        border: "1px solid var(--border)",
        borderLeft: `3px solid ${accent}`,
        borderRadius: "var(--radius)",
        padding: "0.65rem 0.85rem",
        width: 190,
        boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
      }}
    >
      <Handle type="target" position={Position.Left} style={{ opacity: 0 }} />
      <div style={{ display: "flex", alignItems: "center", gap: "0.45rem", marginBottom: "0.15rem" }}>
        <span style={{ fontSize: "1rem" }}>{icon}</span>
        <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--foreground)" }}>{label}</span>
      </div>
      <div style={{ fontSize: "0.7rem", color: "var(--muted-foreground)", lineHeight: 1.3 }}>{sub}</div>
      <Handle type="source" position={Position.Right} style={{ opacity: 0 }} />
    </div>
  );
}

const nodeTypes = { pipeline: PipelineNode };

const nodeDefs: { id: string; icon: string; label: string; sub: string; accent: string; x: number; y: number }[] = [
  { id: "browser", icon: "🌐", label: "Your browser", sub: "Types a URL, clicks Analyze", accent: "var(--accent)", x: 0, y: 160 },
  { id: "nextjs", icon: "▲", label: "Next.js web app", sub: "web/app/api/analyze/route.ts", accent: "var(--accent)", x: 230, y: 160 },
  { id: "cli", icon: "⌁", label: "cli.py subprocess", sub: "One short-lived process per request", accent: "var(--primary)", x: 460, y: 160 },
  { id: "scraper", icon: "🛡️", label: "Scraper", sub: "SSRF-safe, respects robots.txt", accent: "var(--success)", x: 690, y: 40 },
  { id: "extractor", icon: "📐", label: "Feature extractor", sub: "45 content/structure/schema signals", accent: "var(--success)", x: 920, y: 40 },
  { id: "model", icon: "🌳", label: "XGBoost model", sub: "Trained on 300 real queries", accent: "var(--primary)", x: 1150, y: 40 },
  { id: "pagehealth", icon: "✅", label: "Page Health", sub: "Meta tags, alt text, HTTPS, viewport", accent: "var(--warning)", x: 920, y: 280 },
  { id: "shap", icon: "💡", label: "SHAP explainer", sub: "Why this score, feature by feature", accent: "var(--warning)", x: 1150, y: 160 },
  { id: "response", icon: "📄", label: "JSON result", sub: "One document back to the browser", accent: "var(--accent)", x: 1380, y: 160 },
];

const edgeDefs: [string, string][] = [
  ["browser", "nextjs"],
  ["nextjs", "cli"],
  ["cli", "scraper"],
  ["scraper", "extractor"],
  ["extractor", "model"],
  ["extractor", "pagehealth"],
  ["model", "shap"],
  ["pagehealth", "shap"],
  ["shap", "response"],
];

export default function ArchitectureDiagram() {
  const nodes: Node[] = useMemo(
    () =>
      nodeDefs.map((n) => ({
        id: n.id,
        type: "pipeline",
        position: { x: n.x, y: n.y },
        data: { icon: n.icon, label: n.label, sub: n.sub, accent: n.accent },
        draggable: true,
      })),
    [],
  );

  const edges: Edge[] = useMemo(
    () =>
      edgeDefs.map(([source, target]) => ({
        id: `${source}-${target}`,
        source,
        target,
        animated: true,
        style: { stroke: "var(--border)", strokeWidth: 1.5 },
      })),
    [],
  );

  return (
    <div
      style={{
        height: 420,
        border: "1px solid var(--border)",
        borderRadius: "var(--radius)",
        overflow: "hidden",
        background: "var(--muted)",
      }}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        proOptions={{ hideAttribution: true }}
        nodesConnectable={false}
        elementsSelectable={false}
        panOnScroll
        zoomOnScroll={false}
      >
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="var(--border)" />
      </ReactFlow>
    </div>
  );
}
