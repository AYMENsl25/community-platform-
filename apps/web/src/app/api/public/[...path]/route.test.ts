import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DELETE, GET, POST, PUT } from "./route";

const eventId = "018f0000-0000-7000-8000-000000000201";
const context = (path: string[]) => ({ params: Promise.resolve({ path }) });

afterEach(() => vi.unstubAllGlobals());

describe("public mutation proxy", () => {
  it("serves only explicit anonymous discovery GETs without session cookies", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(Response.json({ items: [] }));
    vi.stubGlobal("fetch", fetcher);
    process.env.API_PUBLIC_URL = "http://api.test";
    const response = await GET(
      new NextRequest("http://web.test/api/public/api/v1/clubs", {
        headers: { Cookie: "talaqi_access=never; talaqi_csrf=never" },
      }),
      context(["api", "v1", "clubs"]),
    );
    expect(response.headers.get("cache-control")).toBe("public, max-age=60");
    expect(fetcher).toHaveBeenCalledWith("http://api.test/api/v1/clubs", {
      method: "GET",
      headers: {},
      cache: "no-store",
    });
  });

  it("forwards logout safely and preserves only upstream cookie clearing", async () => {
    const upstream = Response.json(
      { logged_out: true },
      {
        headers: {
          "Set-Cookie": "talaqi_access=; Path=/; HttpOnly; Max-Age=0",
        },
      },
    );
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(upstream);
    vi.stubGlobal("fetch", fetcher);
    process.env.API_PUBLIC_URL = "http://api.test";
    const response = await POST(
      new NextRequest("http://web.test/api/public/api/v1/auth/logout", {
        method: "POST",
        headers: {
          Cookie: "talaqi_access=access; talaqi_csrf=csrf; other=never",
          "X-CSRF-Token": "csrf",
        },
      }),
      context(["api", "v1", "auth", "logout"]),
    );
    expect(response.status).toBe(200);
    expect(response.headers.get("set-cookie")).toContain("talaqi_access=");
    expect(fetcher).toHaveBeenCalledWith("http://api.test/api/v1/auth/logout", {
      method: "POST",
      headers: {
        Cookie: "talaqi_access=access; talaqi_csrf=csrf",
        "X-CSRF-Token": "csrf",
      },
      cache: "no-store",
    });
  });

  it("forwards only minimal session cookies and CSRF", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetcher);
    process.env.API_PUBLIC_URL = "http://api.test/";
    const response = await PUT(
      new NextRequest(
        `http://web.test/api/public/api/v1/events/${eventId}/saved`,
        {
          method: "PUT",
          headers: {
            Cookie:
              "talaqi_access=access; talaqi_csrf=csrf; talaqi_refresh=never",
            "X-CSRF-Token": "csrf",
            Authorization: "never",
          },
        },
      ),
      context(["api", "v1", "events", eventId, "saved"]),
    );
    expect(response.status).toBe(204);
    expect(fetcher).toHaveBeenCalledWith(
      `http://api.test/api/v1/events/${eventId}/saved`,
      {
        method: "PUT",
        headers: {
          Cookie: "talaqi_access=access; talaqi_csrf=csrf",
          "X-CSRF-Token": "csrf",
        },
        cache: "no-store",
      },
    );
    expect(JSON.stringify(fetcher.mock.calls[0]?.[1])).not.toContain("never");
  });

  it("rejects malformed and unlisted targets without upstream contact", async () => {
    const fetcher = vi.fn<typeof fetch>();
    vi.stubGlobal("fetch", fetcher);
    const malformed = await DELETE(
      new NextRequest(
        "http://web.test/api/public/api/v1/events/not-an-id/saved",
        { method: "DELETE" },
      ),
      context(["api", "v1", "events", "not-an-id", "saved"]),
    );
    const unlisted = await PUT(
      new NextRequest(
        `http://web.test/api/public/api/v1/events/${eventId}/cancel`,
        { method: "PUT" },
      ),
      context(["api", "v1", "events", eventId, "cancel"]),
    );
    expect(malformed.status).toBe(404);
    expect(unlisted.status).toBe(404);
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("allows only event revalidation, registration, and self-cancellation shapes", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(Response.json({}));
    vi.stubGlobal("fetch", fetcher);
    const headers = {
      Cookie: "talaqi_access=access; talaqi_csrf=csrf; talaqi_refresh=never",
      "X-CSRF-Token": "csrf",
      "Idempotency-Key": "request-key",
      Authorization: "never",
    };
    await GET(
      new NextRequest(`http://web.test/api/public/api/v1/events/${eventId}`),
      context(["api", "v1", "events", eventId]),
    );
    await POST(
      new NextRequest(
        `http://web.test/api/public/api/v1/events/${eventId}/registrations`,
        { method: "POST", headers },
      ),
      context(["api", "v1", "events", eventId, "registrations"]),
    );
    await DELETE(
      new NextRequest(
        `http://web.test/api/public/api/v1/events/${eventId}/registrations/me`,
        { method: "DELETE", headers },
      ),
      context(["api", "v1", "events", eventId, "registrations", "me"]),
    );
    expect(fetcher).toHaveBeenCalledTimes(3);
    expect(fetcher.mock.calls[0]?.[1]).toMatchObject({
      method: "GET",
      headers: {},
    });
    for (const call of fetcher.mock.calls.slice(1)) {
      expect(call[1]).toMatchObject({
        headers: {
          Cookie: "talaqi_access=access; talaqi_csrf=csrf",
          "X-CSRF-Token": "csrf",
          "Idempotency-Key": "request-key",
        },
      });
      expect(JSON.stringify(call[1])).not.toContain("never");
    }
  });
});
