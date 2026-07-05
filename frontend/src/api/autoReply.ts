import { apiFetch } from "./client"

export interface AutoReplyRule {
  account_id: string
  enabled: boolean
  reply_text: string
  cooldown_minutes: number
}

export function getAutoReply(accountId: string) {
  return apiFetch<AutoReplyRule>(`/api/accounts/${accountId}/auto-reply`)
}

export function updateAutoReply(accountId: string, payload: Omit<AutoReplyRule, "account_id">) {
  return apiFetch<AutoReplyRule>(`/api/accounts/${accountId}/auto-reply`, {
    method: "PUT",
    body: JSON.stringify(payload),
  })
}
