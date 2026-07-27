import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET, POST } from "./route";

const caseId = "77777777-7777-4777-8777-777777777777";

function context(path: string[]) {
  return { params: Promise.resolve({ path }) };
}

afterEach(() => vi.unstubAllGlobals());

describe("admin API proxy", () => {
  it("rejects unlisted paths, malformed IDs, extra segments, and wrong methods", async () => {
    const fetcher = vi.fn<typeof fetch>();
    vi.stubGlobal("fetch", fetcher);
    const attempts = [
      GET(
        new NextRequest("http://web.test/api/admin/api/v1/admin/users"),
        context(["api", "v1", "admin", "users"]),
      ),
      GET(
        new NextRequest(
          "http://web.test/api/admin/api/v1/admin/moderation/cases/not-a-uuid",
        ),
        context(["api", "v1", "admin", "moderation", "cases", "not-a-uuid"]),
      ),
      GET(
        new NextRequest(
          `http://web.test/api/admin/api/v1/admin/moderation/cases/${caseId}/actions`,
        ),
        context([
          "api",
          "v1",
          "admin",
          "moderation",
          "cases",
          caseId,
          "actions",
        ]),
      ),
      POST(
        new NextRequest(
          "http://web.test/api/admin/api/v1/admin/moderation/cases",
          { method: "POST", body: "{}" },
        ),
        context(["api", "v1", "admin", "moderation", "cases"]),
      ),
      GET(
        new NextRequest(
          "http://web.test/api/admin/api/v1/admin/audit-events/private",
        ),
        context(["api", "v1", "admin", "audit-events", "private"]),
      ),
    ];

    const responses = await Promise.all(attempts);
    expect(responses.map((response) => response.status)).toEqual([
      404, 404, 404, 404, 404,
    ]);
    for (const response of responses)
      expect(response.headers.get("cache-control")).toBe("private, no-store");
    expect(fetcher).not.toHaveBeenCalled();
  });

  it.each([
    [
      ["api", "v1", "admin", "moderation", "cases"],
      "/api/v1/admin/moderation/cases",
    ],
    [
      ["api", "v1", "admin", "moderation", "cases", caseId],
      `/api/v1/admin/moderation/cases/${caseId}`,
    ],
    [
      ["api", "v1", "admin", "moderation", "targets"],
      "/api/v1/admin/moderation/targets",
    ],
    [["api", "v1", "admin", "audit-events"], "/api/v1/admin/audit-events"],
  ] as const)("allows only GET target %j", async (path, pathname) => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ items: [] }), {
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetcher);
    process.env.API_PUBLIC_URL = "http://api.test/";

    const response = await GET(
      new NextRequest(
        `http://web.test/api/admin${pathname}?cursor=opaque%20cursor`,
        {
          headers: {
            Cookie:
              "talaqi_access=access; talaqi_csrf=csrf; talaqi_refresh=never-forward",
            Authorization: "never-forward",
          },
        },
      ),
      context([...path]),
    );

    expect(response.status).toBe(200);
    expect(response.headers.get("cache-control")).toBe("private, no-store");
    expect(fetcher).toHaveBeenCalledWith(
      `http://api.test${pathname}?cursor=opaque%20cursor`,
      {
        method: "GET",
        headers: { Cookie: "talaqi_access=access; talaqi_csrf=csrf" },
        cache: "no-store",
      },
    );
    expect(JSON.stringify(fetcher.mock.calls[0]?.[1])).not.toContain(
      "never-forward",
    );
  });

  it("forwards only the allowed action body, minimal cookies, content type, and CSRF", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ id: caseId }), {
        status: 200,
        headers: {
          "content-type": "application/json",
          "x-request-id": "44444444-4444-4444-8444-444444444444",
          "x-private-debug": "never-forward",
        },
      }),
    );
    vi.stubGlobal("fetch", fetcher);
    process.env.API_PUBLIC_URL = "http://api.test";
    const body = JSON.stringify({
      action: "suspend",
      reason: "Confirmed policy violation",
    });
    const response = await POST(
      new NextRequest(
        `http://web.test/api/admin/api/v1/admin/moderation/cases/${caseId}/actions`,
        {
          method: "POST",
          body,
          headers: {
            Cookie:
              "talaqi_access=access; talaqi_csrf=csrf; talaqi_refresh=never-forward",
            "Content-Type": "application/json",
            "Idempotency-Key": "moderation-action-00000001",
            "X-CSRF-Token": "csrf",
            Authorization: "never-forward",
          },
        },
      ),
      context(["api", "v1", "admin", "moderation", "cases", caseId, "actions"]),
    );

    expect(response.status).toBe(200);
    expect(response.headers.get("cache-control")).toBe("private, no-store");
    expect(response.headers.get("x-request-id")).toBe(
      "44444444-4444-4444-8444-444444444444",
    );
    expect(response.headers.get("x-private-debug")).toBeNull();
    expect(fetcher).toHaveBeenCalledWith(
      `http://api.test/api/v1/admin/moderation/cases/${caseId}/actions`,
      {
        method: "POST",
        headers: {
          Cookie: "talaqi_access=access; talaqi_csrf=csrf",
          "Content-Type": "application/json",
          "Idempotency-Key": "moderation-action-00000001",
          "X-CSRF-Token": "csrf",
        },
        cache: "no-store",
        body,
      },
    );
  });

  it("maps upstream failures to a stable private 502 without leakage", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn<typeof fetch>()
        .mockRejectedValue(new Error("private database token")),
    );

    const response = await GET(
      new NextRequest(
        "http://web.test/api/admin/api/v1/admin/moderation/cases",
      ),
      context(["api", "v1", "admin", "moderation", "cases"]),
    );

    expect(response.status).toBe(502);
    expect(response.headers.get("cache-control")).toBe("private, no-store");
    expect(await response.json()).toEqual({
      error: { code: "upstream_unavailable" },
    });
  });
});
