import { beforeEach, describe, expect, it, vi } from "vitest";

const { createPublicClient, cookieValues } = vi.hoisted(() => ({
  createPublicClient: vi.fn((options: unknown) => options),
  cookieValues: new Map<string, string>(),
}));

vi.mock("./public-client", () => ({ createPublicClient }));
vi.mock("next/headers", () => ({
  cookies: async () => ({
    get: (name: string) => {
      const value = cookieValues.get(name);
      return value ? { name, value } : undefined;
    },
  }),
}));

import { createServerPublicClient } from "./server-public-client";

describe("createServerPublicClient", () => {
  beforeEach(() => {
    cookieValues.clear();
    createPublicClient.mockClear();
    process.env.API_PUBLIC_URL = "http://api.example.test/";
  });

  it("forwards only the access cookie for caller-aware public reads", async () => {
    cookieValues.set("talaqi_access", "signed-access");
    cookieValues.set("talaqi_refresh", "private-refresh");
    cookieValues.set("talaqi_locale", "ar");
    await createServerPublicClient();
    expect(createPublicClient).toHaveBeenCalledWith({
      baseUrl: "http://api.example.test/",
      cookie: "talaqi_access=signed-access",
    });
  });

  it("keeps anonymous discovery requests free of cookie state", async () => {
    await createServerPublicClient();
    expect(createPublicClient).toHaveBeenCalledWith({
      baseUrl: "http://api.example.test/",
    });
  });
});
