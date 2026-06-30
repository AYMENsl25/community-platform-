import type { Metadata } from "next"
import { SiteFooter } from "@/components/site-footer"
import { SiteNav } from "@/components/site-nav"
import { CreateEventForm } from "@/components/organizer/create-event-form"

export const metadata: Metadata = {
  title: "Add event - COMMUNITI",
  description: "Create and publish a COMMUNITI club event.",
}

export default function NewEventPage() {
  return (
    <>
      <SiteNav />
      <main className="mx-auto max-w-5xl px-4 pb-24 pt-28 sm:px-6">
        <CreateEventForm />
      </main>
      <SiteFooter />
    </>
  )
}
