import type { Metadata } from "next";
import { notFound } from "next/navigation";
import {
  formatNumber,
  LOCALE_CODES,
  translate,
  type LocaleCode,
} from "@talaqi/translations";
import { Card, Container } from "@talaqi/ui";
import { ClubCard } from "@/components/discovery/club-card";
import { MemberCommunications } from "@/components/communications/member-communications";
import { EventCard } from "@/components/discovery/event-card";
import { DiscoveryError } from "@/components/discovery/result-states";
import { PublicShell } from "@/components/shell/shells";
import { createServerPublicClient } from "@/lib/api/server-public-client";
import { resolveRequestLocale } from "@/lib/locale/request-locale";

type Props = {
  params: Promise<{ slug: string }>;
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
  const { slug } = await params;
  const result = await (await createServerPublicClient()).getClub(slug);
  if (!result.ok)
    return {
      title: "Talaqi",
      robots: { index: false, follow: false },
    };
  const path = `/clubs/${result.data.slug}`;
  const image = result.data.cover_media_id
    ? publicUrl(`/api/media/${result.data.cover_media_id}`)
    : undefined;
  return {
    title: result.data.name,
    description: result.data.description,
    alternates: { canonical: publicUrl(path), languages: alternates(path) },
    robots: { index: true, follow: true },
    openGraph: {
      type: "website",
      title: result.data.name,
      description: result.data.description,
      url: publicUrl(path),
      ...(image ? { images: [{ url: image, alt: result.data.name }] } : {}),
    },
  };
}

export default async function ClubPage({ params, searchParams }: Props) {
  const [locale, client, { slug }] = await Promise.all([
    pageLocale(searchParams),
    createServerPublicClient(),
    params,
  ]);
  const result = await client.getClub(slug);
  if (!result.ok && result.status === 404) notFound();
  return (
    <PublicShell currentHref={`/clubs/${slug}`} locale={locale}>
      <Container>
        {!result.ok ? (
          <DiscoveryError
            labels={{
              error: translate(locale, "states.error"),
              retry: translate(locale, "states.retry"),
            }}
            locale={locale}
          />
        ) : (
          <>
            <ClubCard
              club={result.data}
              labels={{ location: translate(locale, "discovery.meetingArea") }}
              locale={locale}
            />
            <MemberCommunications
              kind="club"
              resourceId={result.data.id}
              locale={locale}
            />
            <Card className="tq-public-detail__trust">
              <p>
                {formatNumber(result.data.member_count, locale)}{" "}
                {translate(locale, "discovery.members")}
              </p>
              <p>{translate(locale, "discovery.clubOrganized")}</p>
            </Card>
            <section aria-labelledby="club-events-title">
              <h2 id="club-events-title">
                {translate(locale, "discovery.clubEvents")}
              </h2>
              {result.data.events.length ? (
                <div className="tq-public-detail__related">
                  {result.data.events.map((event) => (
                    <EventCard
                      event={event}
                      key={event.id}
                      locale={locale}
                      showSave
                    />
                  ))}
                </div>
              ) : (
                <p>{translate(locale, "discovery.noClubEvents")}</p>
              )}
            </section>
          </>
        )}
      </Container>
    </PublicShell>
  );
}
