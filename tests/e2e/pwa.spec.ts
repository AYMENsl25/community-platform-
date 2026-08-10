import { expect, test } from "@playwright/test";

test("is installable and serves the public offline shell", async ({ context, page }) => {
  await page.goto("/");
  const manifest = await page.locator('link[rel="manifest"]').getAttribute("href");
  expect(manifest).toBe("/manifest.webmanifest");
  const response = await page.request.get(manifest!);
  const body = await response.json();
  expect(body.icons.map((icon: { sizes: string }) => icon.sizes)).toEqual(
    expect.arrayContaining(["192x192", "512x512"]),
  );
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
    if (!navigator.serviceWorker.controller) {
      await new Promise<void>((resolve) =>
        navigator.serviceWorker.addEventListener("controllerchange", () => resolve(), {
          once: true,
        }),
      );
    }
    const response = await fetch("/api/public/api/v1/clubs");
    if (!response.ok) throw new Error("safe public response was not available");
  });
  await context.setOffline(true);
  const cached = await page.evaluate(() =>
    fetch("/api/public/api/v1/clubs").then((response) => response.json()),
  );
  expect(cached.items).toHaveLength(1);
  await page.goto("/explore");
  await expect(page.getByRole("heading", { name: /offline/i })).toBeVisible();
  await context.setOffline(false);
});

test("successful logout clears user-scoped browser and runtime cache state", async ({
  context,
  page,
}) => {
  await context.addCookies([
    { name: "talaqi_access", value: "member-token", url: "http://127.0.0.1:3100" },
    {
      name: "talaqi_csrf",
      value: "fixture-csrf",
      url: "http://127.0.0.1:3100",
    },
  ]);
  await page.goto("/overview");
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
    localStorage.setItem("talaqi:user:profile", "private");
    sessionStorage.setItem("talaqi:member:filters", "private");
    localStorage.setItem("talaqi_locale", "en");
    const cache = await caches.open("talaqi-pwa-v1-public");
    await cache.put("/private-sentinel", new Response("private"));
  });
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL("/");
  await expect
    .poll(() =>
      page.evaluate(async () => ({
        local: localStorage.getItem("talaqi:user:profile"),
        session: sessionStorage.getItem("talaqi:member:filters"),
        locale: localStorage.getItem("talaqi_locale"),
        cache: await caches.has("talaqi-pwa-v1-public"),
      })),
    )
    .toEqual({ local: null, session: null, locale: "en", cache: false });
});
