import { beforeEach, describe, expect, it, vi } from "vitest";

const { createOrganizerClient, cookieValues } = vi.hoisted(() => ({
  createOrganizerClient: vi.fn((options: unknown) => options),
  cookieValues: new Map<string, string>(),
}));

vi.mock("./organizer-client", () => ({ createOrganizerClient }));
vi.mock("next/headers", () => ({
  cookies: async () => ({
    get: (name: string) => {
      const value = cookieValues.get(name);
      return value ? { name, value } : undefined;
    },
  }),
}));

import { createServerOrganizerClient } from "./server-organizer-client";

describe("server organizer client", () => {
  beforeEach(() => {
    cookieValues.clear();
    createOrganizerClient.mockClear();
    process.env.API_PUBLIC_URL = "http://api.test";
  });

  it("forwards access and CSRF but excludes refresh and unrelated cookies", async () => {
    cookieValues.set("talaqi_access", "access");
    cookieValues.set("talaqi_csrf", "csrf");
    cookieValues.set("talaqi_refresh", "never-forward");
    cookieValues.set("fixture_role", "never-forward");
    await createServerOrganizerClient();
    expect(createOrganizerClient).toHaveBeenCalledWith({
      baseUrl: "http://api.test",
      cookie: "talaqi_access=access; talaqi_csrf=csrf",
      csrfToken: "csrf",
    });
  });
});
