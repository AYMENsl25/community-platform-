import type { Metadata } from "next"
import { SiteFooter } from "@/components/site-footer"
import { SiteNav } from "@/components/site-nav"
import { CreateClubForm } from "@/components/organizer/create-club-form"

export const metadata: Metadata = {
  title: "Create club - COMMUNITI",
  description: "Create a COMMUNITI club and start hosting events.",
}

export default function NewClubPage() {
  return (
    <>
      <SiteNav />
      <main className="mx-auto max-w-5xl px-4 pb-24 pt-28 sm:px-6">
        <CreateClubForm />
      </main>
      <SiteFooter />
    </>
  )
}
