"use client"

const items = [
  "Sunrise hikes",
  "Film clubs",
  "Pottery nights",
  "Weekend treks",
  "Language tables",
  "Run crews",
  "Supper clubs",
  "Volunteer drives",
  "Rooftop jams",
  "Book circles",
]

export function Marquee() {
  return (
    <section aria-label="Things happening on COMMUNITI" className="border-y border-border py-5">
      <div className="group relative flex overflow-hidden [mask-image:linear-gradient(to_right,transparent,black_8%,black_92%,transparent)]">
        {[0, 1].map((dup) => (
          <div
            key={dup}
            aria-hidden={dup === 1}
            className="flex shrink-0 animate-[marquee_36s_linear_infinite] items-center gap-10 pr-10 group-hover:[animation-play-state:paused]"
          >
            {items.map((item, i) => (
              <div key={`${item}-${i}`} className="flex items-center gap-10">
                <span className="whitespace-nowrap text-lg font-medium text-muted-foreground">
                  {item}
                </span>
                <span className="size-1.5 rounded-full bg-primary/60" aria-hidden="true" />
              </div>
            ))}
          </div>
        ))}
      </div>
    </section>
  )
}
