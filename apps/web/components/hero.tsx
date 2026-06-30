"use client"

import { motion } from "motion/react"
import { ArrowRight, Sparkles } from "lucide-react"
import { MagneticButton } from "@/components/magnetic-button"

const headline = ["Find", "your", "people.", "Join", "the", "experiment."]

export function Hero() {
  return (
    <section id="top" className="relative overflow-hidden px-4 pt-36 pb-20 md:pt-44 md:pb-28">
      {/* soft cosmic glow, used sparingly as an accent */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute left-1/2 top-0 -z-10 h-[480px] w-[480px] -translate-x-1/2 rounded-full bg-primary/20 blur-[120px]"
      />

      <div className="mx-auto flex max-w-4xl flex-col items-center text-center">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="mb-8 inline-flex items-center gap-2 rounded-full border border-border bg-card/60 px-4 py-1.5 text-xs font-medium text-muted-foreground backdrop-blur"
        >
          <Sparkles className="size-3.5 text-primary" aria-hidden="true" />
          A living experiment in human connection
        </motion.div>

        <h1 className="text-balance text-4xl font-semibold leading-[1.05] tracking-tight sm:text-6xl md:text-7xl">
          {headline.map((word, i) => (
            <span key={`${word}-${i}`} className="inline-block overflow-hidden pb-1 align-bottom">
              <motion.span
                className="inline-block"
                initial={{ y: "100%" }}
                animate={{ y: 0 }}
                transition={{ duration: 0.7, delay: 0.15 + i * 0.08, ease: [0.22, 1, 0.36, 1] }}
              >
                {word === "experiment." ? (
                  <span className="text-primary">{word}</span>
                ) : (
                  word
                )}
                {i < headline.length - 1 && "\u00A0"}
              </motion.span>
            </span>
          ))}
        </h1>

        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.7 }}
          className="mt-7 max-w-xl text-pretty text-base leading-relaxed text-muted-foreground sm:text-lg"
        >
          COMMUNITI uses AI to connect curious humans with clubs, trips, and real-world
          experiences worth showing up for. Less scrolling. More belonging.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.85 }}
          className="mt-10 flex flex-col items-center gap-3 sm:flex-row"
        >
          <MagneticButton href="/explore" aria-label="Start exploring">
            Start exploring
            <ArrowRight className="size-4 transition-transform duration-300 group-hover:translate-x-1" />
          </MagneticButton>
          <MagneticButton href="/explore" variant="outline" aria-label="Browse experiences">
            Browse experiences
          </MagneticButton>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1, delay: 1.1 }}
          className="mt-14 flex items-center gap-8 text-center"
        >
          {[
            { value: "12.4k", label: "Curious members" },
            { value: "840+", label: "Live experiences" },
            { value: "63", label: "Cities exploring" },
          ].map((stat) => (
            <div key={stat.label}>
              <div className="text-2xl font-semibold tracking-tight sm:text-3xl">{stat.value}</div>
              <div className="mt-1 text-xs text-muted-foreground">{stat.label}</div>
            </div>
          ))}
        </motion.div>
      </div>
    </section>
  )
}
