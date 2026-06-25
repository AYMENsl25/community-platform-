import { SiteNav } from "@/components/site-nav"
import { Hero } from "@/components/hero"
import { Marquee } from "@/components/marquee"
import { Discover } from "@/components/discover"
import { HowItWorks } from "@/components/how-it-works"
import { Experiences } from "@/components/experiences"
import { ManifestoCta } from "@/components/manifesto-cta"
import { SiteFooter } from "@/components/site-footer"

export default function Page() {
  return (
    <main className="relative min-h-screen bg-background text-foreground">
      <SiteNav />
      <Hero />
      <Marquee />
      <Discover />
      <HowItWorks />
      <Experiences />
      <ManifestoCta />
      <SiteFooter />
    </main>
  )
}
