"use client"

import { SignInButton, useAuth, useUser } from "@clerk/nextjs"
import Link from "next/link"
import { AlertCircle, Bell, CalendarDays, Compass, Loader2, Plus, UserRound, Users } from "lucide-react"
import { useEffect, useState } from "react"
import { SiteFooter } from "@/components/site-footer"
import { SiteNav } from "@/components/site-nav"
import { apiGet, bearerHeaders } from "@/lib/api"

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
  city: string | null
}

type Club = {
  id: string
  name: string
  slug: string
  member_role: string
  member_status: string
}

type NotificationItem = {
  id: string
  title: string
  body: string
  is_read: boolean
}

type AccountData = {
  profile: MyProfile | null
  registrations: Registration[]
  clubs: Club[]
  notifications: NotificationItem[]
}

export default function AccountPage() {
  const { isLoaded, isSignedIn, getToken } = useAuth()
  const { user } = useUser()
  const [data, setData] = useState<AccountData>({
    profile: null,
    registrations: [],
    clubs: [],
    notifications: [],
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true

    async function loadAccount() {
      if (!isLoaded) return
      if (!isSignedIn) {
        setLoading(false)
        return
      }

      setLoading(true)
      setError(null)
      try {
        const token = await getToken()
        const headers = bearerHeaders(token)
        const [profile, registrations, clubs, notifications] = await Promise.all([
          apiGet<MyProfile>("/me/profile", { headers }),
          apiGet<Registration[]>("/me/registrations", { headers }),
          apiGet<Club[]>("/me/clubs", { headers }),
          apiGet<NotificationItem[]>("/me/notifications?limit=5", { headers }),
        ])
        if (!active) return
        setData({ profile, registrations, clubs, notifications })
      } catch (loadError) {
        console.error("Account loading failed.", loadError)
        if (active) setError("We could not load your account data. Check sign-in and API status.")
      } finally {
        if (active) setLoading(false)
      }
    }

    void loadAccount()
    return () => {
      active = false
    }
  }, [getToken, isLoaded, isSignedIn])

  return (
    <>
      <SiteNav />
      <main className="mx-auto min-h-screen max-w-6xl px-4 pb-24 pt-28 sm:px-6">
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
                  {data.profile?.bio || "Track the clubs, events, and updates connected to your profile."}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Link href="/explore" className="inline-flex items-center gap-2 rounded-full border border-border px-4 py-2.5 text-sm font-semibold">
                  <Compass className="size-4" aria-hidden="true" />
                  Explore
                </Link>
                <Link href="/organizer/events/new" className="inline-flex items-center gap-2 rounded-full bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground">
                  <Plus className="size-4" aria-hidden="true" />
                  Add event
                </Link>
              </div>
            </section>

            {error && (
              <div className="mt-6 flex gap-3 rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
                <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
                <p>{error}</p>
              </div>
            )}

            <section className="mt-8 grid gap-4 sm:grid-cols-3">
              <Metric icon={<CalendarDays className="size-5" />} label="Registrations" value={data.registrations.length} />
              <Metric icon={<Users className="size-5" />} label="Clubs" value={data.clubs.length} />
              <Metric icon={<Bell className="size-5" />} label="Unread" value={data.notifications.filter((item) => !item.is_read).length} />
            </section>

            <section className="mt-8 grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
              <Panel title="Upcoming registrations">
                {data.registrations.length > 0 ? (
                  data.registrations.map((registration) => (
                    <Link
                      key={registration.event_id}
                      href={`/explore/${registration.event_id}`}
                      className="block rounded-lg border border-border p-4 transition-colors hover:border-primary/60"
                    >
                      <p className="font-semibold">{registration.title}</p>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {registration.club_name} - {new Date(registration.starts_at).toLocaleDateString()}
                      </p>
                    </Link>
                  ))
                ) : (
                  <EmptyState text="No registrations yet." href="/explore" action="Find an event" />
                )}
              </Panel>

              <Panel title="Your clubs">
                {data.clubs.length > 0 ? (
                  data.clubs.map((club) => (
                    <Link key={club.id} href={`/clubs/${club.slug}`} className="block rounded-lg border border-border p-4 transition-colors hover:border-primary/60">
                      <p className="font-semibold">{club.name}</p>
                      <p className="mt-1 text-sm capitalize text-muted-foreground">
                        {club.member_role} - {club.member_status}
                      </p>
                    </Link>
                  ))
                ) : (
                  <EmptyState text="You have not joined a club yet." href="/clubs" action="Browse clubs" />
                )}
              </Panel>
            </section>

            <Panel title="Notifications" className="mt-6">
              {data.notifications.length > 0 ? (
                data.notifications.map((notification) => (
                  <div key={notification.id} className="rounded-lg border border-border p-4">
                    <p className="font-semibold">{notification.title}</p>
                    <p className="mt-1 text-sm leading-6 text-muted-foreground">{notification.body}</p>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">No notifications yet.</p>
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
      <Link href={href} className="mt-3 inline-flex rounded-full bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground">
        {action}
      </Link>
    </div>
  )
}
