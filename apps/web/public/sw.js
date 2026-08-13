import { cacheCategory } from "/pwa-cache-policy.js";

const VERSION = "talaqi-pwa-v1";
const STATIC_CACHE = `${VERSION}-static`;
const PUBLIC_CACHE = `${VERSION}-public`;
const OFFLINE_URL = "/offline";

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => cache.add(OFFLINE_URL)),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter(
              (key) =>
                key.startsWith("talaqi-pwa-") && !key.startsWith(VERSION),
            )
            .map((key) => caches.delete(key)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

async function cached(request, cacheName, event) {
  const cache = await caches.open(cacheName);
  const hit = await cache.match(request);
  const revalidate = fetch(request).then((response) => {
    if (
      response.ok &&
      response.type !== "opaque" &&
      !response.headers.has("Set-Cookie")
    ) {
      return cache.put(request, response.clone()).then(() => response);
    }
    return response;
  });
  if (!hit) return revalidate;
  event.waitUntil(revalidate.catch(() => undefined));
  return hit;
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.mode === "navigate") {
    event.respondWith(fetch(request).catch(() => caches.match(OFFLINE_URL)));
    return;
  }
  const category = cacheCategory(request);
  if (category === "static")
    event.respondWith(cached(request, STATIC_CACHE, event));
  if (category === "public")
    event.respondWith(cached(request, PUBLIC_CACHE, event));
});

self.addEventListener("message", (event) => {
  if (event.data?.type === "SKIP_WAITING") void self.skipWaiting();
  if (event.data?.type === "CLEAR_USER_DATA") {
    event.waitUntil(caches.delete(PUBLIC_CACHE));
  }
});
