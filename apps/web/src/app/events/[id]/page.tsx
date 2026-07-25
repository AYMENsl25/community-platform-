import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { translate } from "@talaqi/translations";
import { Card, Container } from "@talaqi/ui";
import { EventCard } from "@/components/discovery/event-card";
import { DiscoveryError } from "@/components/discovery/result-states";
import { PublicShell } from "@/components/shell/shells";
import { createServerPublicClient } from "@/lib/api/server-public-client";
import { resolveRequestLocale } from "@/lib/locale/request-locale";
type Props = { params: Promise<{ id: string }> };
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const result = await (
    await createServerPublicClient()
  ).getEvent((await params).id);
  return result.ok
    ? { title: result.data.title, description: result.data.description }
    : { title: "Talaqi" };
}
export default async function EventPage({ params }: Props) {
  const [locale, client, { id }] = await Promise.all([
    resolveRequestLocale(),
    createServerPublicClient(),
    params,
  ]);
  const result = await client.getEvent(id);
  if (!result.ok && result.status === 404) notFound();
  return (
    <PublicShell currentHref={`/events/${id}`} locale={locale}>
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
            <EventCard event={result.data} locale={locale} />
            <Card aria-label={translate(locale, "discovery.meetingArea")}>
              <p>{translate(locale, "discovery.privateVenue")}</p>
              <h2>{translate(locale, "discovery.rules")}</h2>
              <p>{translate(locale, "discovery.cancellation")}</p>
            </Card>
          </>
        )}
      </Container>
    </PublicShell>
  );
}
