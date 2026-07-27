import { describe, expect, it, vi } from "vitest";

import { createAdminClient } from "./admin-client";

const caseId = "77777777-7777-4777-8777-777777777777";

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

describe("admin API client", () => {
  it("serializes private list, target-search, and audit queries", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(json({ items: [] }));
    const client = createAdminClient({
      baseUrl: "http://api.test/",
      cookie: "talaqi_access=session; talaqi_csrf=token",
      fetch: fetcher,
    });

    await client.listModerationCases({
      status: "investigating",
      targetType: "club",
      cursor: "opaque +/= cursor",
      limit: 20,
    });
    await client.searchModerationTargets("safe query & value", "event");
    await client.listAuditEvents({
      caseId,
      targetType: "user",
      targetId: "target/id",
      limit: 10,
    });

    expect(fetcher.mock.calls.map(([url]) => String(url))).toEqual([
      "http://api.test/api/v1/admin/moderation/cases?status=investigating&target_type=club&cursor=opaque+%2B%2F%3D+cursor&limit=20",
      "http://api.test/api/v1/admin/moderation/targets?query=safe+query+%26+value&target_type=event",
      `http://api.test/api/v1/admin/audit-events?case_id=${caseId}&target_type=user&target_id=target%2Fid&limit=10`,
    ]);
    for (const [, init] of fetcher.mock.calls) {
      expect(init).toMatchObject({
        method: "GET",
        cache: "no-store",
        credentials: "include",
        headers: {
          Cookie: "talaqi_access=session; talaqi_csrf=token",
        },
      });
    }
  });

  it("posts only the moderation action, reason, and CSRF", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(json({ id: caseId }));
    const client = createAdminClient({
      baseUrl: "http://api.test",
      cookie: "talaqi_access=session; talaqi_csrf=token",
      csrfToken: "token",
      fetch: fetcher,
    });

    await client.submitModerationAction(
      caseId,
      "suspend",
      "Confirmed policy violation",
      "moderation-action-00000001",
    );

    expect(fetcher).toHaveBeenCalledWith(
      `http://api.test/api/v1/admin/moderation/cases/${caseId}/actions`,
      {
        method: "POST",
        cache: "no-store",
        credentials: "include",
        headers: {
          Cookie: "talaqi_access=session; talaqi_csrf=token",
          "Content-Type": "application/json",
          "Idempotency-Key": "moderation-action-00000001",
          "X-CSRF-Token": "token",
        },
        body: JSON.stringify({
          action: "suspend",
          reason: "Confirmed policy violation",
        }),
      },
    );
  });

  it.each([
    [400, "errors.validation"],
    [401, "errors.authentication_required"],
    [403, "errors.forbidden"],
    [404, "errors.not_found"],
    [409, "errors.conflict"],
    [422, "errors.validation"],
    [429, "errors.rate_limited"],
    [500, "errors.internal"],
  ] as const)("maps HTTP %i to safe key %s", async (status, key) => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      json(
        {
          error: {
            code: "private_code",
            message_key: "private.database.message",
          },
        },
        status,
      ),
    );
    const client = createAdminClient({
      baseUrl: "http://api.test",
      fetch: fetcher,
    });

    await expect(client.getModerationCase(caseId)).resolves.toEqual({
      ok: false,
      key,
      status,
      fieldNames: [],
    });
  });

  it("maps CSRF, request ID, and field names without leaking server messages", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      json(
        {
          error: {
            code: "csrf_failed",
            request_id: "33333333-3333-4333-8333-333333333333",
            message: "private stack trace",
            field_errors: [
              null,
              { field: 42, message: "private" },
              { field: "reason", message: "private" },
            ],
          },
        },
        403,
      ),
    );
    const client = createAdminClient({
      baseUrl: "http://api.test",
      fetch: fetcher,
    });

    await expect(
      client.submitModerationAction(
        caseId,
        "restore",
        "Reviewed",
        "moderation-action-00000002",
      ),
    ).resolves.toEqual({
      ok: false,
      key: "errors.csrf_failed",
      status: 403,
      fieldNames: ["reason"],
      requestId: "33333333-3333-4333-8333-333333333333",
    });
  });

  it("handles malformed and network responses without leaking their text", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(
        new Response("private upstream body", { status: 500 }),
      )
      .mockResolvedValueOnce(new Response("not-json", { status: 200 }))
      .mockRejectedValueOnce(new Error("private network token"));
    const client = createAdminClient({
      baseUrl: "http://api.test",
      fetch: fetcher,
    });

    await expect(client.listModerationCases()).resolves.toEqual({
      ok: false,
      key: "errors.internal",
      status: 500,
      fieldNames: [],
    });
    await expect(client.listModerationCases()).resolves.toEqual({
      ok: false,
      key: "errors.internal",
      status: 200,
      fieldNames: [],
    });
    await expect(client.listModerationCases()).resolves.toEqual({
      ok: false,
      key: "errors.internal",
      status: 0,
      fieldNames: [],
    });
  });
});
