import { notFound } from "next/navigation"
import { SiteNav } from "@/components/site-nav"
import { SiteFooter } from "@/components/site-footer"
import { EventDetail } from "@/components/explore/event-detail"
import { EVENTS, getEventById, getOrganizer, getEventsByOrganizer } from "@/lib/events"

export function generateStaticParams() {
  return EVENTS.map((e) => ({ id: e.id }))
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const event = getEventById(id)
  if (!event) return { title: "Experience not found — COMMUNITI" }
  return {
    title: `${event.title} — COMMUNITI`,
    description: event.blurb,
  }
}

export default async function EventPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const event = getEventById(id)
  if (!event) notFound()

  const organizer = getOrganizer(event.organizerId)
  if (!organizer) notFound()

  const more = getEventsByOrganizer(event.organizerId, event.id).slice(0, 3)

  return (
    <>
      <SiteNav />
      <EventDetail event={event} organizer={organizer} more={more} />
      <SiteFooter />
    </>
  )
}
