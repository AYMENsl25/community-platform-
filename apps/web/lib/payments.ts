import { apiPost, bearerHeaders } from "@/lib/api"

export type CheckoutSession = {
  event_id: string
  provider: string
  checkout_id: string | null
  checkout_url: string | null
  amount: string
  currency: string
  status: string
  mode: "development" | "live"
  message: string | null
}

export async function createEventCheckout({
  eventId,
  token,
  returnPath,
}: {
  eventId: string
  token: string | null
  returnPath: string
}): Promise<CheckoutSession> {
  return apiPost<CheckoutSession>(`/payments/events/${encodeURIComponent(eventId)}/checkout`, {
    body: JSON.stringify({ return_path: returnPath }),
    headers: bearerHeaders(token),
  })
}
