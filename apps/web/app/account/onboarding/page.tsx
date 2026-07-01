import { currentUser } from "@clerk/nextjs/server"
import { ArrowRight, CalendarPlus, Compass, Users } from "lucide-react"
import Link from "next/link"

export default async function OnboardingPage() {
  const user = await currentUser()
  const firstName = user?.firstName || "there"

  return (
    <main className="min-h-screen bg-background px-4 py-24 text-foreground">
      <section className="mx-auto flex w-full max-w-3xl flex-col gap-8">
        <div className="space-y-3">
          <p className="text-sm font-semibold uppercase tracking-wide text-primary">
            Account ready
          </p>
          <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
            Welcome, {firstName}
          </h1>
          <p className="max-w-2xl text-base leading-7 text-muted-foreground">
            Your COMMUNITI account is set. Start by exploring events, joining a
            club, or creating the first experience for your community.
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <Link
            href="/explore"
            className="group rounded-lg border border-border bg-card p-5 transition-colors hover:border-primary/60"
          >
            <Compass className="mb-5 size-5 text-primary" aria-hidden="true" />
            <h2 className="text-base font-semibold">Explore events</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Browse live community experiences.
            </p>
            <ArrowRight className="mt-5 size-4 transition-transform group-hover:translate-x-1" />
          </Link>

          <Link
            href="/organizer/clubs/new"
            className="group rounded-lg border border-border bg-card p-5 transition-colors hover:border-primary/60"
          >
            <Users className="mb-5 size-5 text-primary" aria-hidden="true" />
            <h2 className="text-base font-semibold">Create a club</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Start organizing around a shared interest.
            </p>
            <ArrowRight className="mt-5 size-4 transition-transform group-hover:translate-x-1" />
          </Link>

          <Link
            href="/organizer/events/new"
            className="group rounded-lg border border-border bg-card p-5 transition-colors hover:border-primary/60"
          >
            <CalendarPlus className="mb-5 size-5 text-primary" aria-hidden="true" />
            <h2 className="text-base font-semibold">Add an event</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Publish the next gathering for your club.
            </p>
            <ArrowRight className="mt-5 size-4 transition-transform group-hover:translate-x-1" />
          </Link>
        </div>
      </section>
    </main>
  )
}
