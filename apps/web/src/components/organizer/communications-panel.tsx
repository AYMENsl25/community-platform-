"use client";

import type { TranslationKey } from "@talaqi/translations";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Button, Card } from "@talaqi/ui";

import {
  createOrganizerClient,
  type PublishedContent,
} from "@/lib/api/organizer-client";
import { useLocale } from "@/lib/locale/locale-context";

type Kind = "club" | "event";

function csrfToken(): string | undefined {
  if (typeof document === "undefined") return undefined;
  const entry = document.cookie
    .split(";")
    .map((value) => value.trim())
    .find((value) => value.startsWith("talaqi_csrf="));
  return entry
    ? decodeURIComponent(entry.slice("talaqi_csrf=".length))
    : undefined;
}

export function CommunicationsPanel({
  kind,
  resourceId,
  canPublish = true,
  revision,
}: {
  kind: Kind;
  resourceId: string;
  canPublish?: boolean;
  revision?: number;
}) {
  const { t, locale } = useLocale();
  const [items, setItems] = useState<PublishedContent[]>([]);
  const [failure, setFailure] = useState<string>();
  const [busy, setBusy] = useState(false);
  const client = useMemo(
    () =>
      createOrganizerClient({
        baseUrl: "/api/organizer",
        csrfToken: csrfToken(),
      }),
    [],
  );

  useEffect(() => {
    let active = true;
    const load =
      kind === "club"
        ? client.listClubAnnouncements(resourceId)
        : client.listEventUpdates(resourceId);
    void load.then((result) => {
      if (!active) return;
      if (result.ok) setItems(result.data.items);
      else if (canPublish || result.status !== 401) setFailure(t(result.key));
    });
    return () => {
      active = false;
    };
  }, [canPublish, client, kind, resourceId, t]);

  async function publish(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const value = {
      title: String(form.get("title") ?? "").trim(),
      body: String(form.get("body") ?? "").trim(),
      audience: String(form.get("audience") ?? ""),
    };
    setBusy(true);
    setFailure(undefined);
    const result =
      kind === "club"
        ? await client.createClubAnnouncement(resourceId, {
            ...value,
            audience: value.audience as "all_members" | "admins",
          })
        : await client.createEventUpdate(resourceId, {
            ...value,
            audience: value.audience as
              "all_active" | "confirmed" | "cash_pending" | "waitlisted",
            revision: revision ?? 0,
          });
    setBusy(false);
    if (!result.ok) return setFailure(t(result.key));
    setItems((current) => [
      result.data,
      ...current.filter((item) => item.id !== result.data.id),
    ]);
    formElement.reset();
  }

  const audiences: [string, TranslationKey][] =
    kind === "club"
      ? [
          ["all_members", "communications.audience.allMembers"],
          ["admins", "communications.audience.admins"],
        ]
      : [
          ["all_active", "communications.audience.allActive"],
          ["confirmed", "communications.audience.confirmed"],
          ["cash_pending", "communications.audience.cashPending"],
          ["waitlisted", "communications.audience.waitlisted"],
        ];

  return (
    <Card
      className="tq-organizer-card"
      aria-labelledby={`${kind}-communications-title`}
    >
      <h2 id={`${kind}-communications-title`}>
        {t(
          kind === "club"
            ? "communications.club.title"
            : "communications.event.title",
        )}
      </h2>
      {canPublish ? <p>{t("communications.help")}</p> : null}
      {failure ? <p role="alert">{failure}</p> : null}
      {canPublish ? (
        <form onSubmit={publish}>
          <label>
            {t("communications.subject")}
            <input name="title" required maxLength={160} />
          </label>
          <label>
            {t("communications.body")}
            <textarea name="body" required maxLength={10000} />
          </label>
          <label>
            {t("communications.audience")}
            <select name="audience">
              {audiences.map(([value, key]) => (
                <option key={value} value={value}>
                  {t(key)}
                </option>
              ))}
            </select>
          </label>
          <Button disabled={busy} type="submit">
            {t("communications.publish")}
          </Button>
        </form>
      ) : null}
      <h3>{t("communications.history")}</h3>
      {items.length === 0 ? (
        <p>{t("communications.empty")}</p>
      ) : (
        <ul>
          {items.map((item) => (
            <li key={item.id}>
              <strong>{item.title}</strong>
              <p>{item.body}</p>
              <small>
                {new Intl.DateTimeFormat(locale, {
                  dateStyle: "medium",
                  timeStyle: "short",
                }).format(new Date(item.published_at))}
              </small>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
