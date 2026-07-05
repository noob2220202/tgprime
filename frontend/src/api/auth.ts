import { apiFetch } from "./client"

export interface CurrentUser {
  id: string
  username: string
}

export function fetchCurrentUser() {
  return apiFetch<CurrentUser>("/api/auth/me")
}

export function login(username: string, password: string) {
  return apiFetch<CurrentUser>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  })
}

export function logout() {
  return apiFetch<{ ok: boolean }>("/api/auth/logout", { method: "POST" })
}
