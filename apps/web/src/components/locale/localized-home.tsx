"use client";

import type { components } from "@talaqi/api-client";
import type { LocaleCode, TranslationKey } from "@talaqi/translations";
import { ActionLink, Card, Container } from "@talaqi/ui";
import Image from "next/image";

import { ClubCard } from "@/components/discovery/club-card";
import { EventCard } from "@/components/discovery/event-card";
import {
  DiscoveryEmpty,
  DiscoveryError,
} from "@/components/discovery/result-states";
import { PublicShell } from "@/components/shell/shells";
import { LocaleProvider, useLocale } from "@/lib/locale/locale-context";
import { LocaleSelector } from "./locale-selector";

type Metadata = components["schemas"]["DiscoveryMetadataResponse"];
type Event = components["schemas"]["EventCardResponse"];
type Club = components["schemas"]["ClubCardResponse"];

export type LandingData = {
  featuredEvents: Event[];
  metadata: Metadata | null;
  popularClubs: Club[];
  unavailable?: boolean;
};

const emptyLanding: LandingData = {
  featuredEvents: [],
  metadata: null,
  popularClubs: [],
};

function HomeContent({ landing }: { landing: LandingData }) {
  const { locale, t } = useLocale();
  const stateLabels = {
    empty: t("states.empty"),
    error: t("states.error"),
    retry: t("states.retry"),
  };
  const eventLabels = {
    available: (count: number | null) =>
      count === null
        ? t("discovery.unlimited")
        : `${count} ${t("discovery.available")}`,
    cash: t("discovery.cash"),
    featuredReason: t("discovery.featuredExplanation"),
    free: t("discovery.free"),
    save: t("discovery.save"),
    saved: t("discovery.saved"),
  };

  return (
    <PublicShell currentHref="/" locale={locale}>
      <section className="tq-home-hero" id="community">
        <Container className="tq-home-grid">
          <div className="tq-home-copy">
            <LocaleSelector />
            <p className="tq-home-eyebrow">{t("home.eyebrow")}</p>
            <h1>{t("home.title")}</h1>
            <p className="tq-home-lead">{t("home.lead")}</p>
            <div className="tq-home-actions">
              <ActionLink href="/explore">
                {t("shell.navigation.explore")}
              </ActionLink>
              <ActionLink href="#about" variant="secondary">
                {t("home.secondaryAction")}
              </ActionLink>
            </div>
            {landing.metadata ? (
              <div className="tq-home-search">
                <div>
                  <h2>{t("home.region.title")}</h2>
                  <p>{t("home.region.body")}</p>
                </div>
                <RegionChooser metadata={landing.metadata} />
              </div>
            ) : null}
          </div>
          <div className="tq-home-visual">
            <Image
              alt=""
              className="tq-home-visual__image"
              fill
              priority
              sizes="(max-width: 768px) 100vw, 48vw"
              src="/demo/community-gathering.png"
            />
            <div className="tq-home-visual__caption">
              <span aria-hidden="true">●</span>
              <p>{t("home.region.body")}</p>
            </div>
          </div>
        </Container>
      </section>

      <Container className="tq-landing-sections">
        {landing.unavailable ? (
          <DiscoveryError labels={stateLabels} locale={locale} />
        ) : null}
        {landing.metadata ? (
          <section aria-labelledby="categories-title" className="tq-category-section">
            <div className="tq-landing-section-heading">
              <div>
                <h2 id="categories-title">{t("home.categories")}</h2>
              </div>
              <ActionLink href="/explore" variant="secondary">
                {t("shell.navigation.explore")}
              </ActionLink>
            </div>
            <nav
              aria-label={t("home.categories")}
              className="tq-category-links"
            >
              {landing.metadata.categories.map((category) => (
                <a
                  href={`/explore?category=${encodeURIComponent(category.slug ?? "")}`}
                  key={category.slug}
                >
                  <span aria-hidden="true" className="tq-category-links__icon">
                    {categoryGlyph(category.slug ?? "")}
                  </span>
                  <span>
                    {catalogLabel(category.name_key, t, category.slug)}
                  </span>
                  <span aria-hidden="true" className="tq-category-links__arrow">
                    →
                  </span>
                </a>
              ))}
            </nav>
          </section>
        ) : null}

        <section aria-labelledby="featured-title" className="tq-featured-section">
          <div className="tq-landing-section-heading">
            <div>
              <h2 id="featured-title">{t("discovery.featured")}</h2>
              <p>{t("discovery.featuredExplanation")}</p>
            </div>
            <ActionLink href="/explore" variant="secondary">
              {t("shell.navigation.explore")}
            </ActionLink>
          </div>
          {landing.featuredEvents.length ? (
            <div className="tq-landing-grid">
              {landing.featuredEvents.map((event) => (
                <EventCard
                  event={event}
                  key={event.id}
                  labels={eventLabels}
                  locale={locale}
                  showSave
                />
              ))}
            </div>
          ) : (
            <DiscoveryEmpty labels={stateLabels} locale={locale} />
          )}
        </section>

        <section aria-labelledby="clubs-title">
          <h2 id="clubs-title">{t("home.popularClubs")}</h2>
          {landing.popularClubs.length ? (
            <div className="tq-landing-grid">
              {landing.popularClubs.map((club) => (
                <ClubCard
                  club={club}
                  key={club.id}
                  labels={{ location: t("discovery.meetingArea") }}
                  locale={locale}
                />
              ))}
            </div>
          ) : (
            <DiscoveryEmpty labels={stateLabels} locale={locale} />
          )}
        </section>

        <Card aria-labelledby="organizer-title" className="tq-organizer-callout" id="about">
          <div>
            <h2 id="organizer-title">{t("home.organizer.title")}</h2>
            <p>{t("home.organizer.body")}</p>
          </div>
          <ActionLink href="/profile">{t("home.organizer.action")}</ActionLink>
        </Card>
      </Container>
    </PublicShell>
  );
}

