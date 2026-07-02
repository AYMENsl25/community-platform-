"use client"

import { SignInButton, useAuth } from "@clerk/nextjs"
import Link from "next/link"
import useSWR from "swr"
import { useSearchParams } from "next/navigation"
import { AlertCircle, CalendarDays, CheckCircle2, CreditCard, Loader2, Plus, Users } from "lucide-react"
import { Suspense, useMemo, useState } from "react"
import { SiteFooter } from "@/components/site-footer"
import { SiteNav } from "@/components/site-nav"
import { apiGet, bearerHeaders } from "@/lib/api"
import { formatEventPrice } from "@/lib/events"

type ManagedClub = {
  id: string
  name: string
  slug: string
  member_role: string
  member_status: string
  member_count: number
}

type ManagedEvent = {
  id: string
  club_id: string
  club_name: string
  title: string
  starts_at: string
  status: string
  registered_count: number
  waitlist_count: number
  price_amount: string
  currency: string
}

type Attendee = {
  registration_id: string
  user_id: string
  display_name: string
  email: string
  registration_status: string
  payment_required: boolean
  payment_status: string
  amount: string | null
  currency: string | null
  registered_at: string
}

export default function OrganizerPage() {
  return (
    <Suspense fallback={<OrganizerPageFallback />}>
      <OrganizerDashboard />
    </Suspense>
  )
}

function OrganizerPageFallback() {
  return (
    <>
      <SiteNav />
      <main className="mx-auto min-h-screen max-w-7xl px-4 pb-24 pt-28 sm:px-6">
        <div className="flex min-h-[50vh] items-center justify-center text-muted-foreground">
          <Loader2 className="mr-2 size-5 animate-spin" aria-hidden="true" />
          Loading organizer dashboard
        </div>
      </main>
      <SiteFooter />
    </>
  )
}

