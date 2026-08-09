"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import {
  formatNumber,
  translate,
  type TranslationKey,
} from "@talaqi/translations";
import { Button, Card } from "@talaqi/ui";

import {
  createOrganizerClient,
  type Attendee,
  type AttendeeSummary,
  type RegistrationState,
} from "@/lib/api/organizer-client";
import { useLocale } from "@/lib/locale/locale-context";

function csrfToken(): string | undefined {
  const entry = document.cookie
    .split(";")
    .map((value) => value.trim())
    .find((value) => value.startsWith("talaqi_csrf="));
  return entry
    ? decodeURIComponent(entry.slice("talaqi_csrf=".length))
    : undefined;
}

const client = () =>
  createOrganizerClient({ baseUrl: "/api/organizer", csrfToken: csrfToken() });

const states = [
  "confirmed",
  "cash_pending",
  "waitlisted",
  "cancelled",
  "expired",
] as const;

export function AttendeeWorkspace({
  eventId,
  capacity,
}: {
  eventId: string;
  capacity: number | null;
}) {
  const { locale } = useLocale();
  const [items, setItems] = useState<Attendee[]>([]);
  const [summary, setSummary] = useState<AttendeeSummary | null>(null);
  const [state, setState] = useState<RegistrationState>(null);
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState<{
    state: RegistrationState;
    search: string;
  }>({
    state: null,
    search: "",
  });
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [failure, setFailure] = useState<TranslationKey | null>(null);
  const [notice, setNotice] = useState<TranslationKey | null>(null);
  const [actingId, setActingId] = useState<string | null>(null);

  const load = useCallback(
    async (append = false, nextCursor?: string) => {
      setLoading(true);
      setFailure(null);
      const api = client();
      const [page, totals] = await Promise.all([
        api.listAttendees(eventId, {
          ...(filters.state ? { state: filters.state } : {}),
          ...(filters.search ? { search: filters.search } : {}),
          ...(nextCursor ? { cursor: nextCursor } : {}),
        }),
        api.getAttendeeSummary(eventId),
      ]);
      if (!page.ok) setFailure(page.key);
      else {
        setItems((current) =>
          append ? [...current, ...page.data.items] : page.data.items,
        );
        setCursor(page.data.next_cursor);
      }
      if (!totals.ok) setFailure(totals.key);
      else setSummary(totals.data);
      setLoading(false);
    },
    [eventId, filters],
  );

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [eventId, load]);

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice(null);
    setFilters({ state, search: search.trim() });
  }

  async function confirm(attendee: Attendee) {
    setActingId(attendee.registration_id);
    setFailure(null);
    const result = await client().confirmCash(
      eventId,
      attendee.registration_id,
    );
    if (!result.ok) setFailure(result.key);
    else {
      setNotice("events.attendees.confirmedNotice");
      await load();
    }
    setActingId(null);
  }

  async function requestExport() {
    setFailure(null);
    const result = await client().requestAttendeeExport(eventId, {
      ...(filters.state ? { state: filters.state } : {}),
      ...(filters.search ? { search: filters.search } : {}),
    });
    setNotice(result.ok ? "events.attendees.exportQueued" : null);
    if (!result.ok) setFailure(result.key);
  }

  return (
    <Card aria-label={translate(locale, "events.attendees.title")}>
      <h2>{translate(locale, "events.attendees.title")}</h2>
      {summary ? (
        <dl className="tq-attendee-summary">
          <div>
            <dt>{translate(locale, "events.attendees.capacity")}</dt>
            <dd>
              {formatNumber(summary.held, locale)} /{" "}
              {capacity === null
                ? translate(locale, "discovery.unlimited")
                : formatNumber(capacity, locale)}
            </dd>
          </div>
          <div>
            <dt>{translate(locale, "events.attendees.confirmed")}</dt>
            <dd>{formatNumber(summary.confirmed, locale)}</dd>
          </div>
          <div>
            <dt>{translate(locale, "events.attendees.cashPending")}</dt>
            <dd>{formatNumber(summary.cash_pending, locale)}</dd>
          </div>
          <div>
            <dt>{translate(locale, "events.attendees.waitlisted")}</dt>
            <dd>{formatNumber(summary.waitlisted, locale)}</dd>
          </div>
        </dl>
      ) : null}

      <form className="tq-attendee-filters" onSubmit={applyFilters}>
        <label>
          {translate(locale, "events.attendees.search")}
          <input
            value={search}
            maxLength={80}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
        <label>
          {translate(locale, "events.attendees.state")}
          <select
            value={state ?? ""}
            onChange={(event) =>
              setState((event.target.value || null) as RegistrationState)
            }
          >
            <option value="">
              {translate(locale, "events.attendees.allStates")}
            </option>
            {states.map((value) => (
              <option key={value} value={value}>
                {translate(locale, `events.attendees.state.${value}`)}
              </option>
            ))}
          </select>
        </label>
        <Button type="submit">
          {translate(locale, "events.attendees.apply")}
        </Button>
        <Button type="button" onClick={() => void requestExport()}>
          {translate(locale, "events.attendees.export")}
        </Button>
      </form>

      <p className="tq-attendee-notice" aria-live="polite">
        {failure
          ? translate(locale, failure)
          : notice
            ? translate(locale, notice)
            : ""}
      </p>
      {loading && items.length === 0 ? (
        <p role="status">{translate(locale, "states.loading")}</p>
      ) : null}
      {!loading && items.length === 0 && !failure ? (
        <p>{translate(locale, "events.attendees.empty")}</p>
      ) : null}
      {items.length ? (
        <div className="tq-attendee-table-wrap">
          <table className="tq-attendee-table">
            <thead>
              <tr>
                <th>{translate(locale, "events.attendees.member")}</th>
                <th>{translate(locale, "events.attendees.state")}</th>
                <th>{translate(locale, "events.attendees.method")}</th>
                <th>{translate(locale, "events.attendees.action")}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((attendee) => (
                <tr key={attendee.registration_id}>
                  <td data-label={translate(locale, "events.attendees.member")}>
                    <strong>{attendee.display_name}</strong>
                    <small>@{attendee.username}</small>
                  </td>
                  <td data-label={translate(locale, "events.attendees.state")}>
                    {translate(
                      locale,
                      `events.attendees.state.${attendee.state}`,
                    )}
                  </td>
                  <td data-label={translate(locale, "events.attendees.method")}>
                    {translate(
                      locale,
                      attendee.method === "free"
                        ? "discovery.free"
                        : "discovery.cash",
                    )}
                  </td>
                  <td data-label={translate(locale, "events.attendees.action")}>
                    {attendee.state === "cash_pending" ? (
                      <Button
                        disabled={actingId === attendee.registration_id}
                        type="button"
                        onClick={() => void confirm(attendee)}
                      >
                        {translate(locale, "events.attendees.confirmCash")}
                      </Button>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {cursor ? (
        <Button
          disabled={loading}
          type="button"
          onClick={() => void load(true, cursor)}
        >
          {translate(locale, "events.attendees.loadMore")}
        </Button>
      ) : null}
    </Card>
  );
}
