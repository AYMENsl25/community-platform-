import type { operations } from "@talaqi/api-client";
import { translate, type LocaleCode } from "@talaqi/translations";
import { Container } from "@talaqi/ui";
import { EventCard } from "@/components/discovery/event-card";
import { FilterDrawer } from "@/components/discovery/filter-drawer";
import { QuickFilters } from "@/components/discovery/quick-filters";
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
        <header className="tq-explore-heading">
          <p className="tq-home-eyebrow">
            {translate(locale, "discovery.event")}
          </p>
          <h1>{translate(locale, "discovery.title")}</h1>
          <form action="/explore" className="tq-explore-search" method="get">
            {keys
              .filter((key) => key !== "cursor" && key !== "search")
              .map((key) =>
                query[key] ? (
                  <input
                    key={key}
                    name={key}
                    type="hidden"
                    value={String(query[key])}
                  />
                ) : null,
              )}
            <label htmlFor="explore-search">
              <span className="tq-visually-hidden">{translate(locale, "filters.search")}</span>
              <input
                autoComplete="off"
                defaultValue={query.search ?? ""}
                id="explore-search"
                name="search"
                placeholder={translate(locale, "filters.search")}
                type="search"
              />
            </label>
            <button className="tq-discovery-control" type="submit">
              {translate(locale, "shell.navigation.explore")}
            </button>
          </form>
        </header>
        {metadata.ok ? (
          <div className="tq-explore-tools">
            <QuickFilters
              locale={locale}
              metadata={metadata.data}
              values={Object.fromEntries(
                keys.map((key) => [key, query[key]?.toString()]),
              )}
            />
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
          </div>
        ) : null}
        {!events.ok ? (
          <DiscoveryError labels={labels} locale={locale} />
        ) : events.data.items.length === 0 ? (
          <DiscoveryEmpty labels={labels} locale={locale} />
        ) : (
          <>
            <div className="tq-results-heading">
              <h2>{translate(locale, "discovery.events")}</h2>
              <p>
                {events.data.items.length} {translate(locale, "discovery.events")}
              </p>
            </div>
            <section
              aria-label={translate(locale, "a11y.searchResults")}
              className="tq-discovery-grid"
            >
              {events.data.items.map((event) => (
                <EventCard event={event} key={event.id} locale={locale} showSave />
              ))}
            </section>
          </>
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
