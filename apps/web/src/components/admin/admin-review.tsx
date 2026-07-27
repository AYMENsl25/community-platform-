"use client";

import type { TranslationKey } from "@talaqi/translations";
import Link from "next/link";
import { useMemo, useState, type FormEvent } from "react";

import {
  createAdminClient,
  type AdminResult,
  type ModerationCaseSummary,
  type ModerationTargetSummary,
  type ModerationTargetType,
} from "@/lib/api/admin-client";
import { useLocale } from "@/lib/locale/locale-context";

type Feedback = { key: TranslationKey; requestId?: string };

function csrfToken(): string | undefined {
  const value = document.cookie
    .split(";")
    .map((item) => item.trim())
    .find((item) => item.startsWith("talaqi_csrf="));
  return value
    ? decodeURIComponent(value.slice("talaqi_csrf=".length))
    : undefined;
}

export function AdminReview({
  initialCases,
  initialError,
}: {
  initialCases: ModerationCaseSummary[];
  initialError?: Feedback;
}) {
  const { t } = useLocale();
  const [results, setResults] = useState<ModerationTargetSummary[]>([]);
  const [feedback, setFeedback] = useState<Feedback | undefined>(initialError);
  const [busy, setBusy] = useState(false);
  const client = useMemo(
    () => createAdminClient({ baseUrl: "/api/admin", csrfToken: csrfToken() }),
    [],
  );
  const canSearch = !initialError;

  function fail(result: Extract<AdminResult<unknown>, { ok: false }>) {
    setFeedback({
      key: result.key,
      ...(result.requestId ? { requestId: result.requestId } : {}),
    });
  }

  async function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const query = String(form.get("query") ?? "").trim();
    const type = String(form.get("target_type")) as ModerationTargetType;
    if (!query) return;
    setBusy(true);
    setFeedback(undefined);
    const result = await client.searchModerationTargets(query, type);
    setBusy(false);
    if (!result.ok) return fail(result);
    setResults(result.data.items);
  }

  return (
    <section className="tq-admin" aria-labelledby="admin-review-title">
      <header className="tq-admin__header">
        <div>
          <h1 id="admin-review-title">{t("admin.review.title")}</h1>
          <p>{t("admin.review.lead")}</p>
        </div>
      </header>
      {feedback ? (
        <div className="tq-admin-alert" role="alert">
          <p>{t(feedback.key)}</p>
          {feedback.requestId ? <code>{feedback.requestId}</code> : null}
        </div>
      ) : null}
      {initialCases.some((item) => item.is_emergency) ? (
        <aside className="tq-admin-emergency" role="alert">
          <strong>{t("admin.emergency.title")}</strong>
          <p>{t("admin.emergency.notice")}</p>
        </aside>
      ) : null}
      <div className="tq-admin__grid">
        <section className="tq-admin-card" aria-labelledby="case-queue-title">
          <h2 id="case-queue-title">{t("admin.review.queue")}</h2>
          {initialCases.length ? (
            <ul className="tq-admin-list">
              {initialCases.map((item) => (
                <li key={item.id}>
                  <div className="tq-admin-card__heading">
                    <div>
                      <strong>{item.target.display_name}</strong>
                      <p>
                        {t(`admin.category.${item.category}` as TranslationKey)}
                      </p>
                    </div>
                    <span className="tq-admin-badge">
                      {t(`admin.priority.${item.priority}` as TranslationKey)}
                    </span>
                  </div>
                  <Link href={`/admin/review/${item.id}`}>
                    {t("admin.review.open")}
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <p>{t("admin.review.empty")}</p>
          )}
        </section>
        {canSearch ? (
          <section
            className="tq-admin-card"
            aria-labelledby="target-search-title"
          >
            <h2 id="target-search-title">{t("admin.search.title")}</h2>
            <form className="tq-admin-search" onSubmit={search}>
              <label>
                {t("admin.search.type")}
                <select name="target_type">
                  <option value="user">{t("admin.target.user")}</option>
                  <option value="club">{t("admin.target.club")}</option>
                  <option value="event">{t("admin.target.event")}</option>
                </select>
              </label>
              <label>
                {t("admin.search.query")}
                <input name="query" required />
              </label>
              <button disabled={busy} type="submit">
                {t("admin.search.submit")}
              </button>
            </form>
            {results.length ? (
              <ul className="tq-admin-search-results" aria-live="polite">
                {results.map((item) => (
                  <li key={item.id}>
                    <strong>{item.display_name}</strong>
                    <span>{item.secondary_text}</span>
                  </li>
                ))}
              </ul>
            ) : null}
          </section>
        ) : null}
      </div>
    </section>
  );
}
