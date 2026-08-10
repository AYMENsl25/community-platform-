import { describe, expect, it } from "vitest";
import { cacheCategory } from "../../../public/pwa-cache-policy.js";

const request = (path, method = "GET") =>
  new Request(`https://talaqi.test${path}`, { method });

describe("privacy-safe PWA cache policy", () => {
  it.each([
    ["/_next/static/chunks/app-abc123.js", "static"],
    ["/api/public/api/v1/clubs?limit=20", "public"],
    ["/api/public/api/v1/search?q=music", "public"],
    ["/api/public/api/v1/metadata", "public"],
    ["/api/public/api/v1/regions/TR/policy", "public"],
  ])("allows %s only in the %s cache", (path, category) => {
    expect(cacheCategory(request(path))).toBe(category);
  });

  it.each([
    "/brand/talaqi-pwa-192.png",
    "/manifest.webmanifest",
    "/api/public/api/v1/me/saved-events",
    "/api/public/api/v1/invitations/token",
    "/api/public/api/v1/events/id/registrations",
    "/api/organizer/api/v1/notifications",
    "/api/organizer/api/v1/events/id/attendees",
    "/api/admin/api/v1/moderation/cases",
    "/api/public/api/v1/events/private-id",
  ])("bypasses sensitive GET %s", (path) => {
    expect(cacheCategory(request(path))).toBe("bypass");
  });

  it.each(["POST", "PUT", "PATCH", "DELETE"])(
    "bypasses every %s mutation",
    (method) => {
      expect(cacheCategory(request("/api/public/api/v1/clubs", method))).toBe(
        "bypass",
      );
    },
  );
});
