"use client";

import type { AdminAuditEvent } from "@/lib/api/admin-client";
import { useLocale } from "@/lib/locale/locale-context";

export function AdminAudit({ events }: { events: AdminAuditEvent[] }) {
  const { t } = useLocale();
  return (
    <section className="tq-admin" aria-labelledby="admin-audit-title">
      <header>
        <h1 id="admin-audit-title">{t("admin.audit.title")}</h1>
        <p>{t("admin.audit.lead")}</p>
      </header>
      <section className="tq-admin-card">
        {events.length ? (
          <ul className="tq-admin-history">
            {events.map((event) => (
              <li key={event.id}>
                <strong>{event.action}</strong>
                <p>
                  {event.target_type}: {event.target_id ?? "—"}
                  {" — "}
                  {event.actor_user_id ?? event.actor_kind}
                </p>
                {event.reason ? <p>{event.reason}</p> : null}
                <small>{event.created_at}</small>
                {event.request_id ? (
                  <p>
                    {t("admin.audit.requestId")}:{" "}
                    <code>{event.request_id}</code>
                  </p>
                ) : null}
                <dl>
                  {Object.entries(
                    event.safe_after ?? event.safe_before ?? {},
                  ).map(([key, value]) => (
                    <div key={key}>
                      <dt>{key}</dt>
                      <dd>{String(value)}</dd>
                    </div>
                  ))}
                </dl>
              </li>
            ))}
          </ul>
        ) : (
          <p>{t("admin.audit.empty")}</p>
        )}
      </section>
    </section>
  );
}
