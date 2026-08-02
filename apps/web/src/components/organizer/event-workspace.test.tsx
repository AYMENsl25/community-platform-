import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type {
  Capabilities,
  ManagedClub,
  ManagedEvent,
} from "@/lib/api/organizer-client";
import { LocaleProvider } from "@/lib/locale/locale-context";

import { EventWorkspace } from "./event-workspace";

const managedEvent: ManagedEvent = {
  id: "019f9e7d-d7a0-7d86-9166-2053f7de2401",
  ownership_type: "independent",
  club_id: null,
  owner_user_id: "019f9e7d-d7a0-7d86-9166-2053f7de2402",
  title: "Community walk",
  description: "A welcoming walk",
  category_slug: "outdoors",
  country_code: "TR",
  city_slug: "istanbul",
  start_at: "2026-09-05T09:00:00Z",
  end_at: "2026-09-05T11:00:00Z",
  time_zone: "Europe/Istanbul",
  capacity: 20,
  visibility: "public",
  status: "draft",
  registration_method: "free",
  cash_expiry_minutes: null,
  cancellation_cutoff_minutes: 60,
  district: "Kadikoy",
  public_meeting_area: "Ferry entrance",
  exact_address: "Private address",
  latitude: 40.99,
  longitude: 29.02,
  exact_venue_is_public: false,
  cover_media_id: null,
  revision: 1,
  published_at: null,
  cancelled_at: null,
  completed_at: null,
  suspended_at: null,
  suspension_reason: null,
  created_at: "2026-08-02T08:00:00Z",
  updated_at: "2026-08-02T08:00:00Z",
  capabilities: ["duplicate", "delete_draft", "preview"],
  validation_blockers: [],
};

const managedClub = {
  id: "019f9e7d-d7a0-7d86-9166-2053f7de2410",
  slug: "walkers",
  name: "City Walkers",
  description: "Walking club",
  category_slug: "outdoors",
  country_code: "TR",
  city_slug: "istanbul",
  membership_policy: "open",
  social_links: {},
  logo_media_id: null,
  cover_media_id: null,
  revision: 1,
  status: "published",
  missing_fields: [],
  published_at: "2026-08-01T08:00:00Z",
  suspended_at: null,
  suspension_reason: null,
  closed_at: null,
  created_at: "2026-08-01T08:00:00Z",
  updated_at: "2026-08-01T08:00:00Z",
  role: "owner",
  capabilities: ["edit_profile", "manage_members", "preview_profile"],
} satisfies ManagedClub;

const metadata = {
  countries: [{ code: "TR", name_key: "regions.country.tr" }],
  cities: [{ slug: "istanbul", name_key: "regions.city.istanbul" }],
  categories: [{ slug: "outdoors", name_key: "regions.category.outdoors" }],
};

const capabilities = {
  create_club: false,
  create_independent_event: false,
  save_event: true,
  register_event: true,
  access_admin: false,
  blockers: [],
} satisfies Capabilities;

afterEach(() => {
  vi.unstubAllGlobals();
  document.cookie = "talaqi_csrf=; Max-Age=0; path=/";
});

function workspace(overrides: Partial<Capabilities> = {}) {
  return render(
    <LocaleProvider initialLocale="en">
      <EventWorkspace
        initialEvents={[managedEvent]}
        managedClubs={[managedClub]}
        metadata={metadata}
        capabilities={{ ...capabilities, ...overrides }}
      />
    </LocaleProvider>,
  );
}

describe("event organizer workspace", () => {
  it("renders only server-returned ownership choices and lifecycle capabilities", () => {
    workspace();
    expect(
      screen.getByRole("heading", { name: "Event organizer workspace" }),
    ).toBeVisible();
    expect(screen.getByRole("option", { name: "City Walkers" })).toBeVisible();
    expect(
      screen.queryByRole("option", { name: "Independent event" }),
    ).toBeNull();
    expect(
      screen.getByRole("button", { name: "Duplicate as draft" }),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: "Delete draft" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Cancel event" })).toBeNull();
    expect(
      screen.getByText("Attendee management arrives in Phase 4."),
    ).toBeVisible();
  });

  it("recovers a stale edit using the latest private revision", async () => {
    document.cookie = "talaqi_csrf=csrf-token; path=/";
    const latest = { ...managedEvent, revision: 2, title: "Latest title" };
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            error: { code: "stale_revision", field_errors: [] },
          }),
          { status: 409, headers: { "content-type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(latest), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", fetcher);
    workspace();
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    expect(
      await screen.findByText(
        "This club changed elsewhere. Reload before saving again.",
      ),
    ).toBeVisible();
    fireEvent.click(
      screen.getByRole("button", { name: "Load latest revision" }),
    );
    await waitFor(() =>
      expect(screen.getByRole("textbox", { name: "Title" })).toHaveValue(
        "Latest title",
      ),
    );
    expect(fetcher.mock.calls[0]?.[1]).toMatchObject({
      method: "PATCH",
      headers: expect.objectContaining({
        "X-CSRF-Token": "csrf-token",
      }),
    });
    expect(String(fetcher.mock.calls[1]?.[0])).toContain(
      `${managedEvent.id}/managed`,
    );
  });
});
