import type { Metadata } from "next"
import { Explore } from "@/components/explore/explore"

export const metadata: Metadata = {
  title: "Explore experiences — COMMUNITI",
  description: "Discover top community experiences near you and filter by what you're into.",
}

export default function ExplorePage() {
  return <Explore />
}
