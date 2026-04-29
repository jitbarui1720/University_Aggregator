import type { Run } from "@/types/run";
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  import.meta.env.BACKEND_URI ??
  "http://localhost:8000";

export async function createRun(collegeName: string): Promise<Run> {
  const res = await fetch(`${API_BASE_URL}/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ college_name: collegeName }),
  });
  if (!res.ok) {
    throw new Error("Failed to create run");
  }
  const created = await res.json();
  return {
    run_id: created.run_id,
    college_name: created.college_name ?? collegeName,
    status: created.status ?? "running",
    created_at: created.created_at ?? new Date().toISOString(),
    updated_at: created.updated_at ?? created.created_at ?? new Date().toISOString(),
    finished_at: created.finished_at ?? null,
    result: created.result ?? null,
    error: created.error ?? null,
  };
}

export async function getRun(runId: string): Promise<Run> {
  const res = await fetch(`${API_BASE_URL}/runs/${runId}`);
  if (!res.ok) {
    throw new Error("Failed to fetch run");
  }
  return res.json();
}
