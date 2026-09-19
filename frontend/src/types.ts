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

