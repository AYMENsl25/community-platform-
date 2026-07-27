import { beforeEach, describe, expect, it, vi } from "vitest";

const { createAdminClient, cookieValues } = vi.hoisted(() => ({
  createAdminClient: vi.fn((options: unknown) => options),
  cookieValues: new Map<string, string>(),
}));

vi.mock("./admin-client", () => ({ createAdminClient }));
vi.mock("next/headers", () => ({
  cookies: async () => ({
    get: (name: string) => {
      const value = cookieValues.get(name);
      return value ? { name, value } : undefined;
    },
  }),
}));

import { createServerAdminClient } from "./server-admin-client";

describe("server admin client", () => {
  beforeEach(() => {
    cookieValues.clear();
    createAdminClient.mockClear();
    process.env.API_PUBLIC_URL = "http://api.test";
  });

  it("forwards only access and CSRF cookies", async () => {
    cookieValues.set("talaqi_access", "access");
    cookieValues.set("talaqi_csrf", "csrf");
    cookieValues.set("talaqi_refresh", "never-forward");
    cookieValues.set("fixture_role", "never-forward");

    await createServerAdminClient();

    expect(createAdminClient).toHaveBeenCalledWith({
      baseUrl: "http://api.test",
      cookie: "talaqi_access=access; talaqi_csrf=csrf",
      csrfToken: "csrf",
    });
  });
});
