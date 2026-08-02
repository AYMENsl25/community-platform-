import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DELETE, GET, PATCH, POST } from "./route";

const clubId = "77777777-7777-4777-8777-777777777777";

function context(path: string[]) {
  return { params: Promise.resolve({ path }) };
}

afterEach(() => vi.unstubAllGlobals());

describe("organizer API proxy", () => {
  it("rejects unlisted and malformed targets without contacting the API", async () => {
    const fetcher = vi.fn<typeof fetch>();
    vi.stubGlobal("fetch", fetcher);
    const unlisted = await GET(
      new NextRequest("http://web.test/api/organizer/api/v1/profiles"),
      context(["api", "v1", "profiles"]),
    );
    const malformed = await POST(
      new NextRequest(
        "http://web.test/api/organizer/api/v1/clubs/not-a-uuid/close",
        { method: "POST" },
      ),
      context(["api", "v1", "clubs", "not-a-uuid", "close"]),
    );
    expect(unlisted.status).toBe(404);
    expect(malformed.status).toBe(404);
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("forwards only session-minimal cookies and CSRF to an allowed action", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ status: "closed" }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetcher);
    process.env.API_PUBLIC_URL = "http://api.test/";
    const request = new NextRequest(
      `http://web.test/api/organizer/api/v1/clubs/${clubId}/close`,
      {
        method: "POST",
        body: JSON.stringify({ reason: "Operations ended" }),
        headers: {
          Cookie:
            "talaqi_access=access; talaqi_csrf=csrf; talaqi_refresh=never-forward",
          "Content-Type": "application/json",
          "X-CSRF-Token": "csrf",
          Authorization: "never-forward",
        },
      },
    );

    const response = await POST(
      request,
      context(["api", "v1", "clubs", clubId, "close"]),
    );
    expect(response.status).toBe(200);
    expect(fetcher).toHaveBeenCalledWith(
      `http://api.test/api/v1/clubs/${clubId}/close`,
      expect.objectContaining({
        method: "POST",
        headers: {
          Cookie: "talaqi_access=access; talaqi_csrf=csrf",
          "Content-Type": "application/json",
          "X-CSRF-Token": "csrf",
        },
      }),
    );
    expect(JSON.stringify(fetcher.mock.calls[0]?.[1])).not.toContain(
      "never-forward",
    );
  });

  it("allows only the listed PATCH targets", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetcher);
    process.env.API_PUBLIC_URL = "http://api.test";
    const userId = "88888888-8888-4888-8888-888888888888";

    const clubPatch = await PATCH(
      new NextRequest(`http://web.test/api/organizer/api/v1/clubs/${clubId}`, {
        method: "PATCH",
        body: JSON.stringify({ name: "Updated" }),
      }),
      context(["api", "v1", "clubs", clubId]),
    );
    const rolePatch = await PATCH(
      new NextRequest(
        `http://web.test/api/organizer/api/v1/clubs/${clubId}/members/${userId}/role`,
        {
          method: "PATCH",
          body: JSON.stringify({ role: "admin", reason: "Coverage" }),
        },
      ),
      context(["api", "v1", "clubs", clubId, "members", userId, "role"]),
    );
    const unlistedPatch = await PATCH(
      new NextRequest(
        `http://web.test/api/organizer/api/v1/clubs/${clubId}/close`,
        { method: "PATCH", body: "{}" },
      ),
      context(["api", "v1", "clubs", clubId, "close"]),
    );

    expect(clubPatch.status).toBe(200);
    expect(rolePatch.status).toBe(200);
    expect(unlistedPatch.status).toBe(404);
    expect(fetcher).toHaveBeenCalledTimes(2);
    expect(fetcher.mock.calls.map(([url]) => String(url))).toEqual([
      `http://api.test/api/v1/clubs/${clubId}`,
      `http://api.test/api/v1/clubs/${clubId}/members/${userId}/role`,
    ]);
  });

  it("forwards an upstream request ID without exposing other headers", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ error: { code: "forbidden" } }), {
        status: 403,
        headers: {
          "content-type": "application/json",
          "x-request-id": "55555555-5555-4555-8555-555555555555",
          "x-private-debug": "database-password",
        },
      }),
    );
    vi.stubGlobal("fetch", fetcher);

    const response = await GET(
      new NextRequest(
        `http://web.test/api/organizer/api/v1/clubs/${clubId}/members`,
      ),
      context(["api", "v1", "clubs", clubId, "members"]),
    );

    expect(response.status).toBe(403);
    expect(response.headers.get("x-request-id")).toBe(
      "55555555-5555-4555-8555-555555555555",
    );
    expect(response.headers.get("x-private-debug")).toBeNull();
    expect(response.headers.get("cache-control")).toBe("private, no-store");
  });

  it("maps upstream fetch failures to a stable private 502", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockRejectedValue(new Error("database-password")),
    );

    const response = await GET(
      new NextRequest(
        `http://web.test/api/organizer/api/v1/clubs/${clubId}/members`,
      ),
      context(["api", "v1", "clubs", clubId, "members"]),
    );

    expect(response.status).toBe(502);
    expect(response.headers.get("cache-control")).toBe("private, no-store");
    expect(await response.json()).toEqual({
      error: { code: "upstream_unavailable" },
    });
  });
  it("allowlists event workflows and forwards only CSRF and idempotency headers", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ items: [] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetcher);
    process.env.API_PUBLIC_URL = "http://api.test";
    const eventId = "99999999-9999-4999-8999-999999999999";
    const request = new NextRequest(
      `http://web.test/api/organizer/api/v1/events/${eventId}`,
      {
        method: "DELETE",
        body: JSON.stringify({ revision: 1 }),
        headers: {
          Cookie: "talaqi_access=access; talaqi_csrf=csrf; private=never",
          "Content-Type": "application/json",
          "X-CSRF-Token": "csrf",
          "Idempotency-Key": "event-operation-key",
          Authorization: "never-forward",
        },
      },
    );
    const response = await DELETE(
      request,
      context(["api", "v1", "events", eventId]),
    );
    expect(response.status).toBe(200);
    expect(fetcher).toHaveBeenCalledWith(
      `http://api.test/api/v1/events/${eventId}`,
      expect.objectContaining({
        method: "DELETE",
        headers: {
          Cookie: "talaqi_access=access; talaqi_csrf=csrf",
          "Content-Type": "application/json",
          "X-CSRF-Token": "csrf",
          "Idempotency-Key": "event-operation-key",
        },
      }),
    );
    const denied = await POST(
      new NextRequest(
        "http://web.test/api/organizer/api/v1/events/not-a-uuid",
        {
          method: "POST",
        },
      ),
      context(["api", "v1", "events", "not-a-uuid"]),
    );
    expect(denied.status).toBe(404);
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
});
