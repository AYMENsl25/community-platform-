import Image from "next/image"
import Link from "next/link"
import type { Metadata } from "next"
import { ArrowRight, Building2, MapPin, Search, Users } from "lucide-react"
import { SiteFooter } from "@/components/site-footer"
import { SiteNav } from "@/components/site-nav"
import { getClubs } from "@/lib/backend-clubs"

export const metadata: Metadata = {
  title: "Clubs - COMMUNITI",
  description: "Browse public community clubs and find the groups behind COMMUNITI events.",
}

export default async function ClubsPage() {
  const clubs = await getClubs()

  return (
    <>
      <SiteNav />
      <main className="mx-auto min-h-screen max-w-6xl px-4 pb-24 pt-28 sm:px-6">
        <section className="flex flex-col gap-6 border-b border-border pb-8 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <p className="inline-flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-primary">
              <Building2 className="size-4" aria-hidden="true" />
              Club directory
            </p>
            <h1 className="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl">Find the clubs worth showing up for</h1>
            <p className="mt-4 text-base leading-7 text-muted-foreground">
              Browse public clubs, see where they gather, and jump into the communities creating events on COMMUNITI.
            </p>
          </div>
          <Link
            href="/explore"
            className="inline-flex items-center justify-center gap-2 rounded-full border border-border px-5 py-3 text-sm font-semibold transition-colors hover:border-primary/50 hover:text-primary"
          >
            <Search className="size-4" aria-hidden="true" />
            Explore events
          </Link>
        </section>

        <section className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {clubs.map((club) => (
            <Link
              key={club.id}
              href={`/clubs/${club.slug}`}
              className="group overflow-hidden rounded-lg border border-border bg-card transition-colors hover:border-primary/60"
            >
              <div className="relative aspect-[16/9] overflow-hidden bg-muted">
                <Image
                  src={club.cover_image_url || club.logo_url || "/placeholder.jpg"}
                  alt={club.name}
                  fill
                  sizes="(min-width: 1024px) 33vw, (min-width: 640px) 50vw, 100vw"
                  className="object-cover transition-transform duration-500 group-hover:scale-105"
                />
              </div>
              <div className="p-5">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-xs font-semibold uppercase tracking-wide text-primary">
                      {club.category_name || "Community"}
                    </p>
                    <h2 className="mt-1 truncate text-lg font-semibold tracking-tight">{club.name}</h2>
                  </div>
                  <ArrowRight className="mt-1 size-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-1 group-hover:text-primary" />
                </div>
                <p className="mt-3 line-clamp-3 text-sm leading-6 text-muted-foreground">
                  {club.description || "A COMMUNITI club hosting public events and local gatherings."}
                </p>
                <div className="mt-5 flex flex-wrap gap-4 text-xs text-muted-foreground">
                  <span className="inline-flex items-center gap-1.5">
                    <MapPin className="size-3.5" aria-hidden="true" />
                    {club.city || "Online"}
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <Users className="size-3.5" aria-hidden="true" />
                    {club.member_count} members
                  </span>
                </div>
              </div>
            </Link>
          ))}
        </section>
      </main>
      <SiteFooter />
    </>
  )
}
