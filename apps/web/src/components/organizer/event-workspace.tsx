"use client";

import { useRef, useState, type FormEvent } from "react";
import { translate, type TranslationKey } from "@talaqi/translations";
import { Button, Card } from "@talaqi/ui";

import {
  createOrganizerClient,
  type Capabilities,
  type EventCreate,
  type EventPatch,
  type ManagedClub,
  type ManagedEvent,
  type RegionPolicy,
} from "@/lib/api/organizer-client";
import { useLocale } from "@/lib/locale/locale-context";

import "./organizer.css";

type Metadata = {
  countries: { code: string; name_key: string }[];
  cities: { slug: string; name_key: string }[];
  categories: { slug: string; name_key: string }[];
};

type Props = {
  initialEvents: ManagedEvent[];
  managedClubs: ManagedClub[];
  metadata: Metadata;
  capabilities: Capabilities;
  initialPolicy?: RegionPolicy;
};

const validationBlockerLabels: Partial<Record<string, TranslationKey>> = {
  description: "events.form.description",
  category_slug: "events.form.category",
  country_code: "events.form.country",
  city_slug: "events.form.city",
  start_at: "events.form.start",
  end_at: "events.form.end",
  time_zone: "events.form.timeZone",
  registration_method: "events.form.method",
  cancellation_cutoff_minutes: "events.form.cancellation",
  schedule: "events.form.start",
  coordinates: "events.form.latitude",
};

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

const client = () =>
  createOrganizerClient({
    baseUrl: "/api/organizer",
    csrfToken: csrfToken(),
  });

function inputDate(value: string | null): string {
  return value ? new Date(value).toISOString().slice(0, 16) : "";
}

function eventValues(event?: ManagedEvent) {
  return {
    title: event?.title ?? "",
    description: event?.description ?? "",
    category_slug: event?.category_slug ?? "",
    country_code: event?.country_code ?? "",
    city_slug: event?.city_slug ?? "",
    start_at: inputDate(event?.start_at ?? null),
    end_at: inputDate(event?.end_at ?? null),
    time_zone: event?.time_zone ?? "",
    capacity: event?.capacity?.toString() ?? "",
    visibility: event?.visibility ?? "public",
    registration_method: event?.registration_method ?? "free",
    cash_expiry_minutes: event?.cash_expiry_minutes?.toString() ?? "",
    cancellation_cutoff_minutes:
      event?.cancellation_cutoff_minutes?.toString() ?? "",
    district: event?.district ?? "",
    public_meeting_area: event?.public_meeting_area ?? "",
    exact_address: event?.exact_address ?? "",
    latitude: event?.latitude?.toString() ?? "",
    longitude: event?.longitude?.toString() ?? "",
    exact_venue_is_public: event?.exact_venue_is_public ?? false,
    cover_media_id: event?.cover_media_id ?? "",
  };
}

function optional(value: FormDataEntryValue | null): string | null {
  const normalized = String(value ?? "").trim();
  return normalized || null;
}

function numberValue(value: FormDataEntryValue | null): number | null {
  const normalized = optional(value);
  return normalized === null ? null : Number(normalized);
}

