import { AdminReview } from "@/components/admin/admin-review";
import { AdminShell } from "@/components/shell/shells";
import { createServerAdminClient } from "@/lib/api/server-admin-client";
import { resolveRequestLocale } from "@/lib/locale/request-locale";

export const dynamic = "force-dynamic";

export default async function AdminReviewPage() {
  const locale = await resolveRequestLocale();
  const client = await createServerAdminClient();
  const result = await client.listModerationCases();
  return (
    <AdminShell currentHref="/admin/review" locale={locale}>
      <AdminReview
        initialCases={result.ok ? result.data.items : []}
        {...(result.ok
          ? {}
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
