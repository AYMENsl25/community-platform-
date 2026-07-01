import { apiGet } from "@/lib/api"
import { ORGANIZERS } from "@/lib/events"

export type ClubCard = {
  id: string
  name: string
  slug: string
  description: string | null
  logo_url: string | null
  cover_image_url: string | null
  city: string | null
  country: string | null
  member_count: number
  category_name: string | null
}

export type ClubDetail = ClubCard & {
  owner_id: string
  category_id: string | null
  visibility: string
  status: string
  owner_name: string
  owner_avatar_url: string | null
}

export type MyClubSummary = ClubCard & {
  visibility: string
  status: string
  member_role: string
  member_status: string
}

export async function getClubs(): Promise<ClubCard[]> {
  try {
    return await apiGet<ClubCard[]>("/clubs?limit=100")
  } catch (error) {
    console.warn("Using static clubs because the COMMUNITI API is unavailable.", error)
    return Object.values(ORGANIZERS).map((organizer) => ({
      id: organizer.id,
      name: organizer.name,
      slug: organizer.id,
      description: organizer.bio,
      logo_url: organizer.logo,
      cover_image_url: organizer.reel[0]?.poster ?? organizer.logo,
      city: "San Francisco",
      country: "United States",
      member_count: organizer.members,
      category_name: organizer.verified ? "Verified community" : "Community",
    }))
  }
}

export async function getClub(slug: string): Promise<ClubDetail | null> {
  try {
    return await apiGet<ClubDetail>(`/clubs/${encodeURIComponent(slug)}`)
  } catch (error) {
    console.warn("Using static club detail because the COMMUNITI API is unavailable.", error)
    const organizer = ORGANIZERS[slug]
    if (!organizer) return null

    return {
      id: organizer.id,
      name: organizer.name,
      slug: organizer.id,
      description: organizer.bio,
      logo_url: organizer.logo,
      cover_image_url: organizer.reel[0]?.poster ?? organizer.logo,
      city: "San Francisco",
      country: "United States",
      member_count: organizer.members,
      category_name: organizer.verified ? "Verified community" : "Community",
      owner_id: organizer.id,
      category_id: null,
      visibility: "public",
      status: "published",
      owner_name: organizer.name,
      owner_avatar_url: organizer.logo,
    }
  }
}
