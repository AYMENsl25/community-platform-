import type { components } from "@talaqi/api-client";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
const listEvents = vi.fn();
const getMetadata = vi.fn();
vi.mock("@/lib/api/server-public-client", () => ({
  createServerPublicClient: async () => ({ listEvents, getMetadata }),
}));
vi.mock("@/lib/locale/request-locale", () => ({
  resolveRequestLocale: async () => "en",
}));
import ExplorePage from "./page";

const metadata = {
  countries: [{ code: "TR", name_key: "regions.country.tr" }],
  cities: [{ slug: "istanbul", name_key: "regions.city.istanbul" }],
  categories: [{ slug: "sports", name_key: "categories.sports" }],
  price_types: ["free", "cash"],
  sort: "featured",
} satisfies components["schemas"]["DiscoveryMetadataResponse"];

describe("ExplorePage", () => {
  beforeEach(() => {
    listEvents.mockResolvedValue({
      ok: true,
      data: { items: [], next_cursor: null },
    });
    getMetadata.mockResolvedValue({ ok: true, data: metadata });
  });
  it("passes bounded URL filters and renders localized controls", async () => {
    render(
      await ExplorePage({
        searchParams: Promise.resolve({
          country: "TR",
          city: "istanbul",
          category: "sports",
          price: "free",
          search: "run",
          cursor: "next-page",
          ignored: "private",
        }),
      }),
    );
    expect(listEvents).toHaveBeenCalledWith({
      country: "TR",
      city: "istanbul",
      category: "sports",
      price: "free",
      search: "run",
      cursor: "next-page",
      limit: 20,
    });
    fireEvent.click(screen.getByRole("button", { name: "Open filters" }));
    expect(screen.getByRole("dialog", { name: "Filters" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/Nothing matches/);
  });
  it("preserves active filters in the localized next link", async () => {
    listEvents.mockResolvedValue({
      ok: true,
      data: { items: [], next_cursor: "opaque-next" },
    });
    render(
      await ExplorePage({
        searchParams: Promise.resolve({
          country: "TR",
          city: "istanbul",
          search: "run club",
        }),
      }),
    );
    expect(
      screen.getByRole("link", { name: "Load more results" }),
    ).toHaveAttribute(
      "href",
      "/explore?country=TR&city=istanbul&search=run+club&cursor=opaque-next",
    );
  });
});
