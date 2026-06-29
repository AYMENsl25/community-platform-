export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? process.env.API_BASE_URL ?? "http://127.0.0.1:8000/api/v1"

export async function apiGet<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...init?.headers,
    },
    next: { revalidate: 30 },
  })

  if (!response.ok) {
    throw new Error(`COMMUNITI API request failed: ${response.status} ${response.statusText}`)
  }

  return (await response.json()) as T
}
