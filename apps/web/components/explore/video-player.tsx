"use client"

import Image from "next/image"
import { AnimatePresence, motion } from "motion/react"
import { Play, Box, Loader2 } from "lucide-react"
import { useState } from "react"
import { cn } from "@/lib/utils"

export function VideoPlayer({
  poster,
  title,
  badge = "3D Experiment Reel",
}: {
  poster: string
  title: string
  badge?: string
}) {
  const [state, setState] = useState<"idle" | "loading" | "playing">("idle")

  function play() {
    if (state !== "idle") return
    setState("loading")
    window.setTimeout(() => setState("playing"), 1100)
  }

  return (
    <div className="relative aspect-video w-full overflow-hidden rounded-3xl border border-border bg-card">
      <Image
        src={poster || "/placeholder.svg"}
        alt={`${title} preview`}
        fill
        sizes="(min-width: 1024px) 66vw, 100vw"
        className={cn(
          "object-cover transition-all duration-700",
          state === "playing" ? "scale-105 blur-0" : "scale-100",
        )}
      />
      <div className="absolute inset-0 bg-gradient-to-t from-background/80 via-background/20 to-background/30" />

      <span className="absolute left-4 top-4 inline-flex items-center gap-1.5 rounded-full border border-border bg-background/70 px-3 py-1.5 text-xs font-medium backdrop-blur">
        <Box className="size-3.5 text-primary" aria-hidden="true" />
        {badge}
      </span>

      <button
        type="button"
        onClick={play}
        aria-label={`Play ${title}`}
        className="absolute inset-0 flex items-center justify-center focus-visible:outline-none"
      >
        <AnimatePresence mode="wait">
          {state !== "playing" && (
            <motion.span
              key={state}
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.8, opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="relative grid size-20 place-items-center rounded-full bg-primary text-primary-foreground shadow-lg"
            >
              {/* pulsing ring */}
              <motion.span
                className="absolute inset-0 rounded-full bg-primary/40"
                animate={{ scale: [1, 1.6], opacity: [0.6, 0] }}
                transition={{ duration: 1.6, repeat: Number.POSITIVE_INFINITY, ease: "easeOut" }}
              />
              {state === "loading" ? (
                <Loader2 className="size-7 animate-spin" aria-hidden="true" />
              ) : (
                <Play className="ml-1 size-7 fill-current" aria-hidden="true" />
              )}
            </motion.span>
          )}
        </AnimatePresence>
      </button>

      {/* fake playback bar */}
      <AnimatePresence>
        {state === "playing" && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="absolute inset-x-4 bottom-4 flex items-center gap-3 rounded-full border border-border bg-background/70 px-4 py-2.5 backdrop-blur"
          >
            <span className="text-xs font-medium tabular-nums text-muted-foreground">0:00</span>
            <div className="relative h-1 flex-1 overflow-hidden rounded-full bg-muted">
              <motion.div
                className="absolute inset-y-0 left-0 rounded-full bg-primary"
                initial={{ width: "0%" }}
                animate={{ width: "100%" }}
                transition={{ duration: 30, ease: "linear" }}
              />
            </div>
            <span className="text-xs font-medium tabular-nums text-muted-foreground">2:30</span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
