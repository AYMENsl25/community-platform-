import { AdminCaseDetail } from "@/components/admin/admin-case-detail";
import { AdminShell } from "@/components/shell/shells";
import { createServerAdminClient } from "@/lib/api/server-admin-client";
import { resolveRequestLocale } from "@/lib/locale/request-locale";

export const dynamic = "force-dynamic";

export default async function AdminCasePage({
  params,
}: {
  params: Promise<{ caseId: string }>;
}) {
  const locale = await resolveRequestLocale();
  const { caseId } = await params;
  const client = await createServerAdminClient();
  const result = await client.getModerationCase(caseId);
  return (
    <AdminShell currentHref="/admin/review" locale={locale}>
      <AdminCaseDetail
        {...(result.ok
          ? { initialCase: result.data }
          : {
              initialError: {
                key: result.key,
                ...(result.requestId ? { requestId: result.requestId } : {}),
              },
            })}
      />
    </AdminShell>
  );
}
