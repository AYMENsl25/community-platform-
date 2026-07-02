import Image from "next/image"
import Link from "next/link"
import { notFound } from "next/navigation"
import type { Metadata } from "next"
import { ArrowLeft, CalendarPlus, MapPin, ShieldCheck, UserRound, Users } from "lucide-react"
import { ClubJoinButton } from "@/components/club-join-button"
import { SiteFooter } from "@/components/site-footer"
import { SiteNav } from "@/components/site-nav"
import { getClub, getClubMembers, getClubUpcomingEvents, type ClubEventSummary } from "@/lib/backend-clubs"
import { formatEventPrice } from "@/lib/events"

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params
  const club = await getClub(slug)
  if (!club) return { title: "Club not found - COMMUNITI" }
  return {
    title: `${club.name} - COMMUNITI`,
    description: club.description || `Join ${club.name} on COMMUNITI.`,
  }
}

export default async function ClubPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params
  const club = await getClub(slug)
  if (!club) notFound()

  const [members, clubEvents] = await Promise.all([getClubMembers(club.id), getClubUpcomingEvents(club.id)])

  return (
    <>
      <SiteNav />
      <main className="mx-auto min-h-screen max-w-6xl px-4 pb-24 pt-24 sm:px-6">
        <Link href="/clubs" className="inline-flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground">
          <ArrowLeft className="size-4" aria-hidden="true" />
          Back to clubs
        </Link>

        <section className="mt-6 overflow-hidden rounded-lg border border-border bg-card">
          <div className="relative h-72 bg-muted sm:h-96">
            <Image src={club.cover_image_url || club.logo_url || "/placeholder.jpg"} alt={club.name} fill priority sizes="100vw" className="object-cover" />
            <div className="absolute inset-0 bg-gradient-to-t from-background via-background/40 to-transparent" />
            <div className="absolute inset-x-0 bottom-0 p-6 sm:p-8">
              <div className="flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-background/75 px-3 py-1 text-xs font-semibold backdrop-blur">
                  <ShieldCheck className="size-3.5 text-primary" aria-hidden="true" />
                  {club.status}
                </span>
                <span className="rounded-full bg-background/75 px-3 py-1 text-xs font-semibold backdrop-blur">{club.category_name || "Community"}</span>
              </div>
              <h1 className="mt-3 text-4xl font-semibold tracking-tight sm:text-6xl">{club.name}</h1>
            </div>
          </div>

          <div className="grid gap-8 p-6 sm:p-8 lg:grid-cols-[1fr_320px]">
            <div>
              <p className="text-base leading-8 text-muted-foreground">{club.description || "This club is building a public community on COMMUNITI."}</p>
              <div className="mt-6 grid gap-3 sm:grid-cols-3">
                <Fact icon={<Users className="size-4" />} label="Members" value={club.member_count.toLocaleString()} />
                <Fact icon={<MapPin className="size-4" />} label="City" value={club.city || "Online"} />
                <Fact icon={<CalendarPlus className="size-4" />} label="Upcoming" value={clubEvents.length.toString()} />
              </div>

              <section className="mt-8">
                <h2 className="text-xl font-semibold tracking-tight">Member preview</h2>
                {members.length > 0 ? (
                  <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    {members.map((member) => (
                      <div key={member.user_id} className="flex items-center gap-3 rounded-lg border border-border bg-background/50 p-3">
                        <div className="relative size-10 overflow-hidden rounded-full bg-muted">
                          {member.avatar_url ? <Image src={member.avatar_url} alt={member.display_name} fill sizes="40px" className="object-cover" /> : <UserRound className="m-2.5 size-5 text-muted-foreground" aria-hidden="true" />}
                        </div>
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold">{member.display_name}</p>
                          <p className="text-xs capitalize text-muted-foreground">{member.role}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="mt-4 rounded-lg border border-dashed border-border p-5 text-sm text-muted-foreground">Members will appear here as the club grows.</p>
                )}
              </section>
            </div>

            <aside className="rounded-lg border border-border bg-background/45 p-5">
              <p className="text-sm font-semibold">Organizer</p>
              <div className="mt-4 flex items-center gap-3">
                <div className="relative size-11 overflow-hidden rounded-full bg-muted">
                  {club.owner_avatar_url ? <Image src={club.owner_avatar_url} alt={club.owner_name} fill sizes="44px" className="object-cover" /> : <UserRound className="m-3 size-5 text-muted-foreground" aria-hidden="true" />}
                </div>
                <div>
                  <p className="text-sm font-semibold">{club.owner_name}</p>
                  <p className="text-xs text-muted-foreground">Club organizer</p>
                </div>
              </div>
              <p className="mt-5 text-sm font-semibold">Join this club</p>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">Follow the club, keep track of its events, and build your member profile.</p>
              <ClubJoinButton clubId={club.id} className="mt-5 w-full" />
            </aside>
          </div>
        </section>

        <section className="mt-12">
          <div className="flex items-center justify-between gap-4">
            <h2 className="text-2xl font-semibold tracking-tight">Upcoming events from {club.name}</h2>
            <Link href="/explore" className="text-sm font-semibold text-primary">View all</Link>
          </div>
          {clubEvents.length > 0 ? (
            <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {clubEvents.map((event) => <ClubEventCard key={event.id} event={event} />)}
            </div>
          ) : (
            <div className="mt-5 rounded-lg border border-dashed border-border p-8 text-sm text-muted-foreground">No public events are attached to this club yet.</div>
          )}
        </section>
      </main>
      <SiteFooter />
    </>
  )
}

function ClubEventCard({ event }: { event: ClubEventSummary }) {
  return (
    <Link href={`/explore/${event.id}`} className="block rounded-lg border border-border bg-card p-4 transition-colors hover:border-primary/60">
      <p className="text-xs font-semibold uppercase tracking-wide text-primary">{event.event_type}</p>
      <h3 className="mt-2 text-lg font-semibold tracking-tight">{event.title}</h3>
      <p className="mt-2 text-sm text-muted-foreground">{new Date(event.starts_at).toLocaleDateString()} - {event.city || "Location TBA"}</p>
      <p className="mt-4 text-sm font-semibold">{formatEventPrice(Number(event.price_amount), event.currency)}</p>
    </Link>
  )
}

function Fact({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-background/50 p-4">
      <span className="mb-2 flex text-primary">{icon}</span>
      <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold">{value}</p>
    </div>
  )
}