function OrganizerDashboard() {
  const { isLoaded, isSignedIn, getToken } = useAuth()
  const searchParams = useSearchParams()
  const requestedEvent = searchParams.get("event")
  const [selectedEventId, setSelectedEventId] = useState<string | null>(requestedEvent)
  const shouldLoad = isLoaded && isSignedIn
  const {
    data: organizerData = { clubs: [], events: [] },
    error: organizerError,
    isLoading,
  } = useSWR(shouldLoad ? "organizer-dashboard" : null, async () => {
    const token = await getToken()
    const headers = bearerHeaders(token)
    const [clubData, eventData] = await Promise.all([
      apiGet<ManagedClub[]>("/me/clubs", { headers }),
      apiGet<ManagedEvent[]>("/me/events", { headers }),
    ])
    return {
      clubs: clubData.filter((club) => ["owner", "admin"].includes(club.member_role)),
      events: eventData,
    }
  })
  const clubs = organizerData.clubs
  const events = organizerData.events
  const loading = !isLoaded || (shouldLoad && isLoading)
  const error = organizerError ? "Organizer data could not be loaded. Check sign-in and API status." : null

  const activeEventId = selectedEventId || requestedEvent || events[0]?.id || null

  const {
    data: attendees = [],
    isLoading: attendeesLoading,
  } = useSWR(activeEventId && isSignedIn ? ["event-attendees", activeEventId] : null, async ([, eventId]) => {
    const token = await getToken()
    return apiGet<Attendee[]>(`/events/${encodeURIComponent(eventId)}/registrations`, {
      headers: bearerHeaders(token),
    })
  })
  const selectedEvent = useMemo(() => events.find((event) => event.id === activeEventId) ?? null, [activeEventId, events])
  const paidCount = attendees.filter((attendee) => attendee.payment_status === "paid").length
  const pendingCount = attendees.filter((attendee) => attendee.payment_required && attendee.payment_status !== "paid").length

  return (
    <>
      <SiteNav />
      <main className="mx-auto min-h-screen max-w-7xl px-4 pb-24 pt-28 sm:px-6">
        {!isLoaded || loading ? (
          <div className="flex min-h-[50vh] items-center justify-center text-muted-foreground">
            <Loader2 className="mr-2 size-5 animate-spin" aria-hidden="true" />
            Loading organizer dashboard
          </div>
        ) : !isSignedIn ? (
          <section className="mx-auto max-w-xl rounded-lg border border-border bg-card p-8 text-center">
            <Users className="mx-auto size-8 text-primary" aria-hidden="true" />
            <h1 className="mt-4 text-3xl font-semibold tracking-tight">Sign in to manage your clubs</h1>
            <SignInButton mode="modal">
              <button className="mt-6 rounded-full bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground">Sign in</button>
            </SignInButton>
          </section>
        ) : (
          <>
            <section className="flex flex-col gap-6 border-b border-border pb-8 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <p className="text-sm font-semibold uppercase tracking-wide text-primary">Organizer dashboard</p>
                <h1 className="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl">Manage clubs and events</h1>
                <p className="mt-3 max-w-2xl text-base leading-7 text-muted-foreground">Review attendees, payment states, and the events connected to your clubs.</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Link href="/organizer/clubs/new" className="inline-flex items-center gap-2 rounded-full border border-border px-4 py-2.5 text-sm font-semibold">
                  <Plus className="size-4" aria-hidden="true" />
                  New club
                </Link>
                <Link href="/organizer/events/new" className="inline-flex items-center gap-2 rounded-full bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground">
                  <Plus className="size-4" aria-hidden="true" />
                  New event
                </Link>
              </div>
            </section>

            {error && (
              <div className="mt-6 flex gap-3 rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
                <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
                <p>{error}</p>
              </div>
            )}

            <section className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <Metric icon={<Users className="size-5" />} label="Managed clubs" value={clubs.length} />
              <Metric icon={<CalendarDays className="size-5" />} label="Managed events" value={events.length} />
              <Metric icon={<CheckCircle2 className="size-5" />} label="Paid attendees" value={paidCount} />
              <Metric icon={<CreditCard className="size-5" />} label="Unpaid/pending" value={pendingCount} />
            </section>

            <section className="mt-8 grid gap-6 lg:grid-cols-[340px_1fr]">
              <Panel title="Manage events">
                {events.length > 0 ? (
                  events.map((event) => (
                    <button key={event.id} type="button" onClick={() => setSelectedEventId(event.id)} className={`rounded-lg border p-4 text-left transition-colors ${activeEventId === event.id ? "border-primary bg-primary/5" : "border-border hover:border-primary/60"}`}>
                      <p className="font-semibold">{event.title}</p>
                      <p className="mt-1 text-sm text-muted-foreground">{event.club_name}</p>
                      <p className="mt-2 text-xs text-muted-foreground">{event.registered_count} registered - {formatEventPrice(Number(event.price_amount), event.currency)}</p>
                    </button>
                  ))
                ) : (
                  <EmptyState text="No managed events yet." href="/organizer/events/new" action="Create event" />
                )}
              </Panel>

              <Panel title={selectedEvent ? `Attendees: ${selectedEvent.title}` : "Attendees"}>
                {attendeesLoading ? (
                  <p className="flex items-center text-sm text-muted-foreground"><Loader2 className="mr-2 size-4 animate-spin" aria-hidden="true" /> Loading attendees</p>
                ) : attendees.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[680px] text-left text-sm">
                      <thead className="text-xs uppercase tracking-wide text-muted-foreground">
                        <tr>
                          <th className="py-2 pr-4">Attendee</th>
                          <th className="py-2 pr-4">Registration</th>
                          <th className="py-2 pr-4">Payment</th>
                          <th className="py-2 pr-4">Amount</th>
                          <th className="py-2">Registered</th>
                        </tr>
                      </thead>
                      <tbody>
                        {attendees.map((attendee) => (
                          <tr key={attendee.registration_id} className="border-t border-border">
                            <td className="py-3 pr-4">
                              <p className="font-semibold">{attendee.display_name}</p>
                              <p className="text-xs text-muted-foreground">{attendee.email}</p>
                            </td>
                            <td className="py-3 pr-4 capitalize">{attendee.registration_status}</td>
                            <td className="py-3 pr-4 capitalize">{attendee.payment_status}</td>
                            <td className="py-3 pr-4">{attendee.amount ? formatEventPrice(Number(attendee.amount), attendee.currency || "SAR") : "Free"}</td>
                            <td className="py-3">{new Date(attendee.registered_at).toLocaleDateString()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No attendees found for this event yet.</p>
                )}
              </Panel>
            </section>

            <Panel title="Manage clubs" className="mt-6">
              {clubs.length > 0 ? (
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {clubs.map((club) => (
                    <Link key={club.id} href={`/clubs/${club.slug}`} className="rounded-lg border border-border p-4 transition-colors hover:border-primary/60">
                      <p className="font-semibold">{club.name}</p>
                      <p className="mt-1 text-sm capitalize text-muted-foreground">{club.member_role} - {club.member_count} members</p>
                    </Link>
                  ))}
                </div>
              ) : (
                <EmptyState text="No managed clubs yet." href="/organizer/clubs/new" action="Create club" />
              )}
            </Panel>
          </>
        )}
      </main>
      <SiteFooter />
    </>
  )
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <div className="rounded-lg border border-border bg-card p-5">
      <span className="text-primary">{icon}</span>
      <p className="mt-4 text-3xl font-semibold tracking-tight">{value}</p>
      <p className="mt-1 text-sm text-muted-foreground">{label}</p>
    </div>
  )
}

function Panel({ title, children, className }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <section className={className}>
      <h2 className="text-xl font-semibold tracking-tight">{title}</h2>
      <div className="mt-4 grid gap-3 rounded-lg border border-border bg-card p-4">{children}</div>
    </section>
  )
}

function EmptyState({ text, href, action }: { text: string; href: string; action: string }) {
  return (
    <div className="rounded-lg border border-dashed border-border p-5 text-sm text-muted-foreground">
      <p>{text}</p>
      <Link href={href} className="mt-3 inline-flex rounded-full bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground">{action}</Link>
    </div>
  )
}


