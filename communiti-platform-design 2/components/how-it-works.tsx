"use client"

import { Compass, Sparkles, Users } from "lucide-react"
import { Reveal } from "@/components/reveal"

const steps = [
  {
    icon: Compass,
    no: "01",
    title: "Tell us what moves you",
    body: "Pick a few interests. Our AI builds a sense of who you are — no endless quizzes, no noise.",
  },
  {
    icon: Sparkles,
    no: "02",
    title: "Get matched, not flooded",
    body: "Semantic recommendations surface the handful of clubs and experiences that actually fit you.",
  },
  {
    icon: Users,
    no: "03",
    title: "Show up in real life",
    body: "Reserve a spot, join the waitlist, meet your people. The experiment happens offline.",
  },
]

export function HowItWorks() {
  return (
    <section id="how" className="px-4 py-24 md:py-32">
      <div className="mx-auto max-w-5xl">
        <Reveal>
          <p className="text-sm font-medium tracking-wide text-primary">THE EXPERIMENT</p>
          <h2 className="mt-3 max-w-2xl text-balance text-3xl font-semibold tracking-tight sm:text-4xl md:text-5xl">
            Three steps from stranger to belonging.
          </h2>
        </Reveal>

        <div className="mt-14 grid gap-6 md:grid-cols-3">
          {steps.map((step, i) => (
            <Reveal key={step.no} delay={i * 0.12}>
              <article className="group h-full rounded-3xl border border-border bg-card p-7 transition-colors duration-300 hover:border-primary/50">
                <div className="flex items-center justify-between">
                  <span className="flex size-11 items-center justify-center rounded-2xl bg-primary/10 text-primary transition-colors duration-300 group-hover:bg-primary group-hover:text-primary-foreground">
                    <step.icon className="size-5" aria-hidden="true" />
                  </span>
                  <span className="font-mono text-sm text-muted-foreground">{step.no}</span>
                </div>
                <h3 className="mt-6 text-lg font-semibold tracking-tight">{step.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{step.body}</p>
              </article>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}
