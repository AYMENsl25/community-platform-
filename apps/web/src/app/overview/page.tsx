import { DashboardWorkspace } from "@/components/dashboard/dashboard-workspace";
import { MemberShell } from "@/components/shell/shells";
import { resolveRequestLocale } from "@/lib/locale/request-locale";

export default async function MemberOverviewPage() {
  const locale = await resolveRequestLocale();
  return (
    <MemberShell currentHref="/overview" locale={locale}>
      <DashboardWorkspace role="member" locale={locale} />
    </MemberShell>
  );
}
