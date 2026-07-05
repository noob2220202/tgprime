import { apiFetch } from "./client"

export interface Account {
  id: string
  label: string
  phone_number: string | null
  telegram_user_id: number | null
  username: string | null
  first_name: string | null
  last_name: string | null
  bio: string | null
  status: string
  status_detail: string | null
  created_at: string
}

export function listAccounts() {
  return apiFetch<Account[]>("/api/accounts")
}

export function loginStart(payload: { label: string; phone_number: string; api_id: number; api_hash: string }) {
  return apiFetch<{ login_session_id: string }>("/api/accounts/login/start", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export function loginVerifyCode(payload: { login_session_id: string; code: string }) {
  return apiFetch<{ status: "done" | "needs_2fa"; account: Account | null }>(
    "/api/accounts/login/verify-code",
    { method: "POST", body: JSON.stringify(payload) }
  )
}

export function loginVerify2fa(payload: { login_session_id: string; password: string }) {
  return apiFetch<Account>("/api/accounts/login/verify-2fa", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export function importSession(payload: { label: string; api_id: string; api_hash: string; file: File }) {
  const form = new FormData()
  form.set("label", payload.label)
  form.set("api_id", payload.api_id)
  form.set("api_hash", payload.api_hash)
  form.set("session_file", payload.file)
  return apiFetch<Account>("/api/accounts/import-session", { method: "POST", body: form })
}
