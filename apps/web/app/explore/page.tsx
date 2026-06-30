import type { Metadata } from "next"
import { Explore } from "@/components/explore/explore"
import { getExploreEvents } from "@/lib/backend-events"

export const metadata: Metadata = {
  title: "Explore experiences — COMMUNITI",
  description: "Discover top community experiences near you and filter by what you're into.",
}

export default async function ExplorePage() {
  const events = await getExploreEvents()

  return <Explore initialEvents={events} />
}
