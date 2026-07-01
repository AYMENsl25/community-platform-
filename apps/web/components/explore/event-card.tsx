"use client"

import Image from "next/image"
import Link from "next/link"
import { motion } from "motion/react"
import { Flame, MapPin, Users } from "lucide-react"
import { JoinButton } from "@/components/join-button"
import { formatEventPrice, type CommunityEvent } from "@/lib/events"

export function EventCard({ event }: { event: CommunityEvent }) {
  return (
    <motion.article
      layout
      initial={{ opacity: 0, scale: 0.96, y: 24 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.96, y: -12 }}
      transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
      className="group relative flex flex-col overflow-hidden rounded-3xl border border-border bg-card"
    >
      <Link
        href={`/explore/${event.id}`}
        className="relative aspect-[16/10] overflow-hidden focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <Image
          src={event.image || "/placeholder.svg"}
          alt={event.title}
          fill
          sizes="(min-width: 1024px) 33vw, (min-width: 640px) 50vw, 100vw"
          className="object-cover transition-transform duration-700 ease-[cubic-bezier(0.22,1,0.36,1)] group-hover:scale-105"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-card via-card/10 to-transparent" />

        <div className="absolute left-4 top-4 flex items-center gap-2">
          <span className="rounded-full border border-border bg-background/70 px-3 py-1 text-xs font-medium backdrop-blur">
            {event.category}
          </span>
          {event.trending && (
            <span className="inline-flex items-center gap-1 rounded-full bg-primary px-2.5 py-1 text-xs font-semibold text-primary-foreground">
              <Flame className="size-3" aria-hidden="true" />
              Trending
            </span>
          )}
        </div>

        <span className="absolute right-4 top-4 rounded-full bg-background/70 px-3 py-1 text-xs font-medium backdrop-blur">
          {formatEventPrice(event.price, event.currency)}
        </span>
      </Link>

      <div className="flex flex-1 flex-col p-5">
        <p className="text-xs font-medium text-primary">{event.date}</p>
        <h3 className="mt-1.5 text-lg font-semibold tracking-tight">
          <Link
            href={`/explore/${event.id}`}
            className="transition-colors hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {event.title}
          </Link>
        </h3>
        <p className="mt-1.5 text-pretty text-sm leading-relaxed text-muted-foreground">{event.blurb}</p>

        <div className="mt-4 flex items-center gap-4 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1.5">
            <MapPin className="size-3.5" aria-hidden="true" />
            {event.location}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <Users className="size-3.5" aria-hidden="true" />
            {event.attendees} going
          </span>
        </div>

        <div className="mt-5 flex items-center justify-between border-t border-border pt-4">
          <span className="text-xs font-medium text-muted-foreground">
            <span className="text-foreground">{event.spots}</span> spots left
          </span>
          <JoinButton eventId={event.id} eventTitle={event.title} price={event.price} currency={event.currency} />
        </div>
      </div>
    </motion.article>
  )
}
