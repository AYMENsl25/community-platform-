import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { translate } from "@talaqi/translations";
import { Container } from "@talaqi/ui";
import { ClubCard } from "@/components/discovery/club-card";
import { EventCard } from "@/components/discovery/event-card";
import { DiscoveryError } from "@/components/discovery/result-states";
import { PublicShell } from "@/components/shell/shells";
import { createServerPublicClient } from "@/lib/api/server-public-client";
import { resolveRequestLocale } from "@/lib/locale/request-locale";
type Props = { params: Promise<{ slug: string }> };
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const result = await (
    await createServerPublicClient()
  ).getClub((await params).slug);
  return result.ok
    ? { title: result.data.name, description: result.data.description }
    : { title: "Talaqi" };
}
export default async function ClubPage({ params }: Props) {
  const [locale, client, { slug }] = await Promise.all([
    resolveRequestLocale(),
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
            <section aria-labelledby="club-events-title">
              <h2 id="club-events-title">
                {translate(locale, "discovery.clubEvents")}
              </h2>
              {result.data.events.map((event) => (
                <EventCard event={event} key={event.id} locale={locale} />
              ))}
            </section>
          </>
        )}
      </Container>
    </PublicShell>
  );
}
