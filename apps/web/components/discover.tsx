"use client"

import { Brain, Radio, Wand2, ShieldCheck } from "lucide-react"
import { Reveal } from "@/components/reveal"

const features = [
  {
    icon: Brain,
    title: "AI that understands taste",
    body: "Semantic recommendations from day one. We learn what you love, not just what you click.",
  },
  {
    icon: Radio,
    title: "Live capacity, real-time",
    body: "See spots fill in real time. Join waitlists that actually move when someone drops.",
  },
  {
    icon: Wand2,
    title: "Plan with an assistant",
    body: "Ask for a weekend trip for ten and get a bookable itinerary, built in seconds.",
  },
  {
    icon: ShieldCheck,
    title: "Communities that feel safe",
    body: "Smart moderation and verified organizers keep every gathering welcoming.",
  },
]

export function Discover() {
  return (
    <section id="discover" className="px-4 py-24 md:py-32">
      <div className="mx-auto max-w-6xl">
        <div className="grid gap-12 md:grid-cols-[1fr_1.4fr] md:gap-16">
          <Reveal direction="right" className="md:sticky md:top-28 md:self-start">
            <p className="text-sm font-medium tracking-wide text-primary">WHY COMMUNITI</p>
            <h2 className="mt-3 text-balance text-3xl font-semibold tracking-tight sm:text-4xl md:text-5xl">
              Built for connection, not for the scroll.
            </h2>
            <p className="mt-5 max-w-md text-pretty text-sm leading-relaxed text-muted-foreground">
              Most platforms keep you online. COMMUNITI is designed to get you offline and into a
              room with people who get you.
            </p>
          </Reveal>

          <div className="grid gap-5 sm:grid-cols-2">
            {features.map((feature, i) => (
              <Reveal key={feature.title} delay={i * 0.1}>
                <article className="group h-full rounded-3xl border border-border bg-card p-7 transition-transform duration-300 hover:-translate-y-1">
                  <span className="flex size-11 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                    <feature.icon className="size-5" aria-hidden="true" />
                  </span>
                  <h3 className="mt-6 text-lg font-semibold tracking-tight">{feature.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{feature.body}</p>
                </article>
              </Reveal>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
