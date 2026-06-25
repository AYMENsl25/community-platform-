"use client"

import { useEffect, useState } from "react"
import { Orbit } from "lucide-react"
import { MagneticButton } from "@/components/magnetic-button"
import { cn } from "@/lib/utils"

const links = [
  { label: "Discover", href: "#discover" },
  { label: "How it works", href: "#how" },
  { label: "Experiences", href: "#experiences" },
  { label: "Manifesto", href: "#manifesto" },
]

export function SiteNav() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 16)
    onScroll()
    window.addEventListener("scroll", onScroll, { passive: true })
    return () => window.removeEventListener("scroll", onScroll)
  }, [])

  return (
    <header className="fixed inset-x-0 top-0 z-50 flex justify-center px-4 pt-4">
      <nav
        className={cn(
          "flex w-full max-w-5xl items-center justify-between rounded-full px-4 py-2.5 transition-all duration-500",
          scrolled
            ? "border border-border bg-card/70 backdrop-blur-xl"
            : "border border-transparent bg-transparent",
        )}
      >
        <a href="#top" className="flex items-center gap-2 pl-1">
          <Orbit className="size-5 text-primary" aria-hidden="true" />
          <span className="text-sm font-semibold tracking-tight">COMMUNITI</span>
        </a>

        <ul className="hidden items-center gap-1 md:flex">
          {links.map((link) => (
            <li key={link.href}>
              <a
                href={link.href}
                className="group relative rounded-full px-4 py-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
              >
                {link.label}
                <span className="absolute inset-x-4 bottom-1.5 h-px origin-left scale-x-0 bg-primary transition-transform duration-300 group-hover:scale-x-100" />
              </a>
            </li>
          ))}
        </ul>

        <MagneticButton href="/explore" className="px-5 py-2.5" aria-label="Join the experiment">
          Join
        </MagneticButton>
      </nav>
    </header>
  )
}
