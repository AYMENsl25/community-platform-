import { EventWorkspace } from "@/components/organizer/event-workspace";
import { OrganizerShell } from "@/components/shell/shells";
import { createServerOrganizerClient } from "@/lib/api/server-organizer-client";
import { createServerPublicClient } from "@/lib/api/server-public-client";
import { resolveRequestLocale } from "@/lib/locale/request-locale";

export const dynamic = "force-dynamic";

export default async function OrganizerEventsPage() {
  const [locale, organizer, discovery] = await Promise.all([
    resolveRequestLocale(),
    createServerOrganizerClient(),
    createServerPublicClient(),
  ]);
  const [eventsResult, clubsResult, capabilitiesResult, metadataResult] =
    await Promise.all([
      organizer.listManagedEvents(),
      organizer.listManagedClubs(),
      organizer.getCapabilities(),
      discovery.getMetadata(),
    ]);
  const initialCountry = eventsResult.ok
    ? eventsResult.data.items[0]?.country_code
    : undefined;
  const policyResult = initialCountry
    ? await organizer.getRegionPolicy(initialCountry)
    : undefined;
  return (
    <OrganizerShell currentHref="/organizer/events" locale={locale}>
      <EventWorkspace
        initialEvents={eventsResult.ok ? eventsResult.data.items : []}
        initialPolicy={policyResult?.ok ? policyResult.data : undefined}
        managedClubs={clubsResult.ok ? clubsResult.data.items : []}
        capabilities={
          capabilitiesResult.ok
            ? capabilitiesResult.data
            : {
                create_club: false,
                create_independent_event: false,
                save_event: false,
                register_event: false,
                access_admin: false,
                blockers: ["account_unavailable"],
              }
        }
        metadata={
          metadataResult.ok
            ? {
                countries: metadataResult.data.countries.map((item) => ({
                  code: item.code ?? "",
                  name_key: item.name_key ?? "",
                })),
                cities: metadataResult.data.cities.map((item) => ({
                  slug: item.slug ?? "",
                  name_key: item.name_key ?? "",
                })),
                categories: metadataResult.data.categories.map((item) => ({
                  slug: item.slug ?? "",
                  name_key: item.name_key ?? "",
                })),
              }
            : { countries: [], cities: [], categories: [] }
        }
      />
    </OrganizerShell>
  );
}
