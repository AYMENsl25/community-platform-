"use client"

import { motion, useMotionValue, useSpring, useTransform } from "motion/react"
import Link from "next/link"
import { useRef, useState, type ReactNode } from "react"
import { cn } from "@/lib/utils"

type Variant = "primary" | "outline"

export function MagneticButton({
  children,
  onClick,
  href,
  variant = "primary",
  className,
  "aria-label": ariaLabel,
}: {
  children: ReactNode
  onClick?: () => void
  href?: string
  variant?: Variant
  className?: string
  "aria-label"?: string
}) {
  const ref = useRef<HTMLElement>(null)
  const x = useMotionValue(0)
  const y = useMotionValue(0)

  // radial fill origin (where the cursor entered/moves)
  const [fill, setFill] = useState({ x: 50, y: 50 })
  const [active, setActive] = useState(false)

  const springX = useSpring(x, { stiffness: 250, damping: 18 })
  const springY = useSpring(y, { stiffness: 250, damping: 18 })
  const contentX = useTransform(springX, (v) => v * 0.35)
  const contentY = useTransform(springY, (v) => v * 0.35)

  function handleMove(e: React.MouseEvent) {
    const el = ref.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const relX = e.clientX - rect.left - rect.width / 2
    const relY = e.clientY - rect.top - rect.height / 2
    x.set(relX * 0.45)
    y.set(relY * 0.45)
    setFill({
      x: ((e.clientX - rect.left) / rect.width) * 100,
      y: ((e.clientY - rect.top) / rect.height) * 100,
    })
  }

  function handleEnter(e: React.MouseEvent) {
    const el = ref.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    setFill({
      x: ((e.clientX - rect.left) / rect.width) * 100,
      y: ((e.clientY - rect.top) / rect.height) * 100,
    })
    setActive(true)
  }

  function handleLeave() {
    x.set(0)
    y.set(0)
    setActive(false)
  }

  const base =
    "group relative inline-flex items-center justify-center gap-2 overflow-hidden rounded-full px-7 py-3.5 text-sm font-semibold tracking-tight transition-colors duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"

  const variants: Record<Variant, string> = {
    primary: "bg-primary text-primary-foreground",
    outline: "border border-border bg-transparent text-foreground",
  }

  const fillColor = variant === "primary" ? "bg-foreground" : "bg-primary"
  const hoverText = variant === "primary" ? "group-hover:text-background" : "group-hover:text-primary-foreground"

  const inner = (
    <>
      {/* radial spotlight fill expanding from cursor */}
      <motion.span
        aria-hidden="true"
        className={cn("pointer-events-none absolute aspect-square w-[140%] rounded-full", fillColor)}
        style={{ left: `${fill.x}%`, top: `${fill.y}%`, x: "-50%", y: "-50%" }}
        initial={false}
        animate={{ scale: active ? 1 : 0, opacity: active ? 1 : 0 }}
        transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
      />
      <motion.span
        style={{ x: contentX, y: contentY }}
        className={cn("relative z-10 inline-flex items-center gap-2 transition-colors duration-300", hoverText)}
      >
        {children}
      </motion.span>
    </>
  )

  const sharedProps = {
    onMouseMove: handleMove,
    onMouseEnter: handleEnter,
    onMouseLeave: handleLeave,
    "aria-label": ariaLabel,
    className: cn(base, variants[variant], className),
  }

  if (href) {
    return (
      <MotionLink
        ref={ref as React.RefObject<HTMLAnchorElement>}
        href={href}
        onClick={onClick}
        style={{ x: springX, y: springY }}
        whileTap={{ scale: 0.96 }}
        {...sharedProps}
      >
        {inner}
      </MotionLink>
    )
  }

  return (
    <motion.button
      ref={ref as React.RefObject<HTMLButtonElement>}
      type="button"
      onClick={onClick}
      style={{ x: springX, y: springY }}
      whileTap={{ scale: 0.96 }}
      {...sharedProps}
    >
      {inner}
    </motion.button>
  )
}

const MotionLink = motion.create(Link)
