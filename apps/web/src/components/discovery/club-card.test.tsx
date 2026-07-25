import type { components } from "@talaqi/api-client";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ClubCard } from "./club-card";

const club = {
  id: "018f0000-0000-7000-8000-000000000101",
  slug: "istanbul-community",
  name: "Istanbul Community Club",
  description: "Friendly public gatherings across Istanbul.",
  country_code: "TR",
  city_slug: "istanbul",
  category_slug: "social",
  cover_storage_key: "private/club/key",
} satisfies components["schemas"]["ClubCardResponse"];

describe("ClubCard", () => {
  it("renders safe public fields and the club route", () => {
    const { container } = render(<ClubCard club={club} locale="en" />);
    expect(screen.getByRole("link", { name: club.name })).toHaveAttribute(
      "href",
      `/clubs/${club.slug}`,
    );
    expect(screen.getByText(club.description)).toBeInTheDocument();
    expect(container).toHaveTextContent("Istanbul");
    expect(container).toHaveTextContent("Social");
    expect(container).not.toHaveTextContent("private/club/key");
  });
});
