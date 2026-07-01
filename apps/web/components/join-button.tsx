"use client"

import { useAuth } from "@clerk/nextjs"
import { AnimatePresence, motion } from "motion/react"
import { Check, CreditCard, Plus, ShieldCheck } from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import { apiPost, bearerHeaders } from "@/lib/api"
import { formatEventPrice } from "@/lib/events"
import { queuePendingRegistration, removePendingRegistration, syncPendingRegistrations } from "@/lib/pending-registrations"
import { createEventCheckout } from "@/lib/payments"
import { cn } from "@/lib/utils"

const PARTICLES = Array.from({ length: 8 })

type RegistrationState = {
  status: string
  waitlist_position: number | null
}

type JoinState = "idle" | "payment" | "registering" | "registered" | "canceling" | "error"
type SyncState = "idle" | "synced" | "local" | "failed"

export function JoinButton({
  eventId,
  eventTitle = "this event",
  price = 0,
  currency = "USD",
  paymentLayout = "popover",
  className,
}: {
  eventId?: string
  eventTitle?: string
  price?: number
  currency?: string
  paymentLayout?: "popover" | "panel"
  className?: string
}) {
  const { isLoaded, isSignedIn, getToken } = useAuth()
  const [state, setState] = useState<JoinState>("idle")
  const [syncState, setSyncState] = useState<SyncState>("idle")
  const isPaid = price > 0
  const priceLabel = formatEventPrice(price, currency)

  const saveLocalRegistration = useCallback(() => {
    if (!eventId) return
    window.localStorage.setItem(registrationStorageKey(eventId), "registered")
    window.localStorage.setItem(registrationSyncStorageKey(eventId), isSignedIn ? "pending" : "guest")
    queuePendingRegistration({ eventId, eventTitle })
  }, [eventId, eventTitle, isSignedIn])

  const completeRegistration = useCallback(async () => {
    if (!eventId) {
      window.setTimeout(() => setState("registered"), 550)
      return
    }

    setState("registering")
    saveLocalRegistration()
    setSyncState("local")
    window.setTimeout(() => setState("registered"), 250)

    if (!isSignedIn) {
      return
    }

    try {
      const token = await getToken()
      await apiPost<RegistrationState>(`/events/${encodeURIComponent(eventId)}/register`, {
        headers: bearerHeaders(token),
      })
      window.localStorage.setItem(registrationStorageKey(eventId), "registered")
      window.localStorage.removeItem(registrationSyncStorageKey(eventId))
      removePendingRegistration(eventId)
      setSyncState("synced")
    } catch (error) {
      console.warn("Event registration saved locally because API sync failed.", error)
      setSyncState("local")
    }
  }, [eventId, getToken, isSignedIn, saveLocalRegistration])

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return

    let active = true
    const syncTimer = window.setTimeout(() => {
      void syncPendingRegistrations(getToken).then((synced) => {
        if (!active || !eventId || !synced.includes(eventId)) return
        window.localStorage.removeItem(registrationSyncStorageKey(eventId))
        setSyncState("synced")
      })
    }, 500)

    return () => {
      active = false
      window.clearTimeout(syncTimer)
    }
  }, [eventId, getToken, isLoaded, isSignedIn])

  useEffect(() => {
    if (!eventId) return

    const syncTimer = window.setTimeout(() => {
      if (window.localStorage.getItem(registrationStorageKey(eventId)) === "registered") {
        setState("registered")
        setSyncState(window.localStorage.getItem(registrationSyncStorageKey(eventId)) ? "local" : "synced")
      }
    }, 0)

    return () => window.clearTimeout(syncTimer)
  }, [eventId])

  async function handleClick() {
    if (state === "registering" || state === "canceling" || !isLoaded) return

    if (state === "registered") {
      if (!eventId) {
        setState("idle")
        return
      }

      setState("canceling")
      window.localStorage.removeItem(registrationStorageKey(eventId))
      window.localStorage.removeItem(registrationSyncStorageKey(eventId))
      removePendingRegistration(eventId)
      setSyncState("idle")
      window.setTimeout(() => setState("idle"), 200)

      if (!isSignedIn) {
        return
      }

      try {
        const token = await getToken()
        await apiPost<RegistrationState>(`/events/${encodeURIComponent(eventId)}/cancel-registration`, {
          headers: bearerHeaders(token),
        })
      } catch (error) {
        console.warn("Event registration cancellation could not sync with the API.", error)
        setSyncState("failed")
      }
      return
    }

    if (isPaid) {
      setState("payment")
      return
    }

    await completeRegistration()
  }

  async function handlePaymentConfirm() {
    if (state === "registering") return
    if (isPaid && eventId && isSignedIn) {
      setState("registering")
      try {
        const token = await getToken()
        const checkout = await createEventCheckout({
          eventId,
          token,
          returnPath: window.location.pathname,
        })

        if (checkout.checkout_url) {
          queuePendingRegistration({ eventId, eventTitle })
          window.location.assign(checkout.checkout_url)
          return
        }
      } catch (error) {
        console.warn("Payment checkout unavailable; falling back to local registration.", error)
      }
    }

    await completeRegistration()
  }

  const registered = state === "registered"
  const payment = state === "payment"
  const busy = state === "registering" || state === "canceling" || !isLoaded
  const error = state === "error"
  const helperText =
    registered && syncState === "local"
      ? isSignedIn
        ? "Registered here. We will sync when the API is online."
        : "Registered on this device. Sign in later to sync your account."
      : syncState === "failed"
        ? "Updated here, but the API could not be reached."
        : null

  return (
    <span className={cn("relative inline-flex flex-col", paymentLayout === "panel" && "w-full")}>
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
              : payment
                ? "bg-primary text-primary-foreground"
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
            ) : payment ? (
              <motion.span
                key="payment"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.25 }}
                className="inline-flex items-center gap-1.5"
              >
                <CreditCard className="size-4" aria-hidden="true" />
                Payment needed
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

      {helperText && <span className="mt-2 text-center text-[11px] leading-4 text-muted-foreground">{helperText}</span>}

      <AnimatePresence>
        {payment && (
          <motion.span
            initial={{ opacity: 0, y: -4, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.98 }}
            transition={{ duration: 0.2 }}
            className={cn(
              "z-20 mt-2 rounded-2xl border border-border bg-card p-3 text-left text-xs shadow-xl",
              paymentLayout === "popover" && "absolute right-0 top-full w-72",
            )}
          >
            <span className="flex items-start gap-2">
              <ShieldCheck className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
              <span>
                <span className="block font-semibold text-foreground">Finish registration with payment</span>
                <span className="mt-1 block leading-5 text-muted-foreground">
                  {eventTitle} costs {priceLabel}. You can keep reading the details before paying.
                </span>
              </span>
            </span>
            <span className="mt-3 flex gap-2">
              <button
                type="button"
                onClick={handlePaymentConfirm}
                className="inline-flex flex-1 items-center justify-center rounded-full bg-primary px-3 py-2 font-semibold text-primary-foreground"
              >
                Pay {priceLabel}
              </button>
              <button
                type="button"
                onClick={() => setState("idle")}
                className="inline-flex items-center justify-center rounded-full border border-border px-3 py-2 font-semibold text-foreground"
              >
                Later
              </button>
            </span>
          </motion.span>
        )}
      </AnimatePresence>
    </span>
  )
}

function registrationStorageKey(eventId: string): string {
  return `communiti:registered-event:${eventId}`
}

function registrationSyncStorageKey(eventId: string): string {
  return `communiti:registered-event-sync:${eventId}`
}
