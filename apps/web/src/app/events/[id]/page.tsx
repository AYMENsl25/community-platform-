import type { Metadata } from "next";
import { notFound } from "next/navigation";
import type { components } from "@talaqi/api-client";
import {
  formatNumber,
  getLocaleDirection,
  LOCALE_CODES,
  translate,
  type LocaleCode,
} from "@talaqi/translations";
import { Card, Container } from "@talaqi/ui";
import { CanonicalCover } from "@/components/discovery/canonical-cover";
import { EventCard } from "@/components/discovery/event-card";
import { SaveEventButton } from "@/components/discovery/save-event-button";
import { DiscoveryError } from "@/components/discovery/result-states";
import { PublicShell } from "@/components/shell/shells";
import { createServerPublicClient } from "@/lib/api/server-public-client";
import { resolveRequestLocale } from "@/lib/locale/request-locale";

type EventDetail = components["schemas"]["EventAudienceResponse"];
type Props = {
  params: Promise<{ id: string }>;
  searchParams?: Promise<{ locale?: string }>;
};

async function pageLocale(
  searchParams?: Props["searchParams"],
): Promise<LocaleCode> {
  const requested = (await searchParams)?.locale;
  return LOCALE_CODES.includes(requested as LocaleCode)
    ? (requested as LocaleCode)
    : resolveRequestLocale();
}

function publicUrl(path: string): string {
  return new URL(
    path,
    process.env.WEB_PUBLIC_URL ?? "http://localhost:3000",
  ).toString();
}

function alternates(path: string) {
  return Object.fromEntries(
    LOCALE_CODES.map((locale) => [
      locale,
      publicUrl(`${path}?locale=${locale}`),
    ]),
  );
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const result = await (await createServerPublicClient()).getEvent(id);
  if (!result.ok)
    return {
      title: "Talaqi",
      robots: { index: false, follow: false },
    };
  const path = `/events/${id}`;
  const image = result.data.cover_media_id
    ? publicUrl(`/api/media/${result.data.cover_media_id}`)
    : undefined;
  return {
    title: result.data.title,
    description: result.data.description,
    alternates: { canonical: publicUrl(path), languages: alternates(path) },
    robots: { index: true, follow: true },
    openGraph: {
      type: "article",
      title: result.data.title,
      description: result.data.description,
      url: publicUrl(path),
      ...(image ? { images: [{ url: image, alt: result.data.title }] } : {}),
    },
  };
}

function schedule(event: EventDetail, locale: LocaleCode): string {
  const formatter = new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: event.time_zone,
  });
  const start = new Date(event.start_at);
  const end = new Date(event.end_at);
  return typeof formatter.formatRange === "function"
    ? formatter.formatRange(start, end)
    : `${formatter.format(start)} - ${formatter.format(end)}`;
}

function availability(event: EventDetail, locale: LocaleCode): string {
  return event.available_places === null
    ? translate(locale, "discovery.unlimited")
    : `${formatNumber(event.available_places, locale)} ${translate(
        locale,
        "discovery.available",
      )}`;
}

