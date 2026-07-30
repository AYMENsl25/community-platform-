import type { components } from "@talaqi/api-client";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EventCard } from "./event-card";

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
  price_type: "free",
  district: "Kadikoy",
  public_meeting_area: "Waterfront meeting point",
  capacity: 30,
  available_places: 12,
  cover_storage_key: "private/storage/key",
  club_slug: "istanbul-community",
  club_name: "Istanbul Community Club",
  organizer_display_name: "Fixture Owner",
  is_saved: false,
  registration_state: null,
} satisfies components["schemas"]["EventCardResponse"];

describe("EventCard", () => {
  it("renders safe discovery fields and navigation", () => {
    render(<EventCard event={event} locale="en" showFeaturedReason />);

    expect(screen.getByRole("link", { name: event.title })).toHaveAttribute(
      "href",
      `/events/${event.id}`,
    );
    expect(
      screen.getByRole("link", { name: "Istanbul Community Club" }),
    ).toHaveAttribute("href", `/clubs/${event.club_slug}`);
    expect(screen.getByText(/Waterfront meeting point/)).toBeInTheDocument();
    expect(screen.getByText(/12 Places available/)).toBeInTheDocument();
    expect(
      screen.getByText(/Featured results use transparent rules/),
    ).toBeInTheDocument();
  });

  it("labels events without a capacity as unlimited", () => {
    render(
      <EventCard
        event={{ ...event, capacity: null, available_places: null }}
        locale="en"
      />,
    );

    expect(screen.getByText("Unlimited places")).toBeInTheDocument();
  });
  it("never renders private or internal values", () => {
    const { container } = render(<EventCard event={event} locale="en" />);
    const rendered = container.textContent ?? "";

    expect(rendered).not.toContain(event.cover_storage_key);
    expect(rendered).not.toMatch(
      /latitude|longitude|exact.address|ranking.score/i,
    );
  });

  it("shows the save affordance only when requested", () => {
    const { rerender } = render(<EventCard event={event} locale="en" />);
    expect(
      screen.queryByRole("button", { name: "Save event" }),
    ).not.toBeInTheDocument();
    rerender(<EventCard event={event} locale="en" showSave />);
    expect(
      screen.getByRole("button", { name: "Save event" }),
    ).toBeInTheDocument();
  });
});
