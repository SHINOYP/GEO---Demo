"use client";

import { useMemo } from "react";
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  MarkerType,
  Position,
  type Node,
  type Edge,
  type NodeProps,
} from "@xyflow/react";
import {
  Globe,
  AppWindow,
  Terminal,
  ShieldCheck,
  Ruler,
  TreeDeciduous,
  CheckCircle2,
  Lightbulb,
  FileJson,
  type LucideIcon,
} from "lucide-react";
import "@xyflow/react/dist/style.css";
import { useTheme } from "@/lib/useTheme";

type PipelineNodeData = {
  icon: LucideIcon;
  label: string;
  sub: string;
  accent: string;
};

function PipelineNode({ data }: NodeProps) {
  const { icon: Icon, label, sub, accent } = data as PipelineNodeData;
  return (
    <div
      style={{
        background: "var(--bg)",
        border: "1px solid var(--border)",
        borderRadius: 12,
        padding: "0.75rem 0.9rem",
        width: 200,
        boxShadow: "0 1px 2px rgba(0,0,0,0.04), 0 4px 10px rgba(0,0,0,0.03)",
        display: "flex",
        gap: "0.6rem",
        alignItems: "flex-start",
      }}
    >
      <Handle type="target" position={Position.Left} style={{ opacity: 0 }} />
      <div
        style={{
          width: 32,
          height: 32,
          borderRadius: 9,
          background: `color-mix(in srgb, ${accent} 14%, var(--bg))`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
        }}
      >
        <Icon size={17} color={accent} strokeWidth={2.2} />
      </div>
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--foreground)", lineHeight: 1.25 }}>
          {label}
        </div>
        <div style={{ fontSize: "0.68rem", color: "var(--muted-foreground)", lineHeight: 1.35, marginTop: 2 }}>
          {sub}
        </div>
      </div>
      <Handle type="source" position={Position.Right} style={{ opacity: 0 }} />
    </div>
  );
}

const nodeTypes = { pipeline: PipelineNode };

const WEB_COLOR = "#2563eb";
const ML_COLOR = "#16a34a";
const EXPLAIN_COLOR = "#b45309";

const nodeDefs: {
  id: string;
  icon: LucideIcon;
  label: string;
  sub: string;
  accent: string;
  x: number;
  y: number;
}[] = [
  { id: "browser", icon: Globe, label: "Your browser", sub: "Types a URL, clicks Analyze", accent: WEB_COLOR, x: 0, y: 190 },
  { id: "nextjs", icon: AppWindow, label: "Next.js web app", sub: "web/app/api/analyze/route.ts", accent: WEB_COLOR, x: 250, y: 190 },
  { id: "cli", icon: Terminal, label: "cli.py subprocess", sub: "One short-lived process per request", accent: WEB_COLOR, x: 500, y: 190 },
  { id: "scraper", icon: ShieldCheck, label: "Scraper", sub: "SSRF-safe, respects robots.txt", accent: ML_COLOR, x: 750, y: 190 },
  { id: "extractor", icon: Ruler, label: "Feature extractor", sub: "45 content/structure/schema signals", accent: ML_COLOR, x: 1000, y: 190 },
  { id: "model", icon: TreeDeciduous, label: "XGBoost model", sub: "Trained on 300 real queries", accent: ML_COLOR, x: 1250, y: 50 },
  { id: "pagehealth", icon: CheckCircle2, label: "Page Health", sub: "Meta tags, alt text, HTTPS, viewport", accent: EXPLAIN_COLOR, x: 1250, y: 330 },
  { id: "shap", icon: Lightbulb, label: "SHAP explainer", sub: "Why this score, feature by feature", accent: EXPLAIN_COLOR, x: 1500, y: 190 },
  { id: "response", icon: FileJson, label: "JSON result", sub: "One document back to the browser", accent: WEB_COLOR, x: 1750, y: 190 },
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
  const theme = useTheme();
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
        type: "smoothstep",
        animated: true,
        style: { stroke: "#94a3b8", strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: "#94a3b8", width: 18, height: 18 },
      })),
    [],
  );

  return (
    <div>
      <div
        style={{
          height: 460,
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
          colorMode={theme === "dark" ? "dark" : "light"}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.3}
          maxZoom={1.5}
          proOptions={{ hideAttribution: true }}
          nodesConnectable={false}
          elementsSelectable={false}
          panOnScroll
          zoomOnScroll={false}
        >
          <Background variant={BackgroundVariant.Dots} gap={18} size={1.2} color="var(--border)" />
          <Controls showInteractive={false} position="bottom-right" />
        </ReactFlow>
      </div>
      <div style={{ display: "flex", gap: "1.25rem", marginTop: "0.75rem", flexWrap: "wrap" }}>
        <LegendItem color={WEB_COLOR} label="Web layer (JS)" />
        <LegendItem color={ML_COLOR} label="ML core (Python)" />
        <LegendItem color={EXPLAIN_COLOR} label="Explainability" />
      </div>
    </div>
  );
}

function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.78rem", color: "var(--muted-foreground)" }}>
      <span style={{ width: 9, height: 9, borderRadius: 3, background: color, display: "inline-block" }} />
      {label}
    </div>
  );
}
