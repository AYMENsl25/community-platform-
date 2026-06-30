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

type JoinState = "idle" | "registering" | "registered" | "canceling" | "error"

const DEV_MEMBER_HEADERS = {
  "X-Communiti-User-Email": "member@communiti.local",
}

export function JoinButton({ eventId, className }: { eventId?: string; className?: string }) {
  const [state, setState] = useState<JoinState>("idle")

  async function handleClick() {
    if (state === "registering" || state === "canceling") return

    if (state === "registered") {
      if (!eventId) {
        setState("idle")
        return
      }

      setState("canceling")
      try {
        await apiPost<RegistrationState>(`/events/${encodeURIComponent(eventId)}/cancel-registration`, {
          headers: DEV_MEMBER_HEADERS,
        })
        setState("idle")
      } catch (error) {
        console.error("Event registration cancellation failed.", error)
        setState("error")
      }
      return
    }

    setState("registering")
    if (!eventId) {
      window.setTimeout(() => setState("registered"), 550)
      return
    }

    try {
      await apiPost<RegistrationState>(`/events/${encodeURIComponent(eventId)}/register`, {
        headers: DEV_MEMBER_HEADERS,
      })
      setState("registered")
    } catch (error) {
      console.error("Event registration failed.", error)
      setState("error")
    }
  }

  const registered = state === "registered"
  const busy = state === "registering" || state === "canceling"
  const error = state === "error"

  return (
    <motion.button
      type="button"
      onClick={handleClick}
      disabled={busy}
      whileTap={{ scale: busy ? 1 : 0.94 }}
      aria-label={registered ? "Cancel event registration" : "Register for event"}
      className={cn(
        "relative inline-flex items-center justify-center gap-1.5 overflow-hidden rounded-full px-5 py-2.5 text-sm font-semibold tracking-tight transition-colors duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-wait disabled:opacity-80",
        registered
          ? "bg-primary text-primary-foreground"
          : error
            ? "bg-destructive text-destructive-foreground"
            : "bg-foreground text-background",
        className,
      )}
    >
      <AnimatePresence>
        {registered &&
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
          {registered ? (
            <motion.span
              key="registered"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25 }}
              className="inline-flex items-center gap-1.5"
            >
              <Check className="size-4" aria-hidden="true" />
              Registered
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
              key="register"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25 }}
              className="inline-flex items-center gap-1.5"
            >
              <Plus
                className={cn("size-4 transition-transform", state === "registering" && "rotate-90")}
                aria-hidden="true"
              />
              {state === "registering" ? "Registering" : state === "canceling" ? "Canceling" : "Register"}
            </motion.span>
          )}
        </AnimatePresence>
      </span>
    </motion.button>
  )
}
