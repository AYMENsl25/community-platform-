import type { components } from "@talaqi/api-client";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const getClub = vi.fn();
vi.mock("@/lib/api/server-public-client", () => ({
  createServerPublicClient: async () => ({ getClub }),
}));
vi.mock("@/lib/locale/request-locale", () => ({
  resolveRequestLocale: async () => "en",
}));

import ClubPage, { generateMetadata } from "./page";

vi.mock("@/components/communications/member-communications", () => ({
  MemberCommunications: () => null,
}));

const club = {
  id: "018f0000-0000-7000-8000-000000000101",
  slug: "istanbul-community",
  name: "Istanbul Community Club",
  description: "Friendly public gatherings.",
  country_code: "TR",
  city_slug: "istanbul",
  category_slug: "sports",
  cover_media_id: "018f0000-0000-7000-8000-000000000299",
  member_count: 42,
  events: [],
} satisfies components["schemas"]["ClubDetailResponse"];

describe("ClubPage", () => {
  it("renders safe public club fields and safe metadata", async () => {
    getClub.mockResolvedValue({ ok: true, data: club });
    const props = { params: Promise.resolve({ slug: club.slug }) };
    const { container } = render(await ClubPage(props));
    expect(
      screen.getByRole("heading", { name: club.name }),
    ).toBeInTheDocument();
    expect(container).toHaveTextContent(club.description);
    expect(container).not.toHaveTextContent("private/key");
    expect(await generateMetadata(props)).toMatchObject({
      title: club.name,
      description: club.description,
    });
  });
});
