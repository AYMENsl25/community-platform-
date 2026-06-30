"use client"

import Image from "next/image"
import Link from "next/link"
import dynamic from "next/dynamic"
import {
  ArrowLeft,
  CalendarDays,
  Clock,
  MapPin,
  Users,
  Check,
  Sparkles,
  Backpack,
  Navigation,
} from "lucide-react"
import { Reveal } from "@/components/reveal"
import { JoinButton } from "@/components/join-button"
import { VideoPlayer } from "@/components/explore/video-player"
import { OrganizerPanel } from "@/components/explore/organizer-panel"
import { EventCard } from "@/components/explore/event-card"
import type { CommunityEvent, Organizer } from "@/lib/events"

const EventMap = dynamic(() => import("@/components/explore/event-map"), {
  ssr: false,
  loading: () => <div className="size-full animate-pulse bg-muted" />,
})

export function EventDetail({
  event,
  organizer,
  more,
}: {
  event: CommunityEvent
  organizer: Organizer
  more: CommunityEvent[]
}) {
  return (
    <main className="mx-auto max-w-6xl px-4 pb-24 pt-24 sm:px-6">
      <Link
        href="/explore"
        className="inline-flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Back to experiences
      </Link>

      {/* hero */}
      <Reveal direction="up">
        <div className="relative mt-6 aspect-[16/9] w-full overflow-hidden rounded-3xl border border-border sm:aspect-[21/9]">
          <Image
            src={event.image || "/placeholder.svg"}
            alt={event.title}
            fill
            priority
            sizes="100vw"
            className="object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-background via-background/30 to-transparent" />
          <div className="absolute inset-x-0 bottom-0 p-6 sm:p-8">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-border bg-background/70 px-3 py-1 text-xs font-medium backdrop-blur">
                {event.category}
              </span>
              <span className="rounded-full bg-background/70 px-3 py-1 text-xs font-medium backdrop-blur">
                {event.price === 0 ? "Free" : `$${event.price}`}
              </span>
            </div>
            <h1 className="mt-3 text-balance text-3xl font-semibold tracking-tight sm:text-5xl">{event.title}</h1>
            <p className="mt-2 max-w-2xl text-pretty text-sm text-muted-foreground sm:text-base">{event.blurb}</p>
          </div>
        </div>
      </Reveal>

      <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_360px]">
        {/* left column */}
        <div className="flex flex-col gap-8">
          {/* quick facts */}
          <Reveal direction="up">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Fact icon={<CalendarDays className="size-4" />} label="When" value={event.date} />
              <Fact icon={<Clock className="size-4" />} label="Duration" value={event.duration} />
              <Fact icon={<Users className="size-4" />} label="Going" value={`${event.attendees}`} />
              <Fact icon={<MapPin className="size-4" />} label="Where" value={event.location} />
            </div>
          </Reveal>

          {/* 3D experiment video */}
          <Reveal direction="up">
            <section>
              <SectionTitle icon={<Sparkles className="size-4" />}>See the experiment</SectionTitle>
              <div className="mt-3">
                <VideoPlayer poster={event.image} title={event.title} />
              </div>
            </section>
          </Reveal>

          {/* about */}
          <Reveal direction="up">
            <section>
              <SectionTitle>About this experience</SectionTitle>
              <p className="mt-3 text-pretty leading-relaxed text-muted-foreground">{event.about}</p>

              <div className="mt-5 grid gap-6 sm:grid-cols-2">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Highlights</p>
                  <ul className="mt-3 space-y-2">
                    {event.highlights.map((h) => (
                      <li key={h} className="flex items-center gap-2 text-sm">
                        <Check className="size-4 shrink-0 text-primary" aria-hidden="true" />
                        {h}
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                    <Backpack className="size-3.5" aria-hidden="true" />
                    What to bring
                  </p>
                  <ul className="mt-3 space-y-2">
                    {event.bring.map((b) => (
                      <li key={b} className="flex items-center gap-2 text-sm text-muted-foreground">
                        <span className="size-1.5 rounded-full bg-primary" aria-hidden="true" />
                        {b}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </section>
          </Reveal>

          {/* map */}
          <Reveal direction="up">
            <section>
              <SectionTitle icon={<MapPin className="size-4" />}>Where you&apos;ll meet</SectionTitle>
              <div className="mt-3 overflow-hidden rounded-3xl border border-border">
                <div className="h-72 w-full">
                  <EventMap lat={event.lat} lng={event.lng} label={event.location} />
                </div>
                <div className="flex items-center justify-between gap-4 border-t border-border bg-card p-4">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{event.location}</p>
                    <p className="truncate text-xs text-muted-foreground">{event.address}</p>
                  </div>
                  <a
                    href={`https://www.openstreetmap.org/?mlat=${event.lat}&mlon=${event.lng}#map=15/${event.lat}/${event.lng}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-border px-4 py-2 text-xs font-medium transition-colors hover:border-primary/50 hover:text-primary"
                  >
                    <Navigation className="size-3.5" aria-hidden="true" />
                    Directions
                  </a>
                </div>
              </div>
            </section>
          </Reveal>
        </div>

        {/* right column */}
        <div className="flex flex-col gap-6 lg:sticky lg:top-24 lg:self-start">
          <Reveal direction="up">
            <div className="rounded-3xl border border-border bg-card p-6">
              <div className="flex items-baseline justify-between">
                <p className="text-2xl font-semibold tracking-tight">
                  {event.price === 0 ? "Free" : `$${event.price}`}
                </p>
                <p className="text-xs font-medium text-muted-foreground">
                  <span className="text-foreground">{event.spots}</span> spots left
                </p>
              </div>
              <div className="mt-4">
                <JoinButton eventId={event.id} className="w-full py-3" />
              </div>
              <p className="mt-3 text-center text-xs text-muted-foreground">
                {event.attendees} people are going. You can leave anytime.
              </p>
            </div>
          </Reveal>

          <Reveal direction="up">
            <OrganizerPanel organizer={organizer} />
          </Reveal>
        </div>
      </div>

      {/* more from organizer */}
      {more.length > 0 && (
        <Reveal direction="up">
          <section className="mt-16">
            <h2 className="text-xl font-semibold tracking-tight sm:text-2xl">More from {organizer.name}</h2>
            <div className="mt-5 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {more.map((e) => (
                <EventCard key={e.id} event={e} />
              ))}
            </div>
          </section>
        </Reveal>
      )}
    </main>
  )
}

function Fact({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-border bg-card p-4">
      <span className="mb-2 flex text-primary">{icon}</span>
      <p className="text-[11px] uppercase tracking-widest text-muted-foreground">{label}</p>
      <p className="mt-0.5 text-sm font-medium">{value}</p>
    </div>
  )
}

function SectionTitle({ icon, children }: { icon?: React.ReactNode; children: React.ReactNode }) {
  return (
    <h2 className="flex items-center gap-2 text-xl font-semibold tracking-tight sm:text-2xl">
      {icon && <span className="text-primary">{icon}</span>}
      {children}
    </h2>
  )
}
