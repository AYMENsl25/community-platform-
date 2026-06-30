"use client"

import { AnimatePresence, motion } from "motion/react"
import { Check, Plus } from "lucide-react"
import { useState } from "react"
import { apiPost } from "@/lib/api"
import { cn } from "@/lib/utils"

const PARTICLES = Array.from({ length: 8 })

type RegistrationState = {
  status: string
  waitlist_position: number | null
}

export function JoinButton({ eventId, className }: { eventId?: string; className?: string }) {
  const [state, setState] = useState<"idle" | "joining" | "joined" | "error">("idle")

  async function handleClick() {
    if (state !== "idle") {
      setState("idle")
      return
    }

    setState("joining")
    if (!eventId) {
      window.setTimeout(() => setState("joined"), 550)
      return
    }

    try {
      await apiPost<RegistrationState>(`/events/${encodeURIComponent(eventId)}/register`, {
        headers: {
          "X-Communiti-User-Email": "member@communiti.local",
        },
      })
      setState("joined")
    } catch (error) {
      console.error("Event registration failed.", error)
      setState("error")
    }
  }

  const joined = state === "joined"
  const error = state === "error"

  return (
    <motion.button
      type="button"
      onClick={handleClick}
      whileTap={{ scale: 0.94 }}
      aria-label={joined ? "Leave experience" : "Join experience"}
      className={cn(
        "relative inline-flex items-center justify-center gap-1.5 overflow-hidden rounded-full px-5 py-2.5 text-sm font-semibold tracking-tight transition-colors duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        joined
          ? "bg-primary text-primary-foreground"
          : error
            ? "bg-destructive text-destructive-foreground"
            : "bg-foreground text-background",
        className,
      )}
    >
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
          ) : error ? (
            <motion.span
              key="error"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25 }}
              className="inline-flex items-center gap-1.5"
            >
              Try again
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
