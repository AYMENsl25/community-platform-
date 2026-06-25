import { Orbit } from "lucide-react"

const columns = [
  { heading: "Platform", links: ["Discover", "Experiences", "For organizers", "Mobile app"] },
  { heading: "Company", links: ["Manifesto", "Careers", "Press", "Contact"] },
  { heading: "Legal", links: ["Privacy", "Terms", "Community guidelines"] },
]

export function SiteFooter() {
  return (
    <footer className="border-t border-border px-4 py-14">
      <div className="mx-auto grid max-w-6xl gap-10 md:grid-cols-[1.5fr_repeat(3,1fr)]">
        <div>
          <a href="#top" className="flex items-center gap-2">
            <Orbit className="size-5 text-primary" aria-hidden="true" />
            <span className="text-sm font-semibold tracking-tight">COMMUNITI</span>
          </a>
          <p className="mt-4 max-w-xs text-sm leading-relaxed text-muted-foreground">
            An AI-native experiment in human connection. Find your people. Show up in real life.
          </p>
        </div>

        {columns.map((col) => (
          <nav key={col.heading} aria-label={col.heading}>
            <h3 className="text-sm font-semibold tracking-tight">{col.heading}</h3>
            <ul className="mt-4 space-y-3">
              {col.links.map((link) => (
                <li key={link}>
                  <a
                    href="#"
                    className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                  >
                    {link}
                  </a>
                </li>
              ))}
            </ul>
          </nav>
        ))}
      </div>

      <div className="mx-auto mt-12 flex max-w-6xl flex-col items-center justify-between gap-3 border-t border-border pt-6 text-xs text-muted-foreground sm:flex-row">
        <p>© {new Date().getFullYear()} COMMUNITI. A living experiment.</p>
        <p>Made for curious humans.</p>
      </div>
    </footer>
  )
}