function RegionChooser({ metadata }: { metadata: Metadata }) {
  const { t } = useLocale();
  return (
    <form
      action="/explore"
      aria-label={t("home.region.title")}
      className="tq-region-form"
      method="get"
    >
      <label>
        {t("filters.country")}
        <select defaultValue="" name="country">
          <option value="">{t("regions.chooseCountry")}</option>
          {metadata.countries.map((country) => (
            <option key={country.code} value={country.code}>
              {catalogLabel(country.name_key, t, country.code)}
            </option>
          ))}
        </select>
      </label>
      <label>
        {t("filters.city")}
        <select defaultValue="" name="city">
          <option value="">{t("regions.chooseCity")}</option>
          {metadata.cities.map((city) => (
            <option key={city.slug} value={city.slug}>
              {catalogLabel(city.name_key, t, city.slug)}
            </option>
          ))}
        </select>
      </label>
      <button className="tq-discovery-control" type="submit">
        {t("home.region.action")}
      </button>
    </form>
  );
}

function catalogLabel(
  key: string | undefined,
  t: (key: TranslationKey) => string,
  fallback?: string,
): string {
  if (key) {
    const label = t(key as TranslationKey);
    if (label && label !== t("filters.category")) return label;
  }
  return fallback ? humanize(fallback) : t("filters.category");
}

function categoryGlyph(slug: string): string {
  const glyphs: Record<string, string> = {
    "arts-culture": "✦",
    games: "◆",
    "language-exchange": "◌",
    outdoors: "⌁",
    sports: "◒",
    technology: "⌘",
  };
  return glyphs[slug] ?? "✦";
}

function humanize(value: string): string {
  return value
    .replaceAll("-", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function LocalizedHome({
  initialLocale,
  landing = emptyLanding,
}: {
  initialLocale: LocaleCode;
  landing?: LandingData;
}) {
  return (
    <LocaleProvider initialLocale={initialLocale}>
      <HomeContent landing={landing} />
    </LocaleProvider>
  );
}
