import { apiGet } from "@/lib/api"

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

export async function getClubs(): Promise<ClubCard[]> {
  return apiGet<ClubCard[]>("/clubs?limit=100")
}
