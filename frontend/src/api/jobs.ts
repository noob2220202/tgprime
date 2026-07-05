import { apiFetch } from "./client"

export interface BulkJobItem {
  id: string
  account_id: string
  status: string
  attempt_count: number
  error_message: string | null
  flood_wait_seconds: number | null
  started_at: string | null
  finished_at: string | null
}

export interface BulkJob {
  id: string
  job_type: string
  status: string
  total_items: number
  succeeded_count: number
  failed_count: number
  created_at: string
  started_at: string | null
  finished_at: string | null
}

export interface BulkJobDetail extends BulkJob {
  items: BulkJobItem[]
}

export function listJobs() {
  return apiFetch<BulkJob[]>("/api/bulk-jobs")
}

export function getJob(jobId: string) {
  return apiFetch<BulkJobDetail>(`/api/bulk-jobs/${jobId}`)
}

export interface CreateJobPayload {
  account_ids: string[]
  first_name?: string
  last_name?: string
  bio?: string
  username?: string
  per_account?: Record<string, Record<string, string>>
}

export function createJob(payload: CreateJobPayload, photo?: File | null) {
  const form = new FormData()
  form.set("payload", JSON.stringify(payload))
  if (photo) form.set("photo", photo)
  return apiFetch<BulkJob>("/api/bulk-jobs", { method: "POST", body: form })
}
