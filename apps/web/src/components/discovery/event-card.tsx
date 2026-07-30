import type { components } from "@talaqi/api-client";
import { formatNumber, translate, type LocaleCode } from "@talaqi/translations";
import "./discovery.css";

type Event = components["schemas"]["EventCardResponse"];
export type EventCardLabels = {
  available: (count: number | null) => string;
  cash: string;
  featuredReason: string;
  free: string;
  save: string;
  saved: string;
};
function defaults(locale: LocaleCode): EventCardLabels {
  return {
    available: (count) =>
      count === null
        ? translate(locale, "discovery.unlimited")
        : `${formatNumber(count, locale)} ${translate(locale, "discovery.available")}`,
    cash: translate(locale, "discovery.cash"),
    featuredReason: translate(locale, "discovery.featuredExplanation"),
    free: translate(locale, "discovery.free"),
    save: translate(locale, "discovery.save"),
    saved: translate(locale, "discovery.saved"),
  };
}

export function EventCard({
  event,
  locale,
  labels: overrides,
  showFeaturedReason = false,
  showSave = false,
}: {
  event: Event;
  locale: LocaleCode;
  labels?: Partial<EventCardLabels>;
  showFeaturedReason?: boolean;
  showSave?: boolean;
}) {
  const labels = { ...defaults(locale), ...overrides };
  const schedule = new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: event.time_zone,
  }).format(new Date(event.start_at));
  return (
    <article className="tq-discovery-card tq-event-card" lang={locale}>
      <p className="tq-discovery-card__eyebrow">
        {humanize(event.category_slug)} ·{" "}
        {event.price_type === "free" ? labels.free : labels.cash}
      </p>
      <h3>
        <a href={`/events/${event.id}`}>{event.title}</a>
      </h3>
      <p>{event.description}</p>
      <dl className="tq-discovery-facts">
        <div>
          <dt>{translate(locale, "discovery.schedule")}</dt>
          <dd>{schedule}</dd>
        </div>
        <div>
          <dt>{translate(locale, "discovery.meetingArea")}</dt>
          <dd>
            {[event.district, event.public_meeting_area]
              .filter(Boolean)
              .join(" · ")}
          </dd>
        </div>
        <div>
          <dt>{translate(locale, "discovery.availability")}</dt>
          <dd>{labels.available(event.available_places)}</dd>
        </div>
      </dl>
      {event.club_slug && event.club_name ? (
        <p>
          <a href={`/clubs/${event.club_slug}`}>{event.club_name}</a>
        </p>
      ) : event.organizer_display_name ? (
        <p>{event.organizer_display_name}</p>
      ) : null}
      {showFeaturedReason ? (
        <p className="tq-discovery-note">{labels.featuredReason}</p>
      ) : null}
      {showSave ? (
        <button className="tq-discovery-control" type="button">
          {event.is_saved ? labels.saved : labels.save}
        </button>
      ) : null}
    </article>
  );
}
function humanize(value: string): string {
  return value
    .replaceAll("-", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}
