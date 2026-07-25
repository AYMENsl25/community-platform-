import type { components } from "@talaqi/api-client";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const getEvent = vi.fn();
vi.mock("@/lib/api/server-public-client", () => ({
  createServerPublicClient: async () => ({ getEvent }),
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
  price_type: "free",
  district: "Kadikoy",
  public_meeting_area: "Waterfront",
  capacity: 30,
  available_places: 12,
  cover_storage_key: "private/key",
  club_slug: null,
  club_name: null,
  organizer_display_name: "Public Organizer",
  is_saved: false,
  registration_state: null,
} satisfies components["schemas"]["EventCardResponse"];

describe("EventPage", () => {
  it("renders only safe event details and metadata", async () => {
    getEvent.mockResolvedValue({ ok: true, data: event });
    const props = { params: Promise.resolve({ id: event.id }) };
    const { container } = render(await EventPage(props));
    expect(
      screen.getByRole("heading", { name: event.title }),
    ).toBeInTheDocument();
    expect(container).toHaveTextContent("Waterfront");
    expect(container).toHaveTextContent(
      "Exact venue details are shared only when permitted.",
    );
    expect(container).not.toHaveTextContent("private/key");
    expect(await generateMetadata(props)).toMatchObject({
      title: event.title,
      description: event.description,
    });
  });
});
