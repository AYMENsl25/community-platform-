"use client"

import { SignInButton, UserButton, useUser } from "@clerk/nextjs"
import Link from "next/link"
import { useEffect, useState } from "react"
import { CalendarPlus, LogIn, Orbit, UserPlus } from "lucide-react"
import { MagneticButton } from "@/components/magnetic-button"
import { cn } from "@/lib/utils"

const links = [
  { label: "Discover", href: "/#discover" },
  { label: "How it works", href: "/#how" },
  { label: "Explore", href: "/explore" },
  { label: "Clubs", href: "/clubs" },
  { label: "Manifesto", href: "/#manifesto" },
]

export function SiteNav() {
  const { isLoaded, isSignedIn } = useUser()
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 16)
    onScroll()
    window.addEventListener("scroll", onScroll, { passive: true })
    return () => window.removeEventListener("scroll", onScroll)
  }, [])

  return (
    <header className="fixed inset-x-0 top-0 z-50 flex justify-center px-3 pt-4 sm:px-4">
      <nav
        className={cn(
          "flex w-full max-w-6xl items-center justify-between gap-3 rounded-full px-3 py-2.5 transition-all duration-500 sm:px-4",
          scrolled
            ? "border border-border bg-card/70 backdrop-blur-xl"
            : "border border-transparent bg-transparent",
        )}
      >
        <Link href="/" className="flex shrink-0 items-center gap-2 pl-1">
          <Orbit className="size-5 text-primary" aria-hidden="true" />
          <span className="text-sm font-semibold tracking-tight">COMMUNITI</span>
        </Link>

        <ul className="hidden items-center gap-1 lg:flex">
          {links.map((link) => (
            <li key={link.href}>
              <Link
                href={link.href}
                className="group relative rounded-full px-4 py-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
              >
                {link.label}
                <span className="absolute inset-x-4 bottom-1.5 h-px origin-left scale-x-0 bg-primary transition-transform duration-300 group-hover:scale-x-100" />
              </Link>
            </li>
          ))}
        </ul>

        <div className="flex shrink-0 items-center gap-2">
          <Link
            href="/organizer/events/new"
            className="inline-flex items-center justify-center gap-1.5 rounded-full border border-border bg-background/50 px-3 py-2.5 text-xs font-semibold text-foreground transition-colors hover:border-primary/50 hover:text-primary sm:px-4 sm:text-sm"
            aria-label="Add event"
          >
            <CalendarPlus className="size-4" aria-hidden="true" />
            <span className="hidden min-[420px]:inline">Add event</span>
          </Link>
          <MagneticButton href="/explore" className="px-4 py-2.5 sm:px-5" aria-label="Register for an event">
            <UserPlus className="size-4" aria-hidden="true" />
            Register
          </MagneticButton>
          {isLoaded && !isSignedIn ? (
            <SignInButton mode="modal">
              <button
                type="button"
                className="hidden items-center justify-center gap-1.5 rounded-full border border-border bg-background/50 px-4 py-2.5 text-sm font-semibold text-foreground transition-colors hover:border-primary/50 hover:text-primary sm:inline-flex"
              >
                <LogIn className="size-4" aria-hidden="true" />
                Sign in
              </button>
            </SignInButton>
          ) : null}
          {isLoaded && isSignedIn ? (
            <UserButton
              appearance={{
                elements: {
                  userButtonAvatarBox: "size-9 border border-border",
                },
              }}
            />
          ) : null}
        </div>
      </nav>
    </header>
  )
}
