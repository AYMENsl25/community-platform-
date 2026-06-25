"use client"

import { AnimatePresence, LayoutGroup, motion } from "motion/react"
import { Orbit, Search, SlidersHorizontal } from "lucide-react"
import Link from "next/link"
import { useMemo, useState } from "react"
import { EventCard } from "@/components/explore/event-card"
import { CATEGORIES, EVENTS, WHENS, type EventCategory, type EventWhen } from "@/lib/events"
import { cn } from "@/lib/utils"

type Sort = "Trending" | "Soonest" | "Fewest spots"
const SORTS: Sort[] = ["Trending", "Soonest", "Fewest spots"]

export function Explore() {
  const [query, setQuery] = useState("")
  const [category, setCategory] = useState<EventCategory | "All">("All")
  const [when, setWhen] = useState<EventWhen | "Any">("Any")
  const [freeOnly, setFreeOnly] = useState(false)
  const [sort, setSort] = useState<Sort>("Trending")

  const results = useMemo(() => {
    let list = EVENTS.filter((e) => {
      if (category !== "All" && e.category !== category) return false
      if (when !== "Any" && e.when !== when) return false
      if (freeOnly && e.price !== 0) return false
      if (query.trim()) {
        const q = query.toLowerCase()
        const hay = `${e.title} ${e.blurb} ${e.location} ${e.category}`.toLowerCase()
        if (!hay.includes(q)) return false
      }
      return true
    })

    list = [...list].sort((a, b) => {
      if (sort === "Trending") return Number(b.trending) - Number(a.trending) || b.attendees - a.attendees
      if (sort === "Soonest") {
        const order: Record<string, number> = { Today: 0, "This week": 1, "This weekend": 2 }
        return order[a.when] - order[b.when]
      }
      return a.spots - b.spots
    })
    return list
  }, [query, category, when, freeOnly, sort])

  return (
    <div className="min-h-dvh">
      {/* top bar */}
      <header className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4">
          <Link href="/" className="flex items-center gap-2">
            <Orbit className="size-5 text-primary" aria-hidden="true" />
            <span className="text-sm font-semibold tracking-tight">COMMUNITI</span>
          </Link>
          <div className="relative flex-1 max-w-md">
            <Search
              className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
              aria-hidden="true"
            />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search experiences, places, vibes…"
              aria-label="Search experiences"
              className="w-full rounded-full border border-border bg-card py-2.5 pl-10 pr-4 text-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-primary"
            />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 pb-24 pt-10">
        {/* hero copy */}
        <motion.div
          initial={{ opacity: 0, y: 20, filter: "blur(8px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        >
          <p className="text-sm font-medium tracking-wide text-primary">WELCOME TO THE EXPERIMENT</p>
          <h1 className="mt-3 text-balance text-3xl font-semibold tracking-tight sm:text-4xl md:text-5xl">
            Top experiences near you
          </h1>
          <p className="mt-3 max-w-xl text-pretty text-sm leading-relaxed text-muted-foreground sm:text-base">
            Filter by what you&apos;re into, when you&apos;re free, and how you like to spend. Then tap join — your
            people are waiting.
          </p>
        </motion.div>

        {/* filters */}
        <div className="mt-9 space-y-5">
          {/* categories */}
          <LayoutGroup id="cat">
            <div className="flex flex-wrap gap-2">
              <Chip active={category === "All"} onClick={() => setCategory("All")} layoutId="cat-pill">
                All
              </Chip>
              {CATEGORIES.map((c) => (
                <Chip key={c} active={category === c} onClick={() => setCategory(c)} layoutId="cat-pill">
                  {c}
                </Chip>
              ))}
            </div>
          </LayoutGroup>

          {/* when + free + sort */}
          <div className="flex flex-col gap-4 border-t border-border pt-5 sm:flex-row sm:items-center sm:justify-between">
            <LayoutGroup id="when">
              <div className="flex flex-wrap items-center gap-2">
                <span className="mr-1 inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                  <SlidersHorizontal className="size-3.5" aria-hidden="true" />
                  When
                </span>
                <Chip active={when === "Any"} onClick={() => setWhen("Any")} layoutId="when-pill" small>
                  Any time
                </Chip>
                {WHENS.map((w) => (
                  <Chip key={w} active={when === w} onClick={() => setWhen(w)} layoutId="when-pill" small>
                    {w}
                  </Chip>
                ))}
                <button
                  type="button"
                  onClick={() => setFreeOnly((v) => !v)}
                  aria-pressed={freeOnly}
                  className={cn(
                    "rounded-full border px-3.5 py-1.5 text-xs font-medium transition-colors",
                    freeOnly
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-border text-muted-foreground hover:text-foreground",
                  )}
                >
                  Free only
                </button>
              </div>
            </LayoutGroup>

            <label className="flex items-center gap-2 text-xs text-muted-foreground">
              Sort
              <select
                value={sort}
                onChange={(e) => setSort(e.target.value as Sort)}
                className="rounded-full border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground outline-none focus:border-primary"
              >
                {SORTS.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>

        {/* count */}
        <div className="mt-8 flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            <span className="font-semibold text-foreground">{results.length}</span>{" "}
            {results.length === 1 ? "experience" : "experiences"}
          </p>
        </div>

        {/* grid */}
        <LayoutGroup>
          <motion.div layout className="mt-6 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <AnimatePresence mode="popLayout">
              {results.map((event) => (
                <EventCard key={event.id} event={event} />
              ))}
            </AnimatePresence>
          </motion.div>
        </LayoutGroup>

        {results.length === 0 && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-16 rounded-3xl border border-dashed border-border py-20 text-center"
          >
            <p className="text-lg font-semibold">No experiences match that yet</p>
            <p className="mt-2 text-sm text-muted-foreground">Try clearing a filter or widening your search.</p>
          </motion.div>
        )}
      </main>
    </div>
  )
}

function Chip({
  children,
  active,
  onClick,
  layoutId,
  small,
}: {
  children: React.ReactNode
  active: boolean
  onClick: () => void
  layoutId: string
  small?: boolean
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "relative rounded-full font-medium transition-colors",
        small ? "px-3.5 py-1.5 text-xs" : "px-4 py-2 text-sm",
        active ? "text-primary-foreground" : "text-muted-foreground hover:text-foreground",
      )}
    >
      {active && (
        <motion.span
          layoutId={layoutId}
          className="absolute inset-0 -z-0 rounded-full bg-primary"
          transition={{ type: "spring", stiffness: 420, damping: 34 }}
        />
      )}
      <span className="relative z-10">{children}</span>
    </button>
  )
}
