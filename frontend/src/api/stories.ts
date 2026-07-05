import { apiFetch } from "./client"

export function postStory(accountId: string, photo: File, caption?: string) {
  const form = new FormData()
  form.set("photo", photo)
  if (caption) form.set("caption", caption)
  return apiFetch<{ ok: boolean }>(`/api/accounts/${accountId}/story`, { method: "POST", body: form })
}
