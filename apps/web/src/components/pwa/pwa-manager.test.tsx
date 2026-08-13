import { act, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { LocaleProvider } from "@/lib/locale/locale-context";
import {
  activateWaitingWorker,
  clearUserScopedBrowserState,
  PwaManager,
} from "./pwa-manager";

const postMessage = vi.fn();
const register = vi.fn(async () => ({
  active: { postMessage },
  waiting: null,
  installing: null,
  addEventListener: vi.fn(),
}));

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
  postMessage.mockClear();
  register.mockClear();
  Object.defineProperty(navigator, "serviceWorker", {
    configurable: true,
    value: {
      register,
      getRegistration: vi.fn(async () => ({ active: { postMessage } })),
      controller: null,
      ready: Promise.resolve({ active: { postMessage } }),
    },
  });
});

it("registers the module worker and offers the captured install prompt", async () => {
  render(
    <LocaleProvider initialLocale="en">
      <PwaManager />
    </LocaleProvider>,
  );
  const prompt = vi.fn(async () => undefined);
  const event = new Event("beforeinstallprompt", { cancelable: true });
  Object.assign(event, {
    prompt,
    userChoice: Promise.resolve({ outcome: "accepted" }),
  });
  await act(async () => window.dispatchEvent(event));
  expect(register).toHaveBeenCalledWith("/sw.js", {
    scope: "/",
    type: "module",
  });
  await act(async () =>
    screen.getByRole("button", { name: "Install" }).click(),
  );
  expect(prompt).toHaveBeenCalledOnce();
});

it("clears only user-scoped storage and asks the worker to clear runtime data", async () => {
  localStorage.setItem("talaqi:user:profile", "private");
  localStorage.setItem("talaqi_locale", "fr");
  sessionStorage.setItem("talaqi:organizer:draft", "private");
  await clearUserScopedBrowserState();
  expect(localStorage.getItem("talaqi:user:profile")).toBeNull();
  expect(sessionStorage.getItem("talaqi:organizer:draft")).toBeNull();
  expect(localStorage.getItem("talaqi_locale")).toBe("fr");
  expect(postMessage).toHaveBeenCalledWith({ type: "CLEAR_USER_DATA" });
});

it("waits for controller activation before resolving an update", async () => {
  const container = new EventTarget() as ServiceWorkerContainer;
  const worker = {
    postMessage: vi.fn(() =>
      container.dispatchEvent(new Event("controllerchange")),
    ),
  } as unknown as ServiceWorker;
  await activateWaitingWorker(worker, container, 50);
  expect(worker.postMessage).toHaveBeenCalledWith({ type: "SKIP_WAITING" });
});

it("never blocks local cleanup on a stalled worker registration", async () => {
  vi.useFakeTimers();
  Object.defineProperty(navigator, "serviceWorker", {
    configurable: true,
    value: {
      controller: null,
      getRegistration: vi.fn(() => new Promise(() => undefined)),
    },
  });
  localStorage.setItem("talaqi:user:profile", "private");
  const clearing = clearUserScopedBrowserState();
  await vi.advanceTimersByTimeAsync(500);
  await clearing;
  expect(localStorage.getItem("talaqi:user:profile")).toBeNull();
  vi.useRealTimers();
});

it("treats a rejected worker lookup as best-effort cleanup", async () => {
  Object.defineProperty(navigator, "serviceWorker", {
    configurable: true,
    value: {
      controller: null,
      getRegistration: vi.fn(async () => {
        throw new Error("registration unavailable");
      }),
    },
  });
  localStorage.setItem("talaqi:user:profile", "private");
  await expect(clearUserScopedBrowserState()).resolves.toBeUndefined();
  expect(localStorage.getItem("talaqi:user:profile")).toBeNull();
});
