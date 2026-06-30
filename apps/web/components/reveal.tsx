"use client"

import { motion } from "motion/react"
import type { ReactNode } from "react"

type Direction = "up" | "down" | "left" | "right"

const offsets: Record<Direction, { x: number; y: number; clip: string }> = {
  up: { x: 0, y: 56, clip: "inset(100% 0% 0% 0%)" },
  down: { x: 0, y: -56, clip: "inset(0% 0% 100% 0%)" },
  left: { x: 80, y: 0, clip: "inset(0% 0% 0% 100%)" },
  right: { x: -80, y: 0, clip: "inset(0% 100% 0% 0%)" },
}

export function Reveal({
  children,
  direction = "up",
  delay = 0,
  className,
}: {
  children: ReactNode
  direction?: Direction
  delay?: number
  className?: string
}) {
  const offset = offsets[direction]

  return (
    <motion.div
      className={className}
      initial={{
        opacity: 0,
        x: offset.x,
        y: offset.y,
        filter: "blur(12px)",
        clipPath: offset.clip,
      }}
      whileInView={{
        opacity: 1,
        x: 0,
        y: 0,
        filter: "blur(0px)",
        clipPath: "inset(0% 0% 0% 0%)",
      }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.8, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  )
}
