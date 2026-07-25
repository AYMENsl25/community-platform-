import { describe, expect, it, vi } from "vitest";

import { createPublicClient } from "./public-client";

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

describe("public discovery client", () => {
  it("serializes event filters and caches anonymous requests", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(json({ items: [], next_cursor: null }));
    const client = createPublicClient({
      baseUrl: "http://api.test",
      fetch: fetcher,
    });
    await client.listEvents({
      country: "TR",
      city: "istanbul",
      price: "free",
      cursor: "opaque +/= cursor",
      limit: 20,
      search: undefined,
    });
    const call = fetcher.mock.calls[0];
    expect(call).toBeDefined();
    const [url, init] = call ?? [];
    expect(String(url)).toBe(
      "http://api.test/api/v1/events?country=TR&city=istanbul&price=free&cursor=opaque+%2B%2F%3D+cursor&limit=20",
    );
    expect(init).toMatchObject({ method: "GET" });
    expect(init?.headers).not.toHaveProperty("Cookie");
    expect((init as RequestInit & { next: unknown }).next).toEqual({
      revalidate: 60,
      tags: ["discovery:events"],
    });
  });

  it("uses no-store and forwards cookies for caller-aware reads", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(json({ items: [], next_cursor: null }));
    const client = createPublicClient({
      baseUrl: "http://api.test/",
      fetch: fetcher,
      cookie: "talaqi_access=session",
    });
    await client.listEvents({});
    expect(fetcher).toHaveBeenCalledWith(
      "http://api.test/api/v1/events",
      expect.objectContaining({
        cache: "no-store",
        headers: expect.objectContaining({ Cookie: "talaqi_access=session" }),
      }),
    );
    expect(fetcher.mock.calls[0]?.[1]).not.toHaveProperty("next");
  });

  it("keeps public-only discovery cached even with a session", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(json({ items: [], next_cursor: null }));
    const client = createPublicClient({
      baseUrl: "http://api.test",
      fetch: fetcher,
      cookie: "talaqi_access=session",
    });
    await client.listClubs({ search: "Chess" });
    const call = fetcher.mock.calls[0];
    expect(call).toBeDefined();
    const [, init] = call ?? [];
    expect(init?.headers).not.toHaveProperty("Cookie");
    expect((init as RequestInit & { next: unknown }).next).toEqual({
      revalidate: 60,
      tags: ["discovery:clubs"],
    });
  });

  it("maps failures to stable keys without exposing server bodies", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(
        json(
          {
            error: {
              code: "private",
              message_key: "private.message",
              field_errors: [],
              request_id: "3a629a9d-75d0-497d-91bd-8351303d6f47",
            },
          },
          422,
        ),
      )
      .mockResolvedValueOnce(
        new Response("secret stack trace", { status: 500 }),
      );
    const client = createPublicClient({
      baseUrl: "http://api.test",
      fetch: fetcher,
    });
    await expect(client.listEvents({})).resolves.toEqual({
      ok: false,
      key: "errors.invalid_filters",
      status: 422,
      requestId: "3a629a9d-75d0-497d-91bd-8351303d6f47",
    });
    await expect(client.getEvent("event-id")).resolves.toEqual({
      ok: false,
      key: "errors.unavailable",
      status: 500,
    });
  });

  it("maps network failures without leaking exception text", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockRejectedValue(new Error("database password"));
    const client = createPublicClient({
      baseUrl: "http://api.test",
      fetch: fetcher,
    });
    await expect(client.getClub("safe-club")).resolves.toEqual({
      ok: false,
      key: "errors.unavailable",
      status: 0,
    });
  });

  it("handles 204 saves and sends CSRF privately", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(null, { status: 204 }));
    const client = createPublicClient({
      baseUrl: "http://api.test",
      fetch: fetcher,
      cookie: "talaqi_access=session; talaqi_csrf=token",
      csrfToken: "token",
    });
    await expect(client.saveEvent("event-id")).resolves.toEqual({
      ok: true,
      data: undefined,
    });
    expect(fetcher).toHaveBeenCalledWith(
      "http://api.test/api/v1/events/event-id/saved",
      expect.objectContaining({
        method: "PUT",
        cache: "no-store",
        credentials: "include",
        headers: {
          Cookie: "talaqi_access=session; talaqi_csrf=token",
          "X-CSRF-Token": "token",
        },
      }),
    );
  });

  it.each([
    [401, "errors.auth_required"],
    [403, "errors.action_unavailable"],
    [404, "errors.not_found"],
    [429, "errors.rate_limited"],
  ] as const)("maps HTTP %i to %s", async (status, key) => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(json({ ignored: true }, status));
    const client = createPublicClient({
      baseUrl: "http://api.test",
      fetch: fetcher,
    });
    await expect(client.getEvent("event-id")).resolves.toEqual({
      ok: false,
      key,
      status,
    });
  });
});
