import { AdminOperations } from "@/components/admin/admin-operations";
import { AdminShell } from "@/components/shell/shells";
import { createServerAdminClient } from "@/lib/api/server-admin-client";
import { resolveRequestLocale } from "@/lib/locale/request-locale";

export const dynamic = "force-dynamic";

export default async function AdminOperationsPage() {
  const locale = await resolveRequestLocale();
  const client = await createServerAdminClient();
  const [flags, policy, outbox] = await Promise.all([
    client.listFeatureFlags(),
    client.getRegionPolicy("TR"),
    client.listOutboxEvents("permanent_failed"),
  ]);
  return (
    <AdminShell currentHref="/admin/operations" locale={locale}>
      {flags.ok && policy.ok && outbox.ok ? (
        <AdminOperations
          initialFlags={flags.data.items}
          initialPolicy={policy.data}
          initialOutbox={outbox.data.items}
        />
      ) : (
        <div className="tq-admin-alert" role="alert">
          {!flags.ok
            ? flags.key
            : !policy.ok
              ? policy.key
              : !outbox.ok
                ? outbox.key
                : "errors.internal"}
        </div>
      )}
    </AdminShell>
  );
}
