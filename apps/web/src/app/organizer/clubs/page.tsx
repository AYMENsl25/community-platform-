import { OrganizerShell } from "@/components/shell/shells";
import { ClubWorkspace } from "@/components/organizer/club-workspace";
import { createServerOrganizerClient } from "@/lib/api/server-organizer-client";
import { resolveRequestLocale } from "@/lib/locale/request-locale";

export const dynamic = "force-dynamic";

export default async function OrganizerClubsPage() {
  const locale = await resolveRequestLocale();
  const client = await createServerOrganizerClient();
  const clubsResult = await client.listManagedClubs();
  const clubs = clubsResult.ok ? clubsResult.data.items : [];
  const selected = clubs[0];
  const canManage = selected?.capabilities.includes("manage_members") ?? false;
  const [membersResult, requestsResult] =
    selected && canManage
      ? await Promise.all([
          client.listMembers(selected.id),
          client.listRequests(selected.id),
        ])
      : [undefined, undefined];
  const failedResult = !clubsResult.ok
    ? clubsResult
    : membersResult && !membersResult.ok
      ? membersResult
      : requestsResult && !requestsResult.ok
        ? requestsResult
        : undefined;
  return (
    <OrganizerShell currentHref="/organizer/clubs" locale={locale}>
      <ClubWorkspace
        initialClubs={clubs}
        initialMembers={membersResult?.ok ? membersResult.data.items : []}
        initialRequests={requestsResult?.ok ? requestsResult.data.items : []}
        {...(!failedResult
          ? {}
          : {
              initialError: {
                key: failedResult.key,
                ...(failedResult.requestId
                  ? { requestId: failedResult.requestId }
                  : {}),
              },
            })}
      />
    </OrganizerShell>
  );
}
