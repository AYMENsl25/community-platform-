import { describe, expect, it, vi } from "vitest";

import { createTalaqiClient } from "./index";
import type { components, paths } from "./schema.generated";

describe("generated Talaqi API client", () => {
  it("uses an explicit base URL and injected fetch for a generated operation", async () => {
    const fakeFetch = vi.fn<typeof fetch>(async (input) => {
      const request = input instanceof Request ? input : new Request(input);
      expect(request.url).toBe("https://api.example.test/health/live");
      expect(request.method).toBe("GET");
      return new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    });
    const client = createTalaqiClient({
      baseUrl: "https://api.example.test",
      fetch: fakeFetch,
    });

    const result = await client.GET("/health/live");

    expect(result.data).toEqual({ status: "ok" });
    expect(fakeFetch).toHaveBeenCalledOnce();
  });

  it("preserves locked snake_case envelope and cursor fields in generated types", () => {
    const envelope: components["schemas"]["ErrorEnvelope"] = {
      error: {
        code: "stable_code",
        message_key: "errors.key",
        field_errors: [],
        request_id: "0198a4c0-0000-7000-8000-000000000000",
      },
    };
    const page: components["schemas"]["CursorPage"] = {
      items: [],
      next_cursor: null,
    };

    expect(envelope.error.message_key).toBe("errors.key");
    expect(page.next_cursor).toBeNull();
  });

  it("types both ready and unavailable readiness response variants", async () => {
    type ReadinessResponses = paths["/health/ready"]["get"]["responses"];
    const ready: ReadinessResponses[200]["content"]["application/json"] = {
      status: "ready",
      checks: { database: "ok" },
    };
    const unavailable: ReadinessResponses[503]["content"]["application/json"] =
      {
        status: "not_ready",
        checks: { database: "failed" },
      };
    const fakeFetch = vi.fn<typeof fetch>(async () =>
      Promise.resolve(
        new Response(JSON.stringify(unavailable), {
          status: 503,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );
    const client = createTalaqiClient({
      baseUrl: "https://api.example.test",
      fetch: fakeFetch,
    });

    const result = await client.GET("/health/ready");

    expect(ready.status).toBe("ready");
    expect(result.error).toEqual(unavailable);
    expect(result.response.status).toBe(503);
  });
});
