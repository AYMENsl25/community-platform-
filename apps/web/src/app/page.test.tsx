import type { components } from "@talaqi/api-client";
import { translate } from "@talaqi/translations";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LocalizedHome } from "@/components/locale/localized-home";

const metadata = {
  countries: [{ code: "TR", name_key: "regions.country.tr" }],
  cities: [{ slug: "istanbul", name_key: "regions.city.istanbul" }],
  categories: [{ slug: "sports", name_key: "categories.sports" }],
  price_types: ["free", "cash"],
  sort: "featured",
} satisfies components["schemas"]["DiscoveryMetadataResponse"];

const event = {
  id: "018f0000-0000-7000-8000-000000000201",
  title: "Istanbul Weekend Run",
  description: "A public run.",
  country_code: "TR",
  city_slug: "istanbul",
  category_slug: "sports",
  start_at: "2035-04-12T07:00:00Z",
  end_at: "2035-04-12T09:00:00Z",
  time_zone: "Europe/Istanbul",
  ownership_type: "independent",
  cancellation_cutoff_minutes: 60,
  price_type: "free",
  district: "Kadikoy",
  public_meeting_area: "Waterfront",
  capacity: 30,
  available_places: 12,
  cover_media_id: null,
  club_slug: null,
  club_name: null,
  organizer_display_name: "Public Organizer",
  is_saved: false,
  registration_state: null,
} satisfies components["schemas"]["EventCardResponse"];

const club = {
  id: "018f0000-0000-7000-8000-000000000101",
  slug: "istanbul-community",
  name: "Istanbul Community Club",
  description: "Friendly public gatherings.",
  country_code: "TR",
  city_slug: "istanbul",
  category_slug: "sports",
  cover_media_id: null,
  member_count: 42,
} satisfies components["schemas"]["ClubCardResponse"];

const landing = { metadata, featuredEvents: [event], popularClubs: [club] };

describe("localized home", () => {
  it("renders translated English content inside the public shell", () => {
    const { container } = render(
      <LocalizedHome initialLocale="en" landing={landing} />,
    );
    expect(
      screen.getByRole("heading", {
        level: 1,
        name: translate("en", "home.title"),
      }),
    ).toBeInTheDocument();
    expect(screen.getByRole("main")).toHaveAttribute("id", "main-content");
    expect(container.querySelectorAll("main")).toHaveLength(1);
    expect(screen.getByAltText("Talaqi")).toHaveAttribute(
      "src",
      "/brand/talaqi-wordmark.png",
    );
  });

  it("renders discovery, region, and organizer guidance without a creation shortcut", () => {
    render(<LocalizedHome initialLocale="en" landing={landing} />);
    expect(
      screen.getByRole("form", { name: "Choose your region" }),
    ).toHaveAttribute("action", "/explore");
    expect(screen.getByRole("link", { name: event.title })).toHaveAttribute(
      "href",
      `/events/${event.id}`,
    );
    expect(screen.getByRole("link", { name: club.name })).toHaveAttribute(
      "href",
      `/clubs/${club.slug}`,
    );
    expect(
      screen.getAllByText(translate("en", "discovery.featuredExplanation")),
    ).toHaveLength(2);
    expect(
      screen.getByRole("link", {
        name: translate("en", "home.organizer.action"),
      }),
    ).toHaveAttribute("href", "/profile");
    expect(
      screen.queryByRole("link", { name: /create (club|event)/i }),
    ).not.toBeInTheDocument();
  });

  it("rerenders visible content and shell direction when locale changes", () => {
    const { container } = render(
      <LocalizedHome initialLocale="en" landing={landing} />,
    );
    fireEvent.change(
      screen.getByRole("combobox", { name: "Choose display language" }),
      { target: { value: "ar" } },
    );
    expect(
      screen.getByRole("heading", {
        level: 1,
        name: translate("ar", "home.title"),
      }),
    ).toBeInTheDocument();
    expect(container.querySelector(".tq-public-shell")).toHaveAttribute(
      "lang",
      "ar",
    );
    expect(container.querySelector(".tq-public-shell")).toHaveAttribute(
      "dir",
      "rtl",
    );
  });
});

const listEvents = vi.fn();
const listClubs = vi.fn();
const getMetadata = vi.fn();
vi.mock("@/lib/api/server-public-client", () => ({
  createServerPublicClient: async () => ({
    listEvents,
    listClubs,
    getMetadata,
  }),
}));
vi.mock("@/lib/locale/request-locale", () => ({
  resolveRequestLocale: async () => "en",
}));

describe("Home server integration", () => {
  beforeEach(() => {
    getMetadata.mockResolvedValue({ ok: true, data: metadata });
    listEvents.mockResolvedValue({
      ok: true,
      data: { items: [event], next_cursor: null },
    });
    listClubs.mockResolvedValue({
      ok: true,
      data: { items: [club], next_cursor: null },
    });
  });

  it("requests bounded featured landing content", async () => {
    const { default: Home } = await import("./page");
    render(await Home());
    expect(listEvents).toHaveBeenCalledWith({ limit: 4 });
    expect(listClubs).toHaveBeenCalledWith({ limit: 4 });
    expect(screen.getByRole("link", { name: event.title })).toBeInTheDocument();
  });
});
