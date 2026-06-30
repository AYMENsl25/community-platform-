import { notFound } from "next/navigation"
import { SiteNav } from "@/components/site-nav"
import { SiteFooter } from "@/components/site-footer"
import { EventDetail } from "@/components/explore/event-detail"
import { getExploreEvent } from "@/lib/backend-events"

export const dynamicParams = true

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const detail = await getExploreEvent(id)
  const event = detail?.event
  if (!event) return { title: "Experience not found - COMMUNITI" }
  return {
    title: `${event.title} - COMMUNITI`,
    description: event.blurb,
  }
}

export default async function EventPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const detail = await getExploreEvent(id)
  if (!detail) notFound()

  return (
    <>
      <SiteNav />
      <EventDetail event={detail.event} organizer={detail.organizer} more={detail.more} />
      <SiteFooter />
    </>
  )
}
