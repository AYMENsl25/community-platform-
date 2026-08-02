import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DELETE, PUT } from "./route";

const eventId = "018f0000-0000-7000-8000-000000000201";
const context = (path: string[]) => ({ params: Promise.resolve({ path }) });

afterEach(() => vi.unstubAllGlobals());

describe("public mutation proxy", () => {
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
});
