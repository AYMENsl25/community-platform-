"use client";

import { useState } from "react";
import { translate, type LocaleCode } from "@talaqi/translations";

function csrfToken(): string | undefined {
  const entry = document.cookie
    .split(";")
    .map((value) => value.trim())
    .find((value) => value.startsWith("talaqi_csrf="));
  return entry
    ? decodeURIComponent(entry.slice("talaqi_csrf=".length))
    : undefined;
}

export function SaveEventButton({
  eventId,
  initialSaved,
  locale,
}: {
  eventId: string;
  initialSaved: boolean;
  locale: LocaleCode;
}) {
  const [saved, setSaved] = useState(initialSaved);
  const [pending, setPending] = useState(false);
  const [failed, setFailed] = useState(false);

  async function toggle() {
    setPending(true);
    setFailed(false);
    try {
      const csrf = csrfToken();
      const response = await fetch(
        `/api/public/api/v1/events/${encodeURIComponent(eventId)}/saved`,
        {
          method: saved ? "DELETE" : "PUT",
          credentials: "same-origin",
          cache: "no-store",
          headers: csrf ? { "X-CSRF-Token": csrf } : {},
        },
      );
      if (!response.ok) throw new Error("save_failed");
      setSaved((value) => !value);
    } catch {
      setFailed(true);
    } finally {
      setPending(false);
    }
  }

  return (
    <span>
      <button
        className="tq-discovery-control"
        type="button"
        aria-pressed={saved}
        disabled={pending}
        onClick={toggle}
      >
        {translate(locale, saved ? "discovery.unsave" : "discovery.save")}
      </button>
      <span className="tq-discovery-save-status" aria-live="polite">
        {failed ? translate(locale, "states.error") : ""}
      </span>
    </span>
  );
}