export default async function EventPage({ params, searchParams }: Props) {
  const [{ id }, locale, client] = await Promise.all([
    params,
    pageLocale(searchParams),
    createServerPublicClient(),
  ]);
  const result = await client.getEvent(id);
  if (!result.ok && result.status === 404) notFound();
  if (!result.ok)
    return (
      <PublicShell currentHref={`/events/${id}`} locale={locale}>
        <Container>
          <DiscoveryError
            labels={{
              error: translate(locale, "states.error"),
              retry: translate(locale, "states.retry"),
            }}
            locale={locale}
          />
        </Container>
      </PublicShell>
    );

  const event = result.data;
  const [relatedResult, policyResult] = await Promise.all([
    client.listEvents({
      city: event.city_slug,
      category: event.category_slug,
      limit: 6,
    }),
    client.getRegionPolicy(event.country_code),
  ]);
  const related = relatedResult.ok
    ? relatedResult.data.items
        .filter((item) => item.id !== event.id)
        .slice(0, 4)
    : [];
  const venue = [event.district, event.public_meeting_area]
    .filter(Boolean)
    .join(" \u00b7 ");
  const mapQuery = event.exact_address
    ? [event.exact_address, event.city_slug, event.country_code]
    : [event.district, event.city_slug, event.country_code];
  const mapHref = `https://www.openstreetmap.org/search?query=${encodeURIComponent(
    mapQuery.filter(Boolean).join(", "),
  )}`;

  return (
    <PublicShell currentHref={`/events/${id}`} locale={locale}>
      <Container>
        <article
          className="tq-public-detail"
          dir={getLocaleDirection(locale)}
          lang={locale}
        >
          <CanonicalCover mediaId={event.cover_media_id} alt={event.title} />
          <p className="tq-discovery-card__eyebrow">
            {translate(locale, "discovery.event")}
          </p>
          <h1>{event.title}</h1>
          <p className="tq-public-detail__lead">{event.description}</p>
          <SaveEventButton
            eventId={event.id}
            initialSaved={event.is_saved}
            locale={locale}
          />

          <dl className="tq-discovery-facts tq-public-detail__facts">
            <div>
              <dt>{translate(locale, "discovery.schedule")}</dt>
              <dd>{schedule(event, locale)}</dd>
            </div>
            <div>
              <dt>{translate(locale, "discovery.meetingArea")}</dt>
              <dd>{venue || translate(locale, "discovery.privateVenue")}</dd>
            </div>
            <div>
              <dt>{translate(locale, "discovery.availability")}</dt>
              <dd>{availability(event, locale)}</dd>
            </div>
            <div>
              <dt>{translate(locale, "discovery.organizedBy")}</dt>
              <dd>
                {event.club_slug && event.club_name ? (
                  <a href={`/clubs/${event.club_slug}`}>{event.club_name}</a>
                ) : (
                  event.organizer_display_name
                )}{" "}
                <span className="tq-discovery-note">
                  {translate(
                    locale,
                    event.ownership_type === "club"
                      ? "discovery.clubOrganized"
                      : "discovery.independentOrganized",
                  )}
                </span>
              </dd>
            </div>
          </dl>

          <div className="tq-public-detail__grid">
            <Card aria-label={translate(locale, "discovery.meetingArea")}>
              <h2>{translate(locale, "discovery.meetingArea")}</h2>
              {event.exact_address ? (
                <p>{event.exact_address}</p>
              ) : (
                <p>{translate(locale, "discovery.privateVenue")}</p>
              )}
              <a href={mapHref} rel="noreferrer" target="_blank">
                {translate(locale, "discovery.openMap")}
              </a>
            </Card>
            <Card aria-label={translate(locale, "discovery.rules")}>
              <h2>{translate(locale, "discovery.rules")}</h2>
              <p>
                {translate(
                  locale,
                  event.price_type === "free"
                    ? "discovery.registrationRuleFree"
                    : "discovery.registrationRuleCash",
                )}
              </p>
              <h3>{translate(locale, "discovery.cancellation")}</h3>
              <p>
                {formatNumber(event.cancellation_cutoff_minutes, locale)}{" "}
                {translate(locale, "discovery.minutesBeforeStart")}
              </p>
              {policyResult.ok ? (
                <p className="tq-discovery-note">
                  {event.country_code}
                  {" \u00b7 "}
                  {policyResult.data.allowed_registration_methods
                    .map((method) =>
                      translate(
                        locale,
                        method === "free" ? "discovery.free" : "discovery.cash",
                      ),
                    )
                    .join(", ")}
                </p>
              ) : null}
            </Card>
          </div>
        </article>

        {related.length ? (
          <section aria-labelledby="related-events-title">
            <h2 id="related-events-title">
              {translate(locale, "discovery.relatedEvents")}
            </h2>
            <div className="tq-public-detail__related">
              {related.map((item) => (
                <EventCard event={item} key={item.id} locale={locale} />
              ))}
            </div>
          </section>
        ) : null}
      </Container>
    </PublicShell>
  );
}
