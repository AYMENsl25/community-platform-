"use client";

import { translate } from "@talaqi/translations";
import { useEffect, useState } from "react";
import { useLocale } from "@/lib/locale/locale-context";

type InstallPrompt = Event & {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

const USER_STATE_PREFIXES = [
  "talaqi:user:",
  "talaqi:member:",
  "talaqi:organizer:",
];

function clearStore(store: Storage) {
  for (let index = store.length - 1; index >= 0; index -= 1) {
    const key = store.key(index);
    if (key && USER_STATE_PREFIXES.some((prefix) => key.startsWith(prefix))) {
      store.removeItem(key);
    }
  }
}

export async function clearUserScopedBrowserState(): Promise<void> {
  clearStore(window.localStorage);
  clearStore(window.sessionStorage);
  if ("serviceWorker" in navigator) {
    try {
      const registration = await Promise.race([
        navigator.serviceWorker.getRegistration(),
        new Promise<undefined>((resolve) => window.setTimeout(resolve, 500)),
      ]);
      const worker = navigator.serviceWorker.controller ?? registration?.active;
      worker?.postMessage({ type: "CLEAR_USER_DATA" });
    } catch {
      // Server logout must never be held open by optional worker cleanup.
    }
  }
}

export async function activateWaitingWorker(
  worker: ServiceWorker,
  container: ServiceWorkerContainer = navigator.serviceWorker,
  timeoutMs = 4_000,
): Promise<void> {
  await new Promise<void>((resolve) => {
    const timeout = window.setTimeout(resolve, timeoutMs);
    container.addEventListener(
      "controllerchange",
      () => {
        window.clearTimeout(timeout);
        resolve();
      },
      { once: true },
    );
    worker.postMessage({ type: "SKIP_WAITING" });
  });
}

export function PwaManager() {
  const { locale } = useLocale();
  const [installPrompt, setInstallPrompt] = useState<InstallPrompt>();
  const [waitingWorker, setWaitingWorker] = useState<ServiceWorker>();

  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;
    let registration: ServiceWorkerRegistration | undefined;
    const onLogout = () => void clearUserScopedBrowserState();
    const onInstall = (event: Event) => {
      event.preventDefault();
      setInstallPrompt(event as InstallPrompt);
    };
    window.addEventListener("talaqi:logout", onLogout);
    window.addEventListener("beforeinstallprompt", onInstall);
    void navigator.serviceWorker
      .register("/sw.js", { type: "module", scope: "/" })
      .then((value) => {
        registration = value;
        if (value.waiting) setWaitingWorker(value.waiting);
        value.addEventListener("updatefound", () => {
          const worker = value.installing;
          worker?.addEventListener("statechange", () => {
            if (
              worker.state === "installed" &&
              navigator.serviceWorker.controller
            ) {
              setWaitingWorker(worker);
            }
          });
        });
      });
    return () => {
      window.removeEventListener("talaqi:logout", onLogout);
      window.removeEventListener("beforeinstallprompt", onInstall);
      void registration;
    };
  }, []);

  if (!installPrompt && !waitingWorker) return null;
  return (
    <aside aria-live="polite" className="tq-pwa-prompt">
      <p>
        {translate(
          locale,
          waitingWorker ? "pwa.update.body" : "pwa.install.body",
        )}
      </p>
      <button
        className="tq-action-link"
        onClick={() => {
          if (waitingWorker) {
            void activateWaitingWorker(waitingWorker).then(() =>
              window.location.reload(),
            );
            return;
          }
          if (!installPrompt) return;
          void installPrompt.prompt();
          void installPrompt.userChoice.finally(() =>
            setInstallPrompt(undefined),
          );
        }}
        type="button"
      >
        {translate(
          locale,
          waitingWorker ? "pwa.update.action" : "pwa.install.action",
        )}
      </button>
    </aside>
  );
}
