import { expect, test } from "@playwright/test"

const apiBaseURL = process.env.E2E_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1"
const memberHeaders = { "X-Communiti-User-Email": "member@communiti.local" }
const organizerHeaders = { "X-Communiti-User-Email": "organizer@communiti.local" }

test.describe("live signed-in flows", () => {
  test("registration, pending payment, clubs, dashboard, and organizer attendee states", async ({ page, request }) => {
    await page.goto("/explore")
    await expect(page).toHaveURL(/\/explore/)

    const eventsResponse = await request.get(`${apiBaseURL}/events?limit=10`)
    expect(eventsResponse.ok()).toBeTruthy()
    const events = await eventsResponse.json()
    expect(events.length).toBeGreaterThan(0)

    const paidEvent = events.find((event: { price_amount: string }) => Number(event.price_amount) > 0)
    expect(paidEvent).toBeTruthy()
    const checkoutResponse = await request.post(`${apiBaseURL}/payments/events/${paidEvent.id}/checkout`, {
      headers: {
        ...memberHeaders,
        "Idempotency-Key": `playwright-paid-${Date.now()}`,
      },
      data: { return_path: `/explore/${paidEvent.id}` },
    })
    expect(checkoutResponse.ok()).toBeTruthy()
    const checkout = await checkoutResponse.json()
    expect(checkout.status).toBe("payment_pending")

    const registrationsResponse = await request.get(`${apiBaseURL}/me/registrations`, {
      headers: memberHeaders,
    })
    expect(registrationsResponse.ok()).toBeTruthy()
    const registrations = await registrationsResponse.json()
    expect(registrations.some((registration: { event_id: string; payment_status: string }) => registration.event_id === paidEvent.id && registration.payment_status === "pending")).toBeTruthy()

    const clubsResponse = await request.get(`${apiBaseURL}/clubs?limit=5`)
    expect(clubsResponse.ok()).toBeTruthy()
    const clubs = await clubsResponse.json()
    expect(clubs.length).toBeGreaterThan(0)

    const membershipResponse = await request.get(`${apiBaseURL}/clubs/${clubs[0].id}/membership`, {
      headers: memberHeaders,
    })
    expect(membershipResponse.ok()).toBeTruthy()
    const membership = await membershipResponse.json()
    expect(membership.club_id).toBe(clubs[0].id)

    const managedEventsResponse = await request.get(`${apiBaseURL}/me/events`, {
      headers: organizerHeaders,
    })
    expect(managedEventsResponse.ok()).toBeTruthy()
    const managedEvents = await managedEventsResponse.json()
    expect(managedEvents.length).toBeGreaterThan(0)

    const attendeesResponse = await request.get(`${apiBaseURL}/events/${managedEvents[0].id}/registrations`, {
      headers: organizerHeaders,
    })
    expect(attendeesResponse.ok()).toBeTruthy()
    const attendees = await attendeesResponse.json()
    expect(Array.isArray(attendees)).toBeTruthy()

    await page.goto("/account")
    await expect(page).toHaveURL(/\/account/)
    await page.goto("/organizer")
    await expect(page).toHaveURL(/\/sign-in/)
  })
})

