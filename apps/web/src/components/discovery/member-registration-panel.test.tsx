import type { components } from "@talaqi/api-client";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MemberRegistrationPanel } from "./member-registration-panel";

type EventDetail = components["schemas"]["EventAudienceResponse"];

const event = {
  id: "018f0000-0000-7000-8000-000000000201",
  title: "Community event",
  description: "Description",
  country_code: "TR",
  city_slug: "istanbul",
  category_slug: "community",
  start_at: "2035-04-12T07:00:00Z",
  end_at: "2035-04-12T09:00:00Z",
  time_zone: "Europe/Istanbul",
  ownership_type: "independent",
  cancellation_cutoff_minutes: 60,
  price_type: "free",
  district: "Kadikoy",
  public_meeting_area: "Park entrance",
  exact_address: null,
  latitude: null,
  longitude: null,
  capacity: 10,
  available_places: 1,
  cover_media_id: null,
  club_slug: null,
  club_name: null,
  organizer_display_name: "Organizer",
  is_saved: false,
  registration_id: null,
  registration_method: null,
  registration_state: null,
  registration_cash_expires_at: null,
  registration_confirmed_at: null,
} satisfies EventDetail;

afterEach(() => {
  vi.unstubAllGlobals();
  document.cookie = "talaqi_csrf=; Max-Age=0; path=/";
});

describe("MemberRegistrationPanel", () => {
  it("shows confirmation and venue only after server revalidation", async () => {
    document.cookie = "talaqi_csrf=csrf-token; path=/";
    let resolveRefresh: ((value: Response) => void) | undefined;
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(new Response("{}", { status: 201 }))
      .mockImplementationOnce(
        () =>
          new Promise<Response>((resolve) => {
            resolveRefresh = resolve;
          }),
      );
    vi.stubGlobal("fetch", fetcher);
    vi.spyOn(crypto, "randomUUID").mockReturnValue(
      "018f0000-0000-7000-8000-000000000999",
    );
    render(<MemberRegistrationPanel initialEvent={event} locale="en" />);
    fireEvent.click(screen.getByRole("button", { name: "Register" }));
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
    expect(
      screen.queryByText("Registration confirmed"),
    ).not.toBeInTheDocument();
    resolveRefresh?.(
      Response.json({
        ...event,
        available_places: 0,
        exact_address: "Confirmed venue address",
        registration_id: "018f0000-0000-7000-8000-000000000301",
        registration_method: "free",
        registration_state: "confirmed",
        registration_confirmed_at: "2035-04-01T08:00:00Z",
      }),
    );
    expect(
      await screen.findByText("Registration confirmed"),
    ).toBeInTheDocument();
    expect(screen.getByText("Confirmed venue address")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Cancel registration" }),
    ).toBeInTheDocument();
    expect(fetcher).toHaveBeenNthCalledWith(
      1,
      expect.stringContaining("/registrations"),
      expect.objectContaining({
        method: "POST",
        headers: {
          "X-CSRF-Token": "csrf-token",
          "Idempotency-Key": "018f0000-0000-7000-8000-000000000999",
        },
      }),
    );
  });

  it("renders cash instructions, countdown, waitlist, and localized auth errors", async () => {
    const cash = {
      ...event,
      price_type: "cash" as const,
      registration_id: "018f0000-0000-7000-8000-000000000302",
      registration_method: "cash_organizer_confirmed" as const,
      registration_state: "cash_pending",
      registration_cash_expires_at: "2035-04-01T10:00:00Z",
    } satisfies EventDetail;
    const { rerender } = render(
      <MemberRegistrationPanel initialEvent={cash} locale="en" />,
    );
    expect(screen.getByText(/cash confirmation pending/i)).toBeInTheDocument();
    expect(screen.getByText("Time remaining")).toBeInTheDocument();

    rerender(
      <MemberRegistrationPanel
        key="waitlisted"
        initialEvent={{
          ...event,
          available_places: 0,
          registration_state: "waitlisted",
        }}
        locale="en"
      />,
    );
    expect(screen.getByText("You are on the waitlist")).toBeInTheDocument();

    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(
        Response.json(
          {
            error: {
              code: "unauthorized",
              message_key: "errors.unauthorized",
            },
          },
          { status: 401 },
        ),
      ),
    );
    rerender(
      <MemberRegistrationPanel
        key="anonymous"
        initialEvent={event}
        locale="ar"
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "التسجيل" }));
    expect(
      await screen.findByText("سجّل الدخول للتسجيل في هذه الفعالية."),
    ).toBeInTheDocument();
  });
});
