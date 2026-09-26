export type Parameter = {
  code: string;
  name: string;
  section: string;
  unit: string | null;
  value: string | number | null;
  original_value: string | number | null;
  minimum: number | null;
  maximum: number | null;
  required: boolean;
  value_type: "number" | "text";
  note: string | null;
  source_status: "verified" | "source_present" | "assumed";
  source_name: string | null;
};

export type Project = {
  id: string;
  name: string;
  object_type_code: string;
  calculation_version: string;
  is_demo: boolean;
  parameters: Parameter[];
};

export type Solution = {
  id: string;
  name: string;
  manufacturer: string;
  catalog_type: string | null;
  status: string;
  description: string | null;
  process: string | null;
  trl: number | null;
  industry: string | null;
  price_rub: number | null;
  data_completeness: number;
  source_status: string;
};

export type Candidate = {
  solution_id: string;
  rank: number;
  name: string;
  manufacturer: string;
  price_rub: number | null;
  status: string;
  eligible: boolean;
  score: number;
  contributions: Record<string, number>;
  constraints: { code: string; label: string; status: string; detail: string }[];
  reasons: string[];
  missing_data: string[];
  assumptions: string[];
  requires_verification: boolean;
};

export type MatchingResult = {
  run_id: string;
  model_version: string;
  candidates: Candidate[];
  excluded: Candidate[];
  disclaimer: string;
};

export type Scenario = {
  name: string;
  capex_rub: number;
  annual_opex_rub: number;
  annual_effect_rub: number;
  payback_years: number | null;
  roi_horizon_percent: number | null;
  tco_rub: number;
  cost_per_task_rub: number | null;
};

export type EconomicsResult = {
  model_version: string;
  fleet_basis: "catalog_assumption" | "latest_simulation" | "user_override";
  simulation_run_id: string | null;
  required_robots: number;
  horizon_years: number;
  scenarios: Record<"baseline" | "purchase" | "raas", Scenario>;
  solution: { id: string; name: string; manufacturer: string; price_rub: number };
  sensitivity: {
    factor: string;
    points: { change_percent: number; annual_effect_rub: number; payback_years: number | null }[];
  }[];
  formula_note: string;
  disclaimer: string;
};


export type PlanElementKind =
  | "wall"
  | "door"
  | "storage"
  | "obstacle"
  | "work_zone"
  | "restricted_zone"
  | "pickup"
  | "dropoff"
  | "charger";

export type PlanElement = {
  id: string;
  kind: PlanElementKind;
  label: string;
  x_m: number;
  y_m: number;
  width_m: number;
  height_m: number;
  rotation_deg: number;
  confidence: number;
  source: "model" | "manual" | "demo";
  review_status: "needs_review" | "reviewed" | "confirmed";
  source_region: { page?: number; bbox_px?: number[]; method?: string } | null;
};

export type ProjectPlan = {
  name: string;
  width_m: number;
  height_m: number;
  revision: number;
  source_status: "verified" | "source_present" | "assumed";
  asset_id: string | null;
  scale_m_per_px: number | null;
  scale_status: "unknown" | "confirmed";
  review_status: "draft" | "reviewed" | "confirmed";
  provider_key: string;
  elements: PlanElement[];
};

export type PlanAsset = {
  id: string;
  project_id: string;
  original_name: string;
  media_type: string;
  byte_size: number;
  sha256: string;
  created_at: string;
  content_url: string;
};

export type RecognitionProvider = {
  key: string;
  display_name: string;
  available: boolean;
  uses_model: boolean;
  formats: string[];
  note: string;
  license?: string;
  weights?: string;
};

export type RecognitionResult = {
  provider: { key: string; display_name: string; uses_model: boolean };
  plan: Omit<ProjectPlan, "revision" | "source_status">;
  warnings: string[];
  unresolved: string[];
  model_versions: Record<string, string>;
  revision: { id: string; number: number; review_status: string };
};

export type PlanRevision = {
  id: string;
  revision_number: number;
  asset_id: string | null;
  source: "model" | "manual" | "demo";
  review_status: string;
  provider_key: string;
  created_at: string;
  plan: ProjectPlan;
};

export type SimulationResult = {
  run_id: string;
  model_version: string;
  plan_revision: number;
  robot_count: number;
  recommended_robots: number;
  route_distance_m: number;
  cycle_distance_m: number;
  cycle_time_seconds: number;
  throughput_tasks_hour: number;
  capacity_tasks_hour: number;
  completed_tasks_day: number;
  capacity_gap_tasks_day: number;
  utilization_percent: number;
  route_points: { x_m: number; y_m: number }[];
  warnings: string[];
  assumptions: {
    key: string;
    value: number;
    unit: string;
    status: "assumed";
  }[];
};
