import {
  LocalizedHome,
  type LandingData,
} from "@/components/locale/localized-home";
import { createServerPublicClient } from "@/lib/api/server-public-client";
import { resolveRequestLocale } from "@/lib/locale/request-locale";

export default async function Home() {
  const [locale, client] = await Promise.all([
    resolveRequestLocale(),
    createServerPublicClient(),
  ]);
  const [metadata, events, clubs] = await Promise.all([
    client.getMetadata(),
    client.listEvents({ limit: 4 }),
    client.listClubs({ limit: 4 }),
  ]);
  const landing: LandingData = {
    metadata: metadata.ok ? metadata.data : null,
    featuredEvents: events.ok ? events.data.items : [],
    popularClubs: clubs.ok ? clubs.data.items : [],
    unavailable: !metadata.ok || !events.ok || !clubs.ok,
  };
  return <LocalizedHome initialLocale={locale} landing={landing} />;
}
