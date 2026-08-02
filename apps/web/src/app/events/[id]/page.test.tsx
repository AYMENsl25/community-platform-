import type { components } from "@talaqi/api-client";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const getEvent = vi.fn();
const listEvents = vi.fn();
const getRegionPolicy = vi.fn();
vi.mock("@/lib/api/server-public-client", () => ({
  createServerPublicClient: async () => ({
    getEvent,
    listEvents,
    getRegionPolicy,
  }),
}));
vi.mock("@/lib/locale/request-locale", () => ({
  resolveRequestLocale: async () => "en",
}));

import EventPage, { generateMetadata } from "./page";

const event = {
  id: "018f0000-0000-7000-8000-000000000201",
  title: "Istanbul Weekend Run",
  description: "A safe public run.",
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
  exact_address: null,
  latitude: null,
  longitude: null,
  capacity: 30,
  available_places: 12,
  cover_media_id: "018f0000-0000-7000-8000-000000000299",
  club_slug: null,
  club_name: null,
  organizer_display_name: "Public Organizer",
  is_saved: false,
  registration_state: null,
} satisfies components["schemas"]["EventAudienceResponse"];

describe("EventPage", () => {
  it("renders safe complete details and indexable metadata", async () => {
    getEvent.mockResolvedValue({ ok: true, data: event });
    listEvents.mockResolvedValue({
      ok: true,
      data: { items: [], next_cursor: null },
    });
    getRegionPolicy.mockResolvedValue({
      ok: true,
      data: { country_code: "TR", allowed_registration_methods: ["free"] },
    });
    const props = { params: Promise.resolve({ id: event.id }) };
    const { container } = render(await EventPage(props));
    expect(
      screen.getByRole("heading", { name: event.title }),
    ).toBeInTheDocument();
    expect(container).toHaveTextContent("Waterfront");
    expect(container).toHaveTextContent(
      "Exact venue details are shared only when permitted.",
    );
    expect(container).not.toHaveTextContent("canonical.webp");
    expect(screen.getByRole("img", { name: event.title })).toHaveAttribute(
      "src",
      `/api/media/${event.cover_media_id}`,
    );
    expect(await generateMetadata(props)).toMatchObject({
      title: event.title,
      description: event.description,
      robots: { index: true, follow: true },
      alternates: {
        canonical: `http://localhost:3000/events/${event.id}`,
      },
    });
  });

  it("keeps unavailable content out of search metadata", async () => {
    getEvent.mockResolvedValue({
      ok: false,
      key: "errors.not_found",
      status: 404,
    });
    const metadata = await generateMetadata({
      params: Promise.resolve({ id: event.id }),
    });
    expect(metadata).toMatchObject({
      title: "Talaqi",
      robots: { index: false, follow: false },
    });
    expect(metadata).not.toHaveProperty("alternates");
    expect(metadata).not.toHaveProperty("openGraph");
  });
});
