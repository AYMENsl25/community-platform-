"use client"

import Image from "next/image"
import Link from "next/link"
import { ArrowUpRight, MapPin } from "lucide-react"
import { Reveal } from "@/components/reveal"

const experiences = [
  {
    title: "Sunrise Ridge Hike",
    location: "Marin Headlands",
    tag: "Outdoors",
    spots: "6 spots left",
    image: "/experiences/sunrise-hike.png",
  },
  {
    title: "Hands & Clay Pottery",
    location: "East Side Studio",
    tag: "Craft",
    spots: "Waitlist open",
    image: "/experiences/pottery-night.png",
  },
  {
    title: "Strangers Supper Club",
    location: "Rooftop, Downtown",
    tag: "Social",
    spots: "12 spots left",
    image: "/experiences/supper-club.png",
  },
]

export function Experiences() {
  return (
    <section id="experiences" className="px-4 py-24 md:py-32">
      <div className="mx-auto max-w-6xl">
        <Reveal className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-medium tracking-wide text-primary">HAPPENING NOW</p>
            <h2 className="mt-3 max-w-xl text-balance text-3xl font-semibold tracking-tight sm:text-4xl md:text-5xl">
              Real experiences, picked for real people.
            </h2>
          </div>
          <p className="max-w-sm text-pretty text-sm leading-relaxed text-muted-foreground">
            Every card is a door into a new community. No algorithms optimizing for your attention —
            just for your weekend.
          </p>
        </Reveal>

        <div className="mt-14 grid gap-6 md:grid-cols-3">
          {experiences.map((exp, i) => (
            <Reveal key={exp.title} direction="up" delay={i * 0.1}>
              <Link
                href="/explore"
                aria-label={`Explore ${exp.title}`}
                className="group relative block overflow-hidden rounded-3xl border border-border bg-card"
              >
                <div className="relative aspect-[4/5] overflow-hidden">
                  <Image
                    src={exp.image || "/placeholder.svg"}
                    alt={exp.title}
                    fill
                    sizes="(min-width: 768px) 33vw, 100vw"
                    className="object-cover transition-transform duration-700 ease-[cubic-bezier(0.22,1,0.36,1)] group-hover:scale-105"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-background via-background/20 to-transparent" />
                  <span className="absolute left-4 top-4 rounded-full border border-border bg-background/70 px-3 py-1 text-xs font-medium backdrop-blur">
                    {exp.tag}
                  </span>
                </div>

                <div className="absolute inset-x-0 bottom-0 p-6">
                  <h3 className="text-lg font-semibold tracking-tight">{exp.title}</h3>
                  <div className="mt-1.5 flex items-center gap-1.5 text-sm text-muted-foreground">
                    <MapPin className="size-3.5" aria-hidden="true" />
                    {exp.location}
                  </div>

                  <div className="mt-4 flex translate-y-2 items-center justify-between opacity-0 transition-all duration-500 group-hover:translate-y-0 group-hover:opacity-100">
                    <span className="text-xs font-medium text-primary">{exp.spots}</span>
                    <span className="flex size-9 items-center justify-center rounded-full bg-primary text-primary-foreground">
                      <ArrowUpRight className="size-4" aria-hidden="true" />
                    </span>
                  </div>
                </div>
              </Link>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}
