"use client"

import { AnimatePresence, motion } from "motion/react"
import { Check, Plus } from "lucide-react"
import { useState } from "react"
import { cn } from "@/lib/utils"

const PARTICLES = Array.from({ length: 8 })

export function JoinButton({ className }: { className?: string }) {
  const [state, setState] = useState<"idle" | "joining" | "joined">("idle")

  function handleClick() {
    if (state !== "idle") {
      setState("idle")
      return
    }
    setState("joining")
    window.setTimeout(() => setState("joined"), 550)
  }

  const joined = state === "joined"

  return (
    <motion.button
      type="button"
      onClick={handleClick}
      whileTap={{ scale: 0.94 }}
      aria-label={joined ? "Leave experience" : "Join experience"}
      className={cn(
        "relative inline-flex items-center justify-center gap-1.5 overflow-hidden rounded-full px-5 py-2.5 text-sm font-semibold tracking-tight transition-colors duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        joined ? "bg-primary text-primary-foreground" : "bg-foreground text-background",
        className,
      )}
    >
      {/* success particle burst */}
      <AnimatePresence>
        {joined &&
          PARTICLES.map((_, i) => {
            const angle = (i / PARTICLES.length) * Math.PI * 2
            return (
              <motion.span
                key={i}
                className="pointer-events-none absolute left-1/2 top-1/2 size-1.5 rounded-full bg-primary"
                initial={{ x: 0, y: 0, opacity: 1, scale: 1 }}
                animate={{
                  x: Math.cos(angle) * 34,
                  y: Math.sin(angle) * 34,
                  opacity: 0,
                  scale: 0,
                }}
                transition={{ duration: 0.6, ease: "easeOut" }}
              />
            )
          })}
      </AnimatePresence>

      <span className="relative z-10 inline-flex items-center gap-1.5">
        <AnimatePresence mode="wait" initial={false}>
          {joined ? (
            <motion.span
              key="joined"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25 }}
              className="inline-flex items-center gap-1.5"
            >
              <Check className="size-4" aria-hidden="true" />
              Joined
            </motion.span>
          ) : (
            <motion.span
              key="join"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25 }}
              className="inline-flex items-center gap-1.5"
            >
              <Plus
                className={cn("size-4 transition-transform", state === "joining" && "rotate-90")}
                aria-hidden="true"
              />
              {state === "joining" ? "Joining" : "Join"}
            </motion.span>
          )}
        </AnimatePresence>
      </span>
    </motion.button>
  )
}
