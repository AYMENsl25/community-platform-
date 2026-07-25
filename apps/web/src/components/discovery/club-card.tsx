import type { components } from "@talaqi/api-client";
import {
  translate,
  type LocaleCode,
  type TranslationKey,
} from "@talaqi/translations";
import "./discovery.css";
type Club = components["schemas"]["ClubCardResponse"];
export type ClubCardLabels = { location: string };

export function ClubCard({
  club,
  locale,
  labels,
}: {
  club: Club;
  locale: LocaleCode;
  labels?: Partial<ClubCardLabels>;
}) {
  const copy = { location: translate(locale, "filters.city"), ...labels };
  return (
    <article className="tq-discovery-card tq-club-card" lang={locale}>
      <p className="tq-discovery-card__eyebrow">
        {translate(
          locale,
          `categories.${club.category_slug}` as TranslationKey,
        ) || humanize(club.category_slug)}
      </p>
      <h3>
        <a href={`/clubs/${club.slug}`}>{club.name}</a>
      </h3>
      <p>{club.description}</p>
      <p>
        <span className="tq-visually-hidden">{copy.location}: </span>
        {translate(
          locale,
          `regions.city.${club.city_slug}` as TranslationKey,
        )}, {club.country_code.toUpperCase()}
      </p>
    </article>
  );
}

function humanize(value: string): string {
  return value
    .replaceAll("-", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}
