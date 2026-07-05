export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const isFormData = options.body instanceof FormData
  const res = await fetch(path, {
    ...options,
    credentials: "include",
    headers: {
      // Let the browser set Content-Type (incl. multipart boundary) for FormData bodies.
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      "X-Requested-With": "XMLHttpRequest",
      ...options.headers,
    },
  })

  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail ?? detail
    } catch {
      // ignore non-JSON error bodies
    }
    throw new ApiError(res.status, detail)
  }

  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}
