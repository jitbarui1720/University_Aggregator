export type RunStatus = "running" | "completed" | "failed" | "invalid_program";

export interface FieldEntry {
  value: string;
  source_url: string;
  source_quote: string;
}

export interface Discovery {
  program_name: string;
  program_url: string;
  tuition_url: string;
  faculty_url: string;
  admissions_url: string;
  program_type?: string;
  is_valid_certificate?: string;
  rejection_reason?: string | null;
  context_urls: string[];
  validation_status?: string;
  validation_reason?: string;
}

export interface RunResult {
  status: string;
  college_name: string;
  slug: string;
  validation: {
    is_valid: boolean;
    reason: string;
  };
  discovery: Discovery;
  fields: Record<string, FieldEntry>;
  row: Record<string, string>;
  csv_paths: {
    discovery_csv: string;
    full_csv: string;
  };
  /** Non–Not Found field count after normalization (completed runs only). */
  found_field_count?: number;
  /** True when a second full pipeline run was performed due to low field count. */
  retry_applied?: boolean;
}

export interface Run {
  run_id: string;
  college_name: string;
  status: RunStatus;
  created_at: string;
  updated_at: string;
  finished_at: string | null;
  result: RunResult | null;
  error: {
    message: string;
    traceback?: string;
  } | null;
}
