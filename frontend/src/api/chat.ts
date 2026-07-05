import { apiFetch } from "./client"

export interface Dialog {
  peer_id: number
  peer_type: string
  title: string
  unread_count: number
  last_message_text: string | null
  last_message_date: string | null
}

export interface Message {
  id: number
  date: string
  out: boolean
  sender_id: number | null
  text: string
}

export function getDialogs(accountId: string) {
  return apiFetch<Dialog[]>(`/api/accounts/${accountId}/dialogs`)
}

export function getMessages(accountId: string, peerId: number) {
  return apiFetch<Message[]>(`/api/accounts/${accountId}/dialogs/${peerId}/messages`)
}

export function sendMessage(accountId: string, peerId: number, text: string) {
  return apiFetch<Message>(`/api/accounts/${accountId}/dialogs/${peerId}/messages`, {
    method: "POST",
    body: JSON.stringify({ text }),
  })
}

export function liveSocketUrl(accountId: string): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
  return `${protocol}//${window.location.host}/api/accounts/${accountId}/live`
}
