"use client"

import Image from "next/image"
import { AnimatePresence, motion } from "motion/react"
import { AtSign, BadgeCheck, CalendarDays, Globe, Play, Star, Users, Video } from "lucide-react"
import { useState } from "react"
import type { Organizer } from "@/lib/events"

export function OrganizerPanel({ organizer }: { organizer: Organizer }) {
  const [active, setActive] = useState<number | null>(null)

  return (
    <div className="rounded-3xl border border-border bg-card p-6">
      <div className="flex items-start gap-4">
        <Image
          src={organizer.logo || "/placeholder.svg"}
          alt={organizer.name}
          width={56}
          height={56}
          className="size-14 rounded-2xl border border-border object-cover"
        />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <h3 className="truncate text-base font-semibold tracking-tight">{organizer.name}</h3>
            {organizer.verified && <BadgeCheck className="size-4 shrink-0 text-primary" aria-label="Verified" />}
          </div>
          <p className="text-sm text-muted-foreground">{organizer.handle}</p>
        </div>
      </div>

      <p className="mt-4 text-pretty text-sm leading-relaxed text-muted-foreground">{organizer.bio}</p>

      {/* stats */}
      <div className="mt-5 grid grid-cols-3 gap-3">
        <Stat icon={<Users className="size-4" />} value={formatCount(organizer.members)} label="members" />
        <Stat icon={<CalendarDays className="size-4" />} value={`${organizer.eventsHosted}`} label="hosted" />
        <Stat icon={<Star className="size-4" />} value={organizer.rating.toFixed(1)} label="rating" />
      </div>

      {/* socials */}
      <div className="mt-5 flex flex-wrap items-center gap-2">
        {organizer.socials.instagram && (
          <Social icon={<AtSign className="size-4" />} label={organizer.socials.instagram} />
        )}
        {organizer.socials.youtube && <Social icon={<Video className="size-4" />} label={organizer.socials.youtube} />}
        {organizer.socials.website && <Social icon={<Globe className="size-4" />} label={organizer.socials.website} />}
      </div>

      {/* previous work reel */}
      <div className="mt-6">
        <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Previous work</p>
        <div className="mt-3 grid grid-cols-2 gap-3">
          {organizer.reel.map((video, i) => (
            <button
              key={video.title}
              type="button"
              onClick={() => setActive(active === i ? null : i)}
              className="group relative aspect-video overflow-hidden rounded-2xl border border-border text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label={`Play ${video.title}`}
            >
              <Image
                src={video.poster || "/placeholder.svg"}
                alt={video.title}
                fill
                sizes="50vw"
                className="object-cover transition-transform duration-500 group-hover:scale-110"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-background/90 via-background/20 to-transparent" />

              <span className="absolute right-2 top-2 rounded-full bg-background/70 px-2 py-0.5 text-[10px] font-medium tabular-nums backdrop-blur">
                {video.duration}
              </span>

              <span className="absolute left-1/2 top-1/2 grid size-9 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full bg-primary/90 text-primary-foreground transition-transform duration-300 group-hover:scale-110">
                <AnimatePresence mode="wait">
                  {active === i ? (
                    <motion.span
                      key="bars"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="flex items-end gap-0.5"
                      aria-hidden="true"
                    >
                      {[0, 1, 2].map((b) => (
                        <motion.span
                          key={b}
                          className="w-0.5 rounded-full bg-current"
                          animate={{ height: [4, 12, 6, 14, 5] }}
                          transition={{
                            duration: 0.9,
                            repeat: Number.POSITIVE_INFINITY,
                            delay: b * 0.15,
                          }}
                        />
                      ))}
                    </motion.span>
                  ) : (
                    <Play key="play" className="ml-0.5 size-4 fill-current" aria-hidden="true" />
                  )}
                </AnimatePresence>
              </span>

              <span className="absolute inset-x-2 bottom-2 truncate text-xs font-medium text-foreground">
                {video.title}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

function Stat({ icon, value, label }: { icon: React.ReactNode; value: string; label: string }) {
  return (
    <div className="rounded-2xl border border-border bg-background/40 p-3 text-center">
      <span className="mx-auto mb-1 flex justify-center text-primary">{icon}</span>
      <p className="text-sm font-semibold tabular-nums">{value}</p>
      <p className="text-[11px] text-muted-foreground">{label}</p>
    </div>
  )
}

function Social({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-background/40 px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:border-primary/50 hover:text-foreground">
      {icon}
      {label}
    </span>
  )
}

function formatCount(n: number) {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : `${n}`
}
