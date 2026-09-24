export type Severity = "info" | "warning" | "error" | "blocking";
export type StepStatus = "ok" | "warning" | "blocked" | "failed" | "not_run";

export interface Finding {
  code: string;
  severity: Severity;
  message: string;
  count: number;
  column: string | null;
  sample_ids: string[];
  details: any;
}

export interface StepReport {
  module_id: string;
  module_name: string;
  spec_version: string;
  status: StepStatus;
  started_at?: string;
  duration_s?: number;
  n_rows_in?: number;
  n_rows_out?: number;
  n_cols_in?: number;
  n_cols_out?: number;
  rows_dropped?: number;
  rows_flagged?: number;
  columns_added?: string[];
  columns_modified?: string[];
  params_effective?: Record<string, any>;
  findings?: Finding[];
  artifacts?: Record<string, string>;
  context_updates?: string[];
}

export interface RunReport {
  run_id: string;
  started_at: string;
  finished_at: string;
  duration_s: number;
  status: "ok" | "warning" | "blocked" | "failed";
  failed_step: string | null;
  config_digest: string;
  schema_version: string;
  input: {
    path: string;
    n_rows: number;
    n_cols: number;
    adapter: string;
  };
  steps: StepReport[];
  context_final: {
    adjustment_set: string[];
    treatment_definition: any;
    cluster_column: string | null;
    fold_column: string | null;
    outcome_observed_column: string | null;
  };
  outputs: any;
}

export interface ModuleContent {
  id: string;
  name: string;
  file: string;
  lane: number;
  short: string;
  long: string;
  risk: string;
}
