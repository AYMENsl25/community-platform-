import { beforeEach, describe, expect, it, vi } from "vitest";

const listEvents = vi.fn();
const listClubs = vi.fn();
vi.mock("@/lib/api/public-client", () => ({
  createPublicClient: () => ({ listEvents, listClubs }),
}));

import sitemap from "./sitemap";

beforeEach(() => {
  listEvents.mockResolvedValue({
    ok: true,
    data: {
      items: [{ id: "018f0000-0000-7000-8000-000000000201" }],
      next_cursor: null,
    },
  });
  listClubs.mockResolvedValue({
    ok: true,
    data: { items: [{ slug: "public-club" }], next_cursor: null },
  });
});

describe("public sitemap", () => {
  it("contains only API-eligible public resources with locale alternates", async () => {
    const entries = await sitemap();
    expect(entries.map((entry) => entry.url)).toEqual([
      "http://localhost:3000/",
      "http://localhost:3000/explore",
      "http://localhost:3000/events/018f0000-0000-7000-8000-000000000201",
      "http://localhost:3000/clubs/public-club",
    ]);
    expect(entries[2]?.alternates?.languages).toMatchObject({
      en: expect.stringContaining("?locale=en"),
      tr: expect.stringContaining("?locale=tr"),
      fr: expect.stringContaining("?locale=fr"),
      ar: expect.stringContaining("?locale=ar"),
    });
    expect(JSON.stringify(entries)).not.toMatch(/private|token|exact_address/);
    expect(listEvents).toHaveBeenCalledWith({ limit: 50 });
    expect(listClubs).toHaveBeenCalledWith({ limit: 50 });
  });

  it("fails closed to static public routes when discovery is unavailable", async () => {
    listEvents.mockResolvedValue({ ok: false, status: 503 });
    listClubs.mockResolvedValue({ ok: false, status: 503 });
    expect((await sitemap()).map((entry) => entry.url)).toEqual([
      "http://localhost:3000/",
      "http://localhost:3000/explore",
    ]);
  });
});
