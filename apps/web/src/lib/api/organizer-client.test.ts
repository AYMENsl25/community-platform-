import { describe, expect, it, vi } from "vitest";

import { createOrganizerClient } from "./organizer-client";

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

describe("organizer API client", () => {
  it("keeps reads private and sends CSRF for mutations", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(json({ items: [] }))
      .mockResolvedValueOnce(json({ status: "closed" }));
    const client = createOrganizerClient({
      baseUrl: "http://api.test/",
      cookie: "talaqi_access=session; talaqi_csrf=token",
      csrfToken: "token",
      fetch: fetcher,
    });

    await client.listManagedClubs();
    await client.closeClub(
      "019f9e7d-d7a0-7d86-9166-2053f7de24a3",
      "Operations ended",
    );

    expect(fetcher.mock.calls[0]?.[1]).toMatchObject({
      cache: "no-store",
      credentials: "include",
      headers: { Cookie: "talaqi_access=session; talaqi_csrf=token" },
    });
    expect(fetcher.mock.calls[1]?.[1]).toMatchObject({
      method: "POST",
      headers: {
        Cookie: "talaqi_access=session; talaqi_csrf=token",
        "Content-Type": "application/json",
        "X-CSRF-Token": "token",
      },
      body: JSON.stringify({ reason: "Operations ended" }),
    });
  });

  it("maps safe server errors and never returns private response text", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      json(
        {
          error: {
            code: "stale_revision",
            message_key: "private.database.detail",
            field_errors: [{ field: "revision", message: "private" }],
            request_id: "33333333-3333-4333-8333-333333333333",
          },
        },
        409,
      ),
    );
    const client = createOrganizerClient({
      baseUrl: "http://api.test",
      fetch: fetcher,
    });

    await expect(
      client.updateClub("019f9e7d-d7a0-7d86-9166-2053f7de24a3", {
        revision: 1,
        name: "Safe name",
      }),
    ).resolves.toEqual({
      ok: false,
      key: "organizer.errors.staleRevision",
      status: 409,
      fieldNames: ["revision"],
      requestId: "33333333-3333-4333-8333-333333333333",
    });
  });

  it.each([
    [400, undefined, "errors.validation"],
    [400, "duplicate_slug", "organizer.errors.duplicateSlug"],
    [400, "invalid_reason", "organizer.errors.reason"],
    [401, undefined, "errors.authentication_required"],
    [403, undefined, "errors.forbidden"],
    [404, undefined, "errors.not_found"],
    [422, undefined, "errors.validation"],
  ] as const)("maps HTTP %i with code %s to %s", async (status, code, key) => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      json(
        {
          error: {
            ...(code ? { code } : {}),
            message_key: "private.message",
          },
        },
        status,
      ),
    );
    const client = createOrganizerClient({
      baseUrl: "http://api.test",
      fetch: fetcher,
    });

    await expect(client.listManagedClubs()).resolves.toEqual({
      ok: false,
      key,
      status,
      fieldNames: [],
    });
  });

  it("ignores malformed error bodies and unsafe request identifiers", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(
        new Response("private stack trace", { status: 400 }),
      )
      .mockResolvedValueOnce(
        json(
          {
            error: {
              code: { private: true },
              request_id: { private: true },
              field_errors: [
                null,
                { field: 42 },
                { field: "safe_field", message: "private" },
              ],
            },
          },
          422,
        ),
      );
    const client = createOrganizerClient({
      baseUrl: "http://api.test",
      fetch: fetcher,
    });

    await expect(client.listManagedClubs()).resolves.toEqual({
      ok: false,
      key: "errors.validation",
      status: 400,
      fieldNames: [],
    });
    await expect(client.listManagedClubs()).resolves.toEqual({
      ok: false,
      key: "errors.validation",
      status: 422,
      fieldNames: ["safe_field"],
    });
  });

  it("preserves only a string request ID from a safe error envelope", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      json(
        {
          error: {
            code: "forbidden",
            request_id: "44444444-4444-4444-8444-444444444444",
          },
        },
        403,
      ),
    );
    const client = createOrganizerClient({
      baseUrl: "http://api.test",
      fetch: fetcher,
    });

    await expect(client.listManagedClubs()).resolves.toEqual({
      ok: false,
      key: "errors.forbidden",
      status: 403,
      fieldNames: [],
      requestId: "44444444-4444-4444-8444-444444444444",
    });
  });

  it("maps network failures to a stable internal error", async () => {
    const client = createOrganizerClient({
      baseUrl: "/api/organizer",
      fetch: vi
        .fn<typeof fetch>()
        .mockRejectedValue(new Error("private token")),
    });
    await expect(client.listManagedClubs()).resolves.toEqual({
      ok: false,
      key: "errors.internal",
      status: 0,
      fieldNames: [],
    });
  });
});