export function EventWorkspace({
  initialEvents,
  managedClubs,
  metadata,
  capabilities,
  initialPolicy,
}: Props) {
  const { locale } = useLocale();
  const [events, setEvents] = useState(initialEvents);
  const [selectedId, setSelectedId] = useState<string | null>(
    initialEvents[0]?.id ?? null,
  );
  const [creating, setCreating] = useState(initialEvents.length === 0);
  const [notice, setNotice] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [policy, setPolicy] = useState(initialPolicy);
  const [coverMediaId, setCoverMediaId] = useState<string | null>(
    initialEvents[0]?.cover_media_id ?? null,
  );
  const [uploadState, setUploadState] = useState<
    "pending" | "uploading" | "verified" | "failed"
  >("pending");
  const headingRef = useRef<HTMLHeadingElement>(null);
  const selected = events.find((event) => event.id === selectedId);

  const choose = (event: ManagedEvent) => {
    setSelectedId(event.id);
    setCoverMediaId(event.cover_media_id);
    setUploadState(event.cover_media_id ? "verified" : "pending");
    setCreating(false);
    setNotice(null);
    setFailure(null);
  };

  const replaceEvent = (event: ManagedEvent) => {
    setEvents((current) => [
      event,
      ...current.filter((item) => item.id !== event.id),
    ]);
    setSelectedId(event.id);
    setCreating(false);
    setCoverMediaId(event.cover_media_id);
    setUploadState(event.cover_media_id ? "verified" : "pending");
  };

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFailure(null);
    const form = new FormData(event.currentTarget);
    const owner = String(form.get("owner") ?? "independent");
    const submitter = (event.nativeEvent as SubmitEvent).submitter;
    const publish =
      submitter instanceof HTMLButtonElement && submitter.value === "publish";
    const common = {
      title: String(form.get("title") ?? ""),
      description: String(form.get("description") ?? ""),
      category_slug: optional(form.get("category_slug")),
      country_code: optional(form.get("country_code")),
      city_slug: optional(form.get("city_slug")),
      start_at: optional(form.get("start_at"))
        ? new Date(String(form.get("start_at"))).toISOString()
        : null,
      end_at: optional(form.get("end_at"))
        ? new Date(String(form.get("end_at"))).toISOString()
        : null,
      time_zone: optional(form.get("time_zone")),
      capacity: numberValue(form.get("capacity")),
      visibility: String(form.get("visibility")) as "public" | "private_link",
      registration_method: String(form.get("registration_method")) as
        "free" | "cash_organizer_confirmed",
      cash_expiry_minutes: numberValue(form.get("cash_expiry_minutes")),
      cancellation_cutoff_minutes: numberValue(
        form.get("cancellation_cutoff_minutes"),
      ),
      district: optional(form.get("district")),
      public_meeting_area: optional(form.get("public_meeting_area")),
      exact_address: optional(form.get("exact_address")),
      latitude: numberValue(form.get("latitude")),
      longitude: numberValue(form.get("longitude")),
      exact_venue_is_public: form.get("exact_venue_is_public") === "on",
      cover_media_id: coverMediaId,
      publish,
    };
    const result =
      creating || !selected
        ? await client().createEvent({
            ...common,
            ownership_type: owner === "independent" ? "independent" : "club",
            club_id: owner === "independent" ? null : owner.slice(5),
          } as EventCreate)
        : await client().updateEvent(selected.id, {
            ...common,
            revision: selected.revision,
          } as EventPatch);
    if (!result.ok) {
      setFailure(translate(locale, result.key));
      headingRef.current?.focus();
      return;
    }
    replaceEvent(result.data);
    setNotice(translate(locale, "events.workspace.saved"));
  }

  async function action(kind: "duplicate" | "cancel" | "complete" | "delete") {
    if (!selected) return;
    const api = client();
    const result =
      kind === "duplicate"
        ? await api.duplicateEvent(selected.id)
        : kind === "cancel"
          ? await api.cancelEvent(selected.id, selected.revision)
          : kind === "complete"
            ? await api.completeEvent(selected.id, selected.revision)
            : await api.deleteDraftEvent(selected.id, selected.revision);
    if (!result.ok) {
      setFailure(translate(locale, result.key));
      headingRef.current?.focus();
      return;
    }
    if (kind === "delete") {
      const remaining = events.filter((item) => item.id !== selected.id);
      setEvents(remaining);
      setSelectedId(remaining[0]?.id ?? null);
      setCreating(remaining.length === 0);
    } else {
      replaceEvent(result.data as ManagedEvent);
    }
    setNotice(translate(locale, "events.workspace.actionCompleted"));
  }

  async function reloadConflict() {
    if (!selected) return;
    const result = await client().getManagedEvent(selected.id);
    if (result.ok) {
      replaceEvent(result.data);
      setFailure(null);
      setNotice(translate(locale, "events.workspace.reloaded"));
      headingRef.current?.focus();
    }
  }
  async function loadPolicy(countryCode: string) {
    if (!countryCode) {
      setPolicy(undefined);
      return;
    }
    const result = await client().getRegionPolicy(countryCode);
    setPolicy(result.ok ? result.data : undefined);
  }

  const values = eventValues(creating ? undefined : selected);
  const cities = metadata.cities;
  async function uploadCover(file: File | undefined) {
    if (!file) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setFailure(translate(locale, "events.media.invalid"));
      return;
    }
    setUploadState("uploading");
    setFailure(null);
    const api = client();
    const intent = await api.createMediaUpload({
      original_filename: file.name,
      content_type: file.type as "image/jpeg" | "image/png" | "image/webp",
      byte_size: file.size,
    });
    if (!intent.ok) {
      setUploadState("failed");
      setFailure(translate(locale, intent.key));
      return;
    }
    try {
      const uploaded = await fetch(intent.data.upload.url, {
        method: intent.data.upload.method,
        headers: intent.data.upload.headers,
        body: file,
      });
      if (!uploaded.ok) throw new Error("upload failed");
    } catch {
      setUploadState("failed");
      setFailure(translate(locale, "events.media.failed"));
      return;
    }
    const completed = await api.completeMediaUpload(intent.data.id);
    if (!completed.ok || completed.data.status !== "verified") {
      setUploadState("failed");
      setFailure(
        translate(locale, completed.ok ? "events.media.failed" : completed.key),
      );
      return;
    }
    setCoverMediaId(completed.data.id);
    setUploadState("verified");
  }
  const owners = [
    ...(capabilities.create_independent_event
      ? [
          {
            id: "independent",
            label: translate(locale, "events.owner.independent"),
          },
        ]
      : []),
    ...managedClubs.map((club) => ({
      id: `club:${club.id}`,
      label: club.name,
    })),
  ];

  return (
    <main className="tq-organizer tq-event-workspace">
      <header className="tq-organizer__header">
        <div>
          <p className="tq-organizer__eyebrow">
            {translate(locale, "events.workspace.eyebrow")}
          </p>
          <h1>{translate(locale, "events.workspace.title")}</h1>
          <p>{translate(locale, "events.workspace.lead")}</p>
        </div>
        <Button
          type="button"
          onClick={() => {
            setCreating(true);
            setSelectedId(null);
            setCoverMediaId(null);
            setUploadState("pending");
          }}
          disabled={owners.length === 0}
        >
          {translate(locale, "events.workspace.create")}
        </Button>
      </header>

      {capabilities.blockers.length > 0 ? (
        <Card aria-label={translate(locale, "events.workspace.blockers")}>
          <h2>{translate(locale, "events.workspace.blockers")}</h2>
          <ul>
            {capabilities.blockers.map((value) => (
              <li key={value}>
                {translate(locale, `blockers.${value}` as TranslationKey)}
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      <div className="tq-event-workspace__layout">
        <nav aria-label={translate(locale, "events.workspace.navigation")}>
          {events.length === 0 ? (
            <p>{translate(locale, "events.workspace.empty")}</p>
          ) : (
            <ul className="tq-event-workspace__list">
              {events.map((item) => (
                <li key={item.id}>
                  <button type="button" onClick={() => choose(item)}>
                    <strong>{item.title}</strong>
                    <span>
                      {translate(locale, `events.status.${item.status}`)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </nav>

        <section aria-labelledby="event-form-title">
          <h2 id="event-form-title" ref={headingRef} tabIndex={-1}>
            {creating
              ? translate(locale, "events.form.createTitle")
              : translate(locale, "events.form.editTitle")}
          </h2>
          {failure ? (
            <div role="alert">
              <p>{failure}</p>
              {selected ? (
                <Button type="button" onClick={reloadConflict}>
                  {translate(locale, "events.workspace.reload")}
                </Button>
              ) : null}
            </div>
          ) : null}
          {notice ? <p role="status">{notice}</p> : null}

          {owners.length === 0 && creating ? (
            <Card>{translate(locale, "events.workspace.noOwnership")}</Card>
          ) : (
            <form
              key={selected?.revision ?? "new"}
              onSubmit={submit}
              className="tq-event-form"
            >
              <label>
                {translate(locale, "events.form.owner")}
                <select
                  name="owner"
                  defaultValue={
                    selected?.club_id
                      ? `club:${selected.club_id}`
                      : "independent"
                  }
                  disabled={!creating}
                >
                  {owners.map((owner) => (
                    <option value={owner.id} key={owner.id}>
                      {owner.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                {translate(locale, "events.form.title")}
                <input
                  name="title"
                  required
                  minLength={2}
                  maxLength={160}
                  defaultValue={values.title}
                />
              </label>
              <label className="tq-event-form__wide">
                {translate(locale, "events.form.description")}
                <textarea
                  name="description"
                  maxLength={20000}
                  defaultValue={values.description}
                />
              </label>
              <label>
                {translate(locale, "events.form.category")}
                <select
                  name="category_slug"
                  defaultValue={values.category_slug}
                >
                  <option value="" />
                  {metadata.categories.map((item) => (
                    <option value={item.slug} key={item.slug}>
                      {translate(locale, item.name_key as TranslationKey)}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                {translate(locale, "events.form.country")}
                <select
                  name="country_code"
                  defaultValue={values.country_code}
                  onChange={(event) =>
                    void loadPolicy(event.currentTarget.value)
                  }
                >
                  <option value="" />
                  {metadata.countries.map((item) => (
                    <option value={item.code} key={item.code}>
                      {translate(locale, item.name_key as TranslationKey)}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                {translate(locale, "events.form.city")}
                <select name="city_slug" defaultValue={values.city_slug}>
                  <option value="" />
                  {cities.map((item) => (
                    <option value={item.slug} key={item.slug}>
                      {translate(locale, item.name_key as TranslationKey)}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                {translate(locale, "events.form.timeZone")}
                <input name="time_zone" defaultValue={values.time_zone} />
              </label>
              <label>
                {translate(locale, "events.form.start")}
                <input
                  name="start_at"
                  type="datetime-local"
                  defaultValue={values.start_at}
                />
              </label>
              <label>
                {translate(locale, "events.form.end")}
                <input
                  name="end_at"
                  type="datetime-local"
                  defaultValue={values.end_at}
                />
              </label>
              <label>
                {translate(locale, "events.form.visibility")}
                <select name="visibility" defaultValue={values.visibility}>
                  <option value="public">
                    {translate(locale, "events.visibility.public")}
                  </option>
                  <option value="private_link">
                    {translate(locale, "events.visibility.private")}
                  </option>
                </select>
              </label>
              <label>
                {translate(locale, "events.form.capacity")}
                <input
                  name="capacity"
                  type="number"
                  min={1}
                  defaultValue={values.capacity}
                />
              </label>
              <label>
                {translate(locale, "events.form.method")}
                <select
                  name="registration_method"
                  defaultValue={values.registration_method}
                >
                  <option value="free">
                    {translate(locale, "discovery.free")}
                  </option>
                  <option value="cash_organizer_confirmed">
                    {translate(locale, "discovery.cash")}
                  </option>
                </select>
              </label>
              {policy ? (
                <Card className="tq-event-form__wide">
                  <strong>
                    {translate(locale, "events.form.regionPolicy")}
                  </strong>
                  <p>
                    {policy.allowed_registration_methods
                      .map((method) =>
                        translate(
                          locale,
                          method === "free"
                            ? "discovery.free"
                            : "discovery.cash",
                        ),
                      )
                      .join(", ")}
                  </p>
                  <p>
                    {policy.cancellation_bounds[0]}{" "}
                    {translate(locale, "events.form.rangeSeparator")}{" "}
                    {policy.cancellation_bounds[1]}
                  </p>
                </Card>
              ) : null}
              <label>
                {translate(locale, "events.form.cashDeadline")}
                <input
                  name="cash_expiry_minutes"
                  type="number"
                  min={0}
                  defaultValue={values.cash_expiry_minutes}
                />
              </label>
              <label>
                {translate(locale, "events.form.cancellation")}
                <input
                  name="cancellation_cutoff_minutes"
                  type="number"
                  min={0}
                  defaultValue={values.cancellation_cutoff_minutes}
                />
              </label>
              <label>
                {translate(locale, "events.form.district")}
                <input
                  name="district"
                  maxLength={120}
                  defaultValue={values.district}
                />
              </label>
              <label className="tq-event-form__wide">
                {translate(locale, "events.form.meetingArea")}
                <input
                  name="public_meeting_area"
                  maxLength={300}
                  defaultValue={values.public_meeting_area}
                />
              </label>
              <label className="tq-event-form__wide">
                {translate(locale, "events.form.exactAddress")}
                <input
                  name="exact_address"
                  maxLength={500}
                  defaultValue={values.exact_address}
                />
              </label>
              <label>
                {translate(locale, "events.form.latitude")}
                <input
                  name="latitude"
                  type="number"
                  step="any"
                  min={-90}
                  max={90}
                  defaultValue={values.latitude}
                />
              </label>
              <label>
                {translate(locale, "events.form.longitude")}
                <input
                  name="longitude"
                  type="number"
                  step="any"
                  min={-180}
                  max={180}
                  defaultValue={values.longitude}
                />
              </label>
              <label className="tq-event-form__check">
                <input
                  name="exact_venue_is_public"
                  type="checkbox"
                  defaultChecked={values.exact_venue_is_public}
                />
                {translate(locale, "events.form.publicVenue")}
              </label>
              <label className="tq-event-form__wide">
                {translate(locale, "events.form.coverMedia")}
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={(event) =>
                    void uploadCover(event.currentTarget.files?.[0])
                  }
                  aria-describedby="cover-media-help"
                />
                <input
                  name="cover_media_id"
                  type="hidden"
                  value={coverMediaId ?? ""}
                  readOnly
                />
                <small id="cover-media-help">
                  {translate(locale, "events.form.coverMediaHelp")}{" "}
                  {translate(locale, `events.media.${uploadState}`)}
                </small>
              </label>
              <Card
                className="tq-event-form__wide"
                aria-label={translate(locale, "events.form.venuePreview")}
              >
                <h3>{translate(locale, "events.form.venuePreview")}</h3>
                <p>{translate(locale, "discovery.privateVenue")}</p>
              </Card>
              {!creating && selected?.validation_blockers.length ? (
                <div className="tq-event-form__wide" role="status">
                  <strong>
                    {translate(locale, "events.workspace.blockers")}
                  </strong>
                  <ul>
                    {selected.validation_blockers.map((value) => (
                      <li key={value}>
                        {translate(
                          locale,
                          validationBlockerLabels[value] ?? "errors.validation",
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
              <div className="tq-event-form__actions tq-event-form__wide">
                <Button type="submit" value="draft">
                  {translate(locale, "events.form.saveDraft")}
                </Button>
                <Button type="submit" value="publish">
                  {translate(locale, "events.form.publish")}
                </Button>
              </div>
            </form>
          )}

          {!creating && selected ? (
            <div className="tq-event-workspace__actions">
              {selected.capabilities.includes("duplicate") ? (
                <Button type="button" onClick={() => action("duplicate")}>
                  {translate(locale, "events.action.duplicate")}
                </Button>
              ) : null}
              {selected.capabilities.includes("cancel") ? (
                <Button type="button" onClick={() => action("cancel")}>
                  {translate(locale, "events.action.cancel")}
                </Button>
              ) : null}
              {selected.capabilities.includes("complete") ? (
                <Button type="button" onClick={() => action("complete")}>
                  {translate(locale, "events.action.complete")}
                </Button>
              ) : null}
              {selected.capabilities.includes("delete_draft") ? (
                <Button type="button" onClick={() => action("delete")}>
                  {translate(locale, "events.action.deleteDraft")}
                </Button>
              ) : null}
            </div>
          ) : null}

          <Card aria-label={translate(locale, "events.attendees.title")}>
            <h2>{translate(locale, "events.attendees.title")}</h2>
            <p>{translate(locale, "events.attendees.phase4")}</p>
          </Card>
        </section>
      </div>
    </main>
  );
}
