"use client";

import { translate, type LocaleCode } from "@talaqi/translations";
import { useState } from "react";
import { clearUserScopedBrowserState } from "./pwa-manager";

function csrfToken(): string | undefined {
  return document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith("talaqi_csrf="))
    ?.slice("talaqi_csrf=".length);
}

export function LogoutButton({ locale }: { locale: LocaleCode }) {
  const [failed, setFailed] = useState(false);
  return (
    <div className="tq-logout">
      <button
        className="tq-action-link tq-action-link--secondary"
        onClick={() => {
          const csrf = csrfToken();
          if (!csrf) {
            setFailed(true);
            return;
          }
          void fetch("/api/public/api/v1/auth/logout", {
            method: "POST",
            credentials: "include",
            headers: { "X-CSRF-Token": csrf },
          })
            .then(async (response) => {
              if (!response.ok) {
                setFailed(true);
                return;
              }
              await clearUserScopedBrowserState();
              window.location.assign("/");
            })
            .catch(() => setFailed(true));
        }}
        type="button"
      >
        {translate(locale, "pwa.logout.action")}
      </button>
      {failed ? (
        <p role="alert">{translate(locale, "pwa.logout.error")}</p>
      ) : null}
    </div>
  );
}
