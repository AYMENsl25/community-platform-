"use client"

import { useAuth, useClerk } from "@clerk/nextjs"
import { Check, Loader2, LogIn, UserRoundPlus } from "lucide-react"
import { useEffect, useState } from "react"
import { apiPost, bearerHeaders } from "@/lib/api"
import { cn } from "@/lib/utils"

type JoinState = "idle" | "joining" | "joined" | "leaving" | "error"

export function ClubJoinButton({ clubId, className }: { clubId: string; className?: string }) {
  const { isLoaded, isSignedIn, getToken } = useAuth()
  const { redirectToSignIn } = useClerk()
  const [state, setState] = useState<JoinState>("idle")

  useEffect(() => {
    const syncTimer = window.setTimeout(() => {
      if (window.localStorage.getItem(clubStorageKey(clubId)) === "joined") {
        setState("joined")
      }
    }, 0)

    return () => window.clearTimeout(syncTimer)
  }, [clubId])

  async function handleClick() {
    if (!isLoaded || state === "joining" || state === "leaving") return

    if (!isSignedIn) {
      await redirectToSignIn({ signInForceRedirectUrl: window.location.href })
      return
    }

    if (state === "joined") {
      setState("leaving")
      try {
        const token = await getToken()
        await apiPost(`/clubs/${encodeURIComponent(clubId)}/leave`, {
          headers: bearerHeaders(token),
        })
        window.localStorage.removeItem(clubStorageKey(clubId))
        setState("idle")
      } catch (error) {
        console.error("Club leave failed.", error)
        setState("error")
      }
      return
    }

    setState("joining")
    try {
      const token = await getToken()
      await apiPost(`/clubs/${encodeURIComponent(clubId)}/join`, {
        headers: bearerHeaders(token),
      })
      window.localStorage.setItem(clubStorageKey(clubId), "joined")
      setState("joined")
    } catch (error) {
      console.error("Club join failed.", error)
      setState("error")
    }
  }

  const joined = state === "joined"
  const busy = state === "joining" || state === "leaving" || !isLoaded
  const signedOut = isLoaded && !isSignedIn

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={busy}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-full px-5 py-2.5 text-sm font-semibold transition-colors disabled:cursor-wait disabled:opacity-70",
        joined ? "bg-primary text-primary-foreground" : "bg-foreground text-background",
        state === "error" && "bg-destructive text-destructive-foreground",
        className,
      )}
    >
      {busy ? (
        <Loader2 className="size-4 animate-spin" aria-hidden="true" />
      ) : joined ? (
        <Check className="size-4" aria-hidden="true" />
      ) : signedOut ? (
        <LogIn className="size-4" aria-hidden="true" />
      ) : (
        <UserRoundPlus className="size-4" aria-hidden="true" />
      )}
      {state === "joining"
        ? "Joining"
        : state === "leaving"
          ? "Leaving"
          : state === "error"
            ? "Try again"
            : joined
              ? "Joined"
              : signedOut
                ? "Sign in to join"
                : "Join club"}
    </button>
  )
}

function clubStorageKey(clubId: string): string {
  return `communiti:joined-club:${clubId}`
}
