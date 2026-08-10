import { DashboardWorkspace } from "@/components/dashboard/dashboard-workspace";
import { OrganizerShell } from "@/components/shell/shells";
import { resolveRequestLocale } from "@/lib/locale/request-locale";

export default async function OrganizerOverviewPage() {
  const locale = await resolveRequestLocale();
  return (
    <OrganizerShell currentHref="/organizer/overview" locale={locale}>
      <DashboardWorkspace role="organizer" locale={locale} />
    </OrganizerShell>
  );
}
