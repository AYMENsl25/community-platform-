export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? process.env.API_BASE_URL ?? "http://127.0.0.1:8000/api/v1"

const REQUEST_TIMEOUT_MS = 15_000

type CommunitiErrorBody = {
  error?: {
    code?: string
    message?: string
    request_id?: string
  }
  detail?: string
}

type CommunitiRequestInit = RequestInit & {
  next?: {
    revalidate?: number | false
  }
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const method = init?.method?.toUpperCase() ?? "GET"
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
  const request: CommunitiRequestInit = {
    ...init,
    signal: init?.signal ?? controller.signal,
    headers: {
      Accept: "application/json",
      ...init?.headers,
    },
  }

  if (method === "GET") {
    request.next = { revalidate: 30 }
  }

  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, request)
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("COMMUNITI API request failed: Request timed out. Check that the API server is running.")
    }
    throw error
  } finally {
    clearTimeout(timeout)
  }

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`
    try {
      const body = (await response.json()) as CommunitiErrorBody
      detail = body.error?.message ?? body.detail ?? detail
    } catch {
      // Keep the HTTP status detail when the response is not JSON.
    }
    throw new Error(`COMMUNITI API request failed: ${detail}`)
  }

  return (await response.json()) as T
}

export function bearerHeaders(token: string | null | undefined): HeadersInit {
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export async function apiGet<T>(path: string, init?: RequestInit): Promise<T> {
  return apiRequest<T>(path, init)
}

export async function apiPost<T>(path: string, init?: RequestInit): Promise<T> {
  return apiRequest<T>(path, {
    ...init,
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  })
}
