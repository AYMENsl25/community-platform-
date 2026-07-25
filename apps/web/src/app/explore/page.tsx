import type { operations } from "@talaqi/api-client";
import { translate, type LocaleCode } from "@talaqi/translations";
import { Container } from "@talaqi/ui";
import { EventCard } from "@/components/discovery/event-card";
import { FilterDrawer } from "@/components/discovery/filter-drawer";
import {
  DiscoveryEmpty,
  DiscoveryError,
} from "@/components/discovery/result-states";
import { PublicShell } from "@/components/shell/shells";
import { createServerPublicClient } from "@/lib/api/server-public-client";
import { resolveRequestLocale } from "@/lib/locale/request-locale";

type SearchParams = Record<string, string | string[] | undefined>;
type EventQuery = NonNullable<operations["listEvents"]["parameters"]["query"]>;
const keys = [
  "country",
  "city",
  "category",
  "date_from",
  "date_to",
  "price",
  "search",
  "cursor",
] as const;
const first = (value: string | string[] | undefined) =>
  Array.isArray(value) ? value[0] : value;

function filters(params: SearchParams): EventQuery {
  const query: Record<string, string | number> = { limit: 20 };
  for (const key of keys) {
    const value = first(params[key]);
    if (value) query[key] = value;
  }
  return query as EventQuery;
}

function nextHref(query: EventQuery, cursor: string): string {
  const params = new URLSearchParams();
  for (const key of keys.filter((key) => key !== "cursor")) {
    const value = query[key];
    if (value) params.set(key, String(value));
  }
  params.set("cursor", cursor);
  return `/explore?${params.toString()}`;
}

function stateLabels(locale: LocaleCode) {
  return {
    empty: translate(locale, "states.empty"),
    error: translate(locale, "states.error"),
    retry: translate(locale, "states.retry"),
  };
}

export default async function ExplorePage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const [locale, params, client] = await Promise.all([
    resolveRequestLocale(),
    searchParams,
    createServerPublicClient(),
  ]);
  const query = filters(params);
  const [events, metadata] = await Promise.all([
    client.listEvents(query),
    client.getMetadata(),
  ]);
  const labels = stateLabels(locale);
  return (
    <PublicShell currentHref="/explore" locale={locale}>
      <Container>
        <h1>{translate(locale, "discovery.title")}</h1>
        {metadata.ok ? (
          <FilterDrawer
            filters={{
              category: query.category ?? undefined,
              city: query.city ?? undefined,
              country: query.country ?? undefined,
              date_from: query.date_from ?? undefined,
              date_to: query.date_to ?? undefined,
              price: query.price ?? undefined,
              search: query.search ?? undefined,
            }}
            labels={{
              apply: translate(locale, "filters.apply"),
              category: translate(locale, "filters.category"),
              city: translate(locale, "filters.city"),
              close: translate(locale, "filters.close"),
              country: translate(locale, "filters.country"),
              filters: translate(locale, "filters.title"),
              open: translate(locale, "filters.open"),
              price: translate(locale, "filters.price"),
              search: translate(locale, "filters.search"),
            }}
            metadata={metadata.data}
            locale={locale}
          />
        ) : null}
        {!events.ok ? (
          <DiscoveryError labels={labels} locale={locale} />
        ) : events.data.items.length === 0 ? (
          <DiscoveryEmpty labels={labels} locale={locale} />
        ) : (
          <section aria-label={translate(locale, "a11y.searchResults")}>
            {events.data.items.map((event) => (
              <EventCard event={event} key={event.id} locale={locale} />
            ))}
          </section>
        )}
        {events.ok && events.data.next_cursor ? (
          <a
            className="tq-action-link tq-action-link--secondary"
            href={nextHref(query, events.data.next_cursor)}
          >
            {translate(locale, "discovery.loadMore")}
          </a>
        ) : null}
      </Container>
    </PublicShell>
  );
}
