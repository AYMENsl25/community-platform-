"use client"

import { motion } from "motion/react"
import { ArrowRight } from "lucide-react"
import { MagneticButton } from "@/components/magnetic-button"
import { Reveal } from "@/components/reveal"

const words =
  "We believe belonging shouldn't be left to chance. So we're running an experiment: what happens when a city full of strangers finally finds each other?".split(
    " ",
  )

export function ManifestoCta() {
  return (
    <>
      <section id="manifesto" className="px-4 py-28 md:py-36">
        <div className="mx-auto max-w-4xl text-center">
          <p className="mb-8 text-sm font-medium tracking-wide text-primary">THE MANIFESTO</p>
          <p className="flex flex-wrap justify-center gap-x-2 text-balance text-2xl font-medium leading-snug tracking-tight sm:text-3xl md:text-4xl">
            {words.map((word, i) => (
              <motion.span
                key={`${word}-${i}`}
                initial={{ opacity: 0.15 }}
                whileInView={{ opacity: 1 }}
                viewport={{ once: true, margin: "-20% 0px -20% 0px" }}
                transition={{ duration: 0.4, delay: i * 0.02 }}
                className="inline-block"
              >
                {word}
              </motion.span>
            ))}
          </p>
        </div>
      </section>

      <section className="px-4 pb-28">
        <Reveal className="mx-auto max-w-5xl">
          <div className="relative overflow-hidden rounded-[2rem] border border-border bg-card px-6 py-16 text-center md:py-20">
            <div
              aria-hidden="true"
              className="pointer-events-none absolute left-1/2 top-1/2 -z-0 h-[360px] w-[360px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary/20 blur-[110px]"
            />
            <h2 className="relative text-balance text-3xl font-semibold tracking-tight sm:text-4xl md:text-5xl">
              Your people are already out there.
            </h2>
            <p className="relative mx-auto mt-4 max-w-md text-pretty text-sm leading-relaxed text-muted-foreground sm:text-base">
              Join thousands of curious humans turning interests into real-world experiences.
            </p>
            <div className="relative mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <MagneticButton href="/explore" aria-label="Join the experiment">
                Join the experiment
                <ArrowRight className="size-4 transition-transform duration-300 group-hover:translate-x-1" />
              </MagneticButton>
              <MagneticButton href="/explore" variant="outline" aria-label="Browse experiences">
                Browse experiences
              </MagneticButton>
            </div>
          </div>
        </Reveal>
      </section>
    </>
  )
}
