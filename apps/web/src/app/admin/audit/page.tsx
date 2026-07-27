import { AdminAudit } from "@/components/admin/admin-audit";
import { AdminShell } from "@/components/shell/shells";
import { createServerAdminClient } from "@/lib/api/server-admin-client";
import { resolveRequestLocale } from "@/lib/locale/request-locale";

export const dynamic = "force-dynamic";

export default async function AdminAuditPage() {
  const locale = await resolveRequestLocale();
  const client = await createServerAdminClient();
  const result = await client.listAuditEvents();
  return (
    <AdminShell currentHref="/admin/audit" locale={locale}>
      {result.ok ? (
        <AdminAudit events={result.data.items} />
      ) : (
        <div className="tq-admin-alert" role="alert">
          {result.key}
        </div>
      )}
    </AdminShell>
  );
}
