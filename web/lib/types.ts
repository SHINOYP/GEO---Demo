// Mirrors exactly the JSON shape produced by
// citation-predictor/backend/cli.py's `analyze` subcommand.

export interface ShapDriver {
  feature: string;
  value: number | string | boolean;
  shap_value: number;
}

export interface ShapData {
  shap_values: Record<string, number>;
  top_positive: ShapDriver[];
  top_negative: ShapDriver[];
  base_value: number;
}

export interface Recommendation {
  priority: "high" | "medium" | "low";
  category: string;
  title: string;
  description: string;
  impact: "high" | "medium" | "low";
}

export interface Features {
  model_features: Record<string, number>;
  content: {
    word_count: number;
    paragraph_count: number;
    list_count: number;
    table_count: number;
    avg_paragraph_length: number;
    number_count: number;
    [key: string]: number;
  };
  structure: {
    heading_count: number;
    h1_count: number;
    heading_hierarchy_score: number;
    [key: string]: number;
  };
  schema: {
    schema_present: number;
    [key: string]: number;
  };
  local_business: {
    has_phone: number;
    has_address: number;
    [key: string]: number;
  };
  derived: {
    factual_density: number;
    format_diversity: number;
    emphasis_density: number;
    macro_score: number;
    meso_score: number;
    micro_score: number;
  };
}

export interface AnalysisResult {
  url: string;
  final_url: string;
  timestamp: string;
  citation_probability: number;
  citation_score: number;
  prediction: string;
  likelihood_level: string;
  features: Features;
  shap_data: ShapData;
  shap_error: string | null;
  recommendations: Recommendation[];
  model_note: string;
  mock_used?: boolean; // set client-side when a demo fixture was used
}

export interface ErrorPayload {
  error: true;
  kind: "scraping" | "validation" | "internal";
  message: string;
}

export function isErrorPayload(x: unknown): x is ErrorPayload {
  return !!x && typeof x === "object" && (x as ErrorPayload).error === true;
}
