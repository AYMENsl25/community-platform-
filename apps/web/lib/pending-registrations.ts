import { apiPost, bearerHeaders } from "@/lib/api"

const PENDING_REGISTRATIONS_KEY = "communiti:pending-registrations"

export type PendingRegistration = {
  eventId: string
  eventTitle?: string
  queuedAt: string
}

type RegistrationState = {
  status: string
  waitlist_position: number | null
}

function readPendingRegistrations(): PendingRegistration[] {
  if (typeof window === "undefined") return []

  try {
    const raw = window.localStorage.getItem(PENDING_REGISTRATIONS_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as PendingRegistration[]
    return Array.isArray(parsed) ? parsed.filter((item) => Boolean(item.eventId)) : []
  } catch {
    return []
  }
}

function writePendingRegistrations(items: PendingRegistration[]) {
  window.localStorage.setItem(PENDING_REGISTRATIONS_KEY, JSON.stringify(items))
}

export function queuePendingRegistration(event: Omit<PendingRegistration, "queuedAt">) {
  const existing = readPendingRegistrations()
  const next = [
    ...existing.filter((item) => item.eventId !== event.eventId),
    {
      ...event,
      queuedAt: new Date().toISOString(),
    },
  ]
  writePendingRegistrations(next)
}

export function removePendingRegistration(eventId: string) {
  writePendingRegistrations(readPendingRegistrations().filter((item) => item.eventId !== eventId))
}

export async function syncPendingRegistrations(getToken: () => Promise<string | null>): Promise<string[]> {
  const pending = readPendingRegistrations()
  if (pending.length === 0) return []

  const token = await getToken()
  const synced: string[] = []

  for (const item of pending) {
    try {
      await apiPost<RegistrationState>(`/events/${encodeURIComponent(item.eventId)}/register`, {
        headers: bearerHeaders(token),
      })
      synced.push(item.eventId)
    } catch (error) {
      console.warn("Pending registration sync failed.", item.eventId, error)
    }
  }

  if (synced.length > 0) {
    const syncedSet = new Set(synced)
    writePendingRegistrations(pending.filter((item) => !syncedSet.has(item.eventId)))
  }

  return synced
}
