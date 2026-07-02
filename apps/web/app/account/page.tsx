"use client"

import { SignInButton, useAuth, useUser } from "@clerk/nextjs"
import Link from "next/link"
import useSWR from "swr"
import {
  AlertCircle,
  Bell,
  CalendarDays,
  CheckCircle2,
  Clock3,
  Compass,
  CreditCard,
  Loader2,
  Plus,
  Star,
  Ticket,
  UserRound,
  Users,
} from "lucide-react"
import { useMemo } from "react"
import { SiteFooter } from "@/components/site-footer"
import { SiteNav } from "@/components/site-nav"
import { apiGet, bearerHeaders } from "@/lib/api"
import { formatEventPrice } from "@/lib/events"

type MyProfile = {
  display_name: string
  email: string
  bio: string | null
  city: string | null
  country: string | null
  is_onboarded: boolean
}

type Registration = {
  event_id: string
  title: string
  club_name: string
  starts_at: string
  registration_status: string
  payment_required: boolean
  payment_status: string
  payment_id: string | null
  price_amount: string
  currency: string
  city: string | null
  cover_image_url: string | null
}

type Club = {
  id: string
  name: string
  slug: string
  member_role: string
  member_status: string
  member_count: number
  category_name: string | null
}

type SavedEvent = {
  event_id: string
  title: string
  club_name: string
  starts_at: string
  city: string | null
  saved_at: string
}

type ManagedEvent = {
  id: string
  title: string
  club_name: string
  starts_at: string
  status: string
  registered_count: number
  waitlist_count: number
  price_amount: string
  currency: string
}

type NotificationItem = {
  id: string
  title: string
  body: string
  is_read: boolean
  created_at: string
}

type AccountData = {
  profile: MyProfile | null
  registrations: Registration[]
  clubs: Club[]
  savedEvents: SavedEvent[]
  managedEvents: ManagedEvent[]
  notifications: NotificationItem[]
}

const emptyAccountData: AccountData = {
  profile: null,
  registrations: [],
  clubs: [],
  savedEvents: [],
  managedEvents: [],
  notifications: [],
}

