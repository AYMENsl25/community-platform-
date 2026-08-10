"use client";

import { useEffect, useState } from "react";
import type { components } from "@talaqi/api-client";
import {
  API_MESSAGE_KEYS,
  translate,
  type LocaleCode,
  type TranslationKey,
} from "@talaqi/translations";
import { Card } from "@talaqi/ui";

type EventDetail = components["schemas"]["EventAudienceResponse"];

function csrfToken(): string | undefined {
  const entry = document.cookie
    .split(";")
    .map((value) => value.trim())
    .find((value) => value.startsWith("talaqi_csrf="));
  return entry
    ? decodeURIComponent(entry.slice("talaqi_csrf=".length))
    : undefined;
}

function messageKey(value: unknown): TranslationKey | undefined {
  if (!value || typeof value !== "object" || !("error" in value)) return;
  const error = value.error;
  if (!error || typeof error !== "object" || !("message_key" in error)) return;
  const key = error.message_key;
  return typeof key === "string" &&
    (API_MESSAGE_KEYS as readonly string[]).includes(key)
    ? (key as TranslationKey)
    : undefined;
}

function remaining(deadline: string, locale: LocaleCode, now: number): string {
  const milliseconds = Math.max(0, new Date(deadline).getTime() - now);
  if (milliseconds === 0) return translate(locale, "registration.expired");
  const minutes = Math.ceil(milliseconds / 60_000);
  const formatter = new Intl.RelativeTimeFormat(locale, { numeric: "always" });
  return minutes >= 60
    ? formatter.format(Math.ceil(minutes / 60), "hour")
    : formatter.format(minutes, "minute");
}

export function MemberRegistrationPanel({
  initialEvent,
  locale,
}: {
  initialEvent: EventDetail;
  locale: LocaleCode;
}) {
  const [event, setEvent] = useState(initialEvent);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<TranslationKey | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const deadline = event.registration_cash_expires_at;

  useEffect(() => {
    if (!deadline) return;
    const timer = window.setInterval(() => setNow(Date.now()), 30_000);
    return () => window.clearInterval(timer);
  }, [deadline]);

  async function mutate(method: "POST" | "DELETE") {
    setPending(true);
    setError(null);
    const base = `/api/public/api/v1/events/${encodeURIComponent(event.id)}`;
    const mutationPath =
      method === "POST" ? `${base}/registrations` : `${base}/registrations/me`;
    try {
      const csrf = csrfToken();
      const response = await fetch(mutationPath, {
        method,
        credentials: "same-origin",
        cache: "no-store",
        headers: {
          ...(csrf ? { "X-CSRF-Token": csrf } : {}),
          "Idempotency-Key": crypto.randomUUID(),
        },
      });
      if (!response.ok) {
        const body: unknown = await response.json().catch(() => null);
        setError(
          response.status === 401
            ? "registration.authRequired"
            : (messageKey(body) ?? "registration.tryAgain"),
        );
        return;
      }
      const refreshed = await fetch(base, {
        method: "GET",
        credentials: "same-origin",
        cache: "no-store",
      });
      if (!refreshed.ok) {
        setError("registration.refreshFailed");
        return;
      }
      setEvent((await refreshed.json()) as EventDetail);
    } catch {
      setError("registration.tryAgain");
    } finally {
      setPending(false);
    }
  }

  const active = ["confirmed", "cash_pending", "waitlisted"].includes(
    event.registration_state ?? "",
  );
  const isFull = event.available_places === 0;
  const mapQuery = event.exact_address
    ? [event.exact_address, event.city_slug, event.country_code]
    : [event.district, event.city_slug, event.country_code];
  const mapHref = `https://www.openstreetmap.org/search?query=${encodeURIComponent(
    mapQuery.filter(Boolean).join(", "),
  )}`;

  return (
    <div className="tq-registration-layout">
      <Card aria-label={translate(locale, "registration.title")}>
        <h2>{translate(locale, "registration.title")}</h2>
        {event.registration_state === "confirmed" ? (
          <>
            <h3>{translate(locale, "registration.confirmed")}</h3>
            <p>{translate(locale, "registration.confirmedBody")}</p>
          </>
        ) : null}
        {event.registration_state === "cash_pending" ? (
          <>
            <h3>{translate(locale, "registration.cashPending")}</h3>
            <p>{translate(locale, "registration.cashInstructions")}</p>
            {deadline ? (
              <dl className="tq-registration-deadline">
                <div>
                  <dt>{translate(locale, "registration.expires")}</dt>
                  <dd>
                    <time dateTime={deadline}>
                      {new Intl.DateTimeFormat(locale, {
                        dateStyle: "medium",
                        timeStyle: "short",
                      }).format(new Date(deadline))}
                    </time>
                  </dd>
                </div>
                <div>
                  <dt>{translate(locale, "registration.remaining")}</dt>
                  <dd>{remaining(deadline, locale, now)}</dd>
                </div>
              </dl>
            ) : null}
          </>
        ) : null}
        {event.registration_state === "waitlisted" ? (
          <>
            <h3>{translate(locale, "registration.waitlisted")}</h3>
            <p>{translate(locale, "registration.waitlistedBody")}</p>
          </>
        ) : null}
        <button
          className="tq-discovery-control"
          type="button"
          disabled={pending}
          onClick={() => void mutate(active ? "DELETE" : "POST")}
        >
          {pending
            ? translate(locale, "registration.processing")
            : translate(
                locale,
                active
                  ? "registration.cancel"
                  : isFull
                    ? "registration.joinWaitlist"
                    : "registration.register",
              )}
        </button>
        <p className="tq-registration-status" aria-live="polite">
          {error ? translate(locale, error) : ""}
        </p>
      </Card>
      <Card aria-label={translate(locale, "discovery.meetingArea")}>
        <h2>
          {event.exact_address
            ? translate(locale, "registration.venue")
            : translate(locale, "discovery.meetingArea")}
        </h2>
        <p>
          {event.exact_address ?? translate(locale, "discovery.privateVenue")}
        </p>
        <a href={mapHref} rel="noreferrer" target="_blank">
          {translate(locale, "discovery.openMap")}
        </a>
      </Card>
    </div>
  );
}
