import { apiGet } from "@/lib/api"
import {
  EVENTS,
  getEventById,
  getEventsByOrganizer,
  getOrganizer,
  type CommunityEvent,
  type EventCategory,
  type EventWhen,
  type Organizer,
} from "@/lib/events"

type ApiEventCard = {
  id: string
  club_id: string
  club_name: string
  title: string
  slug: string
  description: string | null
  event_type: string
  starts_at: string
  ends_at: string | null
  city: string | null
  country: string | null
  location_name: string | null
  capacity: number | null
  registered_count: number
  waitlist_count: number
  price_amount: string
  currency: string
  cover_image_url: string | null
  category_name: string | null
}

type ApiEventDetail = ApiEventCard & {
  created_by: string
  timezone: string
  address: string | null
  lat: string | null
  lng: string | null
  status: string
  requires_approval: boolean
  club_slug: string
  club_logo_url: string | null
  organizer_name: string
  organizer_avatar_url: string | null
  is_full: boolean
}

const CATEGORY_FALLBACK: EventCategory = "Social"

function toCategory(value: string | null): EventCategory {
  const normalized = value?.trim()
  if (
    normalized === "Outdoors" ||
    normalized === "Craft" ||
    normalized === "Social" ||
    normalized === "Sports" ||
    normalized === "Music" ||
    normalized === "Wellness" ||
    normalized === "Food"
  ) {
    return normalized
  }
  return CATEGORY_FALLBACK
}

function toWhen(startsAt: string): EventWhen {
  const start = new Date(startsAt)
  const now = new Date()
  const diffDays = Math.ceil((start.getTime() - now.getTime()) / 86_400_000)
  if (diffDays <= 0) return "Today"
  if (diffDays <= 5) return "This week"
  return "This weekend"
}

function formatDate(startsAt: string): string {
  return new Intl.DateTimeFormat("en", {
    weekday: "short",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(startsAt))
}

function formatDuration(startsAt: string, endsAt: string | null): string {
  if (!endsAt) return "Time TBA"
  const start = new Date(startsAt)
  const end = new Date(endsAt)
  const hours = Math.max((end.getTime() - start.getTime()) / 3_600_000, 0)
  if (hours < 1) return "Less than 1 hour"
  if (Number.isInteger(hours)) return `${hours} ${hours === 1 ? "hour" : "hours"}`
  return `${hours.toFixed(1)} hours`
}

function eventTypeToImage(eventType: string): string {
  const type = eventType.toLowerCase()
  if (type.includes("outdoor")) return "/experiences/sunrise-hike.png"
  if (type.includes("sport")) return "/experiences/run-club.png"
  if (type.includes("music")) return "/experiences/live-music.png"
  if (type.includes("food")) return "/experiences/food-crawl.png"
  if (type.includes("wellness")) return "/experiences/yoga.png"
  return "/experiences/book-club.png"
}

function localImageOrFallback(value: string | null, fallback: string): string {
  if (!value) return fallback
  return value.startsWith("/") ? value : fallback
}

function toCoordinate(value: string | null | undefined, fallback: number): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

function mapApiEvent(event: ApiEventCard | ApiEventDetail): CommunityEvent {
  const capacity = event.capacity ?? event.registered_count + 20
  const spots = Math.max(capacity - event.registered_count, 0)
  const image = localImageOrFallback(event.cover_image_url, eventTypeToImage(event.event_type))
  const detail = "club_slug" in event ? event : null

  return {
    id: event.id,
    title: event.title,
    blurb: event.description || `Hosted by ${event.club_name}`,
    about: event.description || `Join ${event.club_name} for this COMMUNITI experience.`,
    category: toCategory(event.category_name),
    when: toWhen(event.starts_at),
    date: formatDate(event.starts_at),
    duration: formatDuration(event.starts_at, event.ends_at),
    location: event.location_name || event.city || "Location TBA",
    address: detail?.address || event.location_name || event.city || "Address TBA",
    city: event.city || "Riyadh",
    lat: toCoordinate(detail?.lat, 24.7136),
    lng: toCoordinate(detail?.lng, 46.6753),
    spots,
    price: Number(event.price_amount),
    currency: event.currency,
    attendees: event.registered_count,
    trending: event.registered_count >= 10,
    image,
    highlights: ["Community hosted", "Real local group", "Easy to join"],
    bring: ["Confirmation", "Comfortable clothes"],
    organizerId: event.club_id,
  }
}

function mapApiOrganizer(event: ApiEventDetail): Organizer {
  const poster = localImageOrFallback(event.cover_image_url, eventTypeToImage(event.event_type))

  return {
    id: event.club_id,
    name: event.club_name,
    handle: event.club_slug ? `@${event.club_slug}` : "@communiti",
    logo: localImageOrFallback(event.club_logo_url || event.organizer_avatar_url, "/orgs/trailheads.png"),
    verified: event.status === "published",
    bio: `${event.organizer_name} hosts ${event.club_name} experiences for the COMMUNITI community.`,
    members: Math.max(event.registered_count + 20, 20),
    eventsHosted: 1,
    rating: 4.8,
    socials: {},
    reel: [{ title: `${event.club_name} preview`, duration: "1:20", poster }],
  }
}

export async function getExploreEvents(): Promise<CommunityEvent[]> {
  try {
    const events = await apiGet<ApiEventCard[]>("/events?limit=100")
    return events.map(mapApiEvent)
  } catch (error) {
    console.warn("Using static events because the COMMUNITI API is unavailable.", error)
    return EVENTS
  }
}

export async function getExploreEvent(
  id: string,
): Promise<{ event: CommunityEvent; organizer: Organizer; more: CommunityEvent[] } | null> {
  try {
    const eventDetail = await apiGet<ApiEventDetail>(`/events/${encodeURIComponent(id)}`)
    const event = mapApiEvent(eventDetail)
    const allEvents = await apiGet<ApiEventCard[]>("/events?limit=100")
    const more = allEvents
      .filter((item) => item.club_id === eventDetail.club_id && item.id !== eventDetail.id)
      .slice(0, 3)
      .map(mapApiEvent)

    return {
      event,
      organizer: mapApiOrganizer(eventDetail),
      more,
    }
  } catch (error) {
    console.warn("Using static event detail because the COMMUNITI API is unavailable.", error)

    const event = getEventById(id)
    if (!event) return null

    const organizer = getOrganizer(event.organizerId)
    if (!organizer) return null

    return {
      event,
      organizer,
      more: getEventsByOrganizer(event.organizerId, event.id).slice(0, 3),
    }
  }
}