export default function AccountPage() {
  const { isLoaded, isSignedIn, getToken } = useAuth()
  const { user } = useUser()
  const shouldLoad = isLoaded && isSignedIn
  const {
    data = emptyAccountData,
    error: accountError,
    isLoading,
  } = useSWR<AccountData>(shouldLoad ? "account-dashboard" : null, async () => {
    const token = await getToken()
    const headers = bearerHeaders(token)
    const [profile, registrations, clubs, savedEvents, managedEvents, notifications] = await Promise.all([
      apiGet<MyProfile>("/me/profile", { headers }),
      apiGet<Registration[]>("/me/registrations", { headers }),
      apiGet<Club[]>("/me/clubs", { headers }),
      apiGet<SavedEvent[]>("/me/saved-events", { headers }),
      apiGet<ManagedEvent[]>("/me/events", { headers }),
      apiGet<NotificationItem[]>("/me/notifications?limit=8", { headers }),
    ])
    return { profile, registrations, clubs, savedEvents, managedEvents, notifications }
  })
  const loading = !isLoaded || (shouldLoad && isLoading)
  const error = accountError ? "We could not load your account data. Check sign-in and API status." : null

  const now = useMemo(() => new Date(), [])
  const upcoming = data.registrations.filter((item) => new Date(item.starts_at) >= now)
  const paidTickets = data.registrations.filter((item) => item.payment_status === "paid")
  const pendingPayments = data.registrations.filter(
    (item) => item.payment_required && ["unpaid", "pending"].includes(item.payment_status),
  )
  const unreadCount = data.notifications.filter((item) => !item.is_read).length

  return (
    <>
      <SiteNav />
      <main className="mx-auto min-h-screen max-w-7xl px-4 pb-24 pt-28 sm:px-6">
        {!isLoaded || loading ? (
          <div className="flex min-h-[50vh] items-center justify-center text-muted-foreground">
            <Loader2 className="mr-2 size-5 animate-spin" aria-hidden="true" />
            Loading account
          </div>
        ) : !isSignedIn ? (
          <section className="mx-auto max-w-xl rounded-lg border border-border bg-card p-8 text-center">
            <UserRound className="mx-auto size-8 text-primary" aria-hidden="true" />
            <h1 className="mt-4 text-3xl font-semibold tracking-tight">Sign in to see your COMMUNITI</h1>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              Your account page tracks registrations, clubs, notifications, and organizer tools.
            </p>
            <SignInButton mode="modal">
              <button className="mt-6 rounded-full bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground">
                Sign in
              </button>
            </SignInButton>
          </section>
        ) : (
          <>
            <section className="flex flex-col gap-6 border-b border-border pb-8 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <p className="text-sm font-semibold uppercase tracking-wide text-primary">Your COMMUNITI</p>
                <h1 className="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl">
                  {data.profile?.display_name || user?.fullName || "Account"}
                </h1>
                <p className="mt-3 max-w-2xl text-base leading-7 text-muted-foreground">
                  {data.profile?.bio || "Track your registrations, tickets, clubs, saved events, and organizer work."}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Link href="/explore" className="inline-flex items-center gap-2 rounded-full border border-border px-4 py-2.5 text-sm font-semibold">
                  <Compass className="size-4" aria-hidden="true" />
                  Explore
                </Link>
                <Link href="/organizer" className="inline-flex items-center gap-2 rounded-full bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground">
                  <Plus className="size-4" aria-hidden="true" />
                  Organizer
                </Link>
              </div>
            </section>

            {error && (
              <div className="mt-6 flex gap-3 rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
                <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
                <p>{error}</p>
              </div>
            )}

            <section className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
              <Metric icon={<CalendarDays className="size-5" />} label="Upcoming" value={upcoming.length} />
              <Metric icon={<Ticket className="size-5" />} label="Paid tickets" value={paidTickets.length} />
              <Metric icon={<Clock3 className="size-5" />} label="Pending pay" value={pendingPayments.length} />
              <Metric icon={<Users className="size-5" />} label="Clubs" value={data.clubs.length} />
              <Metric icon={<Bell className="size-5" />} label="Unread" value={unreadCount} />
            </section>

            <section className="mt-8 grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
              <Panel title="My upcoming events">
                {upcoming.length > 0 ? upcoming.slice(0, 6).map((registration) => <RegistrationRow key={registration.event_id} registration={registration} />) : <EmptyState text="No upcoming registrations yet." href="/explore" action="Find an event" />}
              </Panel>

              <Panel title="Pending payments">
                {pendingPayments.length > 0 ? pendingPayments.slice(0, 5).map((registration) => <RegistrationRow key={registration.event_id} registration={registration} compact />) : <p className="text-sm text-muted-foreground">No pending payments.</p>}
              </Panel>
            </section>

            <section className="mt-6 grid gap-6 lg:grid-cols-3">
              <Panel title="Paid tickets">
                {paidTickets.length > 0 ? paidTickets.slice(0, 4).map((registration) => <RegistrationRow key={registration.event_id} registration={registration} compact />) : <p className="text-sm text-muted-foreground">Paid tickets will appear here after payment confirmation.</p>}
              </Panel>

              <Panel title="Joined clubs">
                {data.clubs.length > 0 ? (
                  data.clubs.slice(0, 5).map((club) => (
                    <Link key={club.id} href={`/clubs/${club.slug}`} className="block rounded-lg border border-border p-4 transition-colors hover:border-primary/60">
                      <p className="font-semibold">{club.name}</p>
                      <p className="mt-1 text-sm capitalize text-muted-foreground">
                        {club.member_role} - {club.member_status} - {club.member_count} members
                      </p>
                    </Link>
                  ))
                ) : (
                  <EmptyState text="You have not joined a club yet." href="/clubs" action="Browse clubs" />
                )}
              </Panel>

              <Panel title="Saved events">
                {data.savedEvents.length > 0 ? (
                  data.savedEvents.slice(0, 5).map((event) => (
                    <Link key={event.event_id} href={`/explore/${event.event_id}`} className="block rounded-lg border border-border p-4 transition-colors hover:border-primary/60">
                      <p className="font-semibold">{event.title}</p>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {event.club_name} - {new Date(event.starts_at).toLocaleDateString()}
                      </p>
                    </Link>
                  ))
                ) : (
                  <EmptyState text="Saved events help you come back later." href="/explore" action="Explore events" />
                )}
              </Panel>
            </section>

            <section className="mt-6 grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
              <Panel title="Organizer overview">
                {data.managedEvents.length > 0 ? (
                  data.managedEvents.slice(0, 5).map((event) => (
                    <Link key={event.id} href={`/organizer?event=${event.id}`} className="block rounded-lg border border-border p-4 transition-colors hover:border-primary/60">
                      <p className="font-semibold">{event.title}</p>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {event.club_name} - {event.registered_count} going - {formatEventPrice(Number(event.price_amount), event.currency)}
                      </p>
                    </Link>
                  ))
                ) : (
                  <EmptyState text="No managed events yet." href="/organizer/events/new" action="Create event" />
                )}
              </Panel>

              <Panel title="Notifications">
                {data.notifications.length > 0 ? (
                  data.notifications.map((notification) => (
                    <div key={notification.id} className="rounded-lg border border-border p-4">
                      <div className="flex items-start justify-between gap-4">
                        <p className="font-semibold">{notification.title}</p>
                        {!notification.is_read && <span className="mt-1 size-2 rounded-full bg-primary" aria-label="Unread" />}
                      </div>
                      <p className="mt-1 text-sm leading-6 text-muted-foreground">{notification.body}</p>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">No notifications yet.</p>
                )}
              </Panel>
            </section>
          </>
        )}
      </main>
      <SiteFooter />
    </>
  )
}

function RegistrationRow({ registration, compact = false }: { registration: Registration; compact?: boolean }) {
  const paid = registration.payment_status === "paid"
  const pendingPayment = registration.payment_required && ["unpaid", "pending"].includes(registration.payment_status)
  return (
    <Link href={`/explore/${registration.event_id}`} className="block rounded-lg border border-border p-4 transition-colors hover:border-primary/60">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="font-semibold">{registration.title}</p>
          <p className="mt-1 text-sm text-muted-foreground">
            {registration.club_name} - {new Date(registration.starts_at).toLocaleDateString()}
          </p>
        </div>
        <span className="inline-flex shrink-0 items-center gap-1 rounded-full border border-border px-2.5 py-1 text-[11px] font-semibold capitalize">
          {paid ? <CheckCircle2 className="size-3" aria-hidden="true" /> : pendingPayment ? <CreditCard className="size-3" aria-hidden="true" /> : <Clock3 className="size-3" aria-hidden="true" />}
          {paid ? "paid" : pendingPayment ? "pay" : registration.registration_status}
        </span>
      </div>
      {!compact && (
        <p className="mt-3 text-xs text-muted-foreground">
          {formatEventPrice(Number(registration.price_amount), registration.currency)} - {registration.city || "Location TBA"}
        </p>
      )}
    </Link>
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
      <Star className="mb-3 size-4 text-primary" aria-hidden="true" />
      <p>{text}</p>
      <Link href={href} className="mt-3 inline-flex rounded-full bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground">
        {action}
      </Link>
    </div>
  )
}