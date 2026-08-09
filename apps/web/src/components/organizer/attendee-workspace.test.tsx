import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { translate } from "@talaqi/translations";
import { LocaleProvider } from "@/lib/locale/locale-context";

import { AttendeeWorkspace } from "./attendee-workspace";

const eventId = "019f9e7d-d7a0-7d86-9166-2053f7de2401";
const cashAttendee = {
  registration_id: "019f9e7d-d7a0-7d86-9166-2053f7de2501",
  user_id: "019f9e7d-d7a0-7d86-9166-2053f7de2502",
  username: "member",
  display_name: "Fixture Member",
  method: "cash_organizer_confirmed",
  state: "cash_pending",
  waitlist_sequence: null,
  cash_expires_at: "2035-09-05T08:00:00Z",
  confirmed_at: null,
  created_at: "2035-09-01T08:00:00Z",
};
const summary = {
  held: 1,
  confirmed: 0,
  cash_pending: 1,
  waitlisted: 2,
  cancelled: 0,
  expired: 0,
};

function json(value: unknown, status = 200) {
  return Response.json(value, { status });
}

function view(locale: "en" | "ar" = "en") {
  return render(
    <LocaleProvider initialLocale={locale}>
      <AttendeeWorkspace eventId={eventId} capacity={10} />
    </LocaleProvider>,
  );
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  document.cookie = "talaqi_csrf=; Max-Age=0; path=/";
});

describe("AttendeeWorkspace", () => {
  it("loads a server summary and confirms cash before reloading state", async () => {
    document.cookie = "talaqi_csrf=csrf; path=/";
    vi.spyOn(crypto, "randomUUID").mockReturnValue(
      "019f9e7d-d7a0-7d86-9166-2053f7de2599",
    );
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(json({ items: [cashAttendee], next_cursor: null }))
      .mockResolvedValueOnce(json(summary))
      .mockResolvedValueOnce(json({ ...cashAttendee, state: "confirmed" }))
      .mockResolvedValueOnce(
        json({
          items: [{ ...cashAttendee, state: "confirmed" }],
          next_cursor: null,
        }),
      )
      .mockResolvedValueOnce(
        json({ ...summary, confirmed: 1, cash_pending: 0 }),
      );
    vi.stubGlobal("fetch", fetcher);
    view();

    expect(await screen.findByText("Fixture Member")).toBeVisible();
    expect(screen.getByText("2")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Confirm cash" }));
    expect(
      await screen.findByText(
        "Cash registration confirmed from the latest server state.",
      ),
    ).toBeVisible();
    expect(fetcher.mock.calls[2]?.[0]).toContain("/confirm-cash");
    expect(fetcher.mock.calls[2]?.[1]).toMatchObject({
      method: "POST",
      headers: expect.objectContaining({
        "X-CSRF-Token": "csrf",
        "Idempotency-Key": "019f9e7d-d7a0-7d86-9166-2053f7de2599",
      }),
    });
  });

  it("applies filters, appends pagination, and queues only a private export status", async () => {
    const second = {
      ...cashAttendee,
      registration_id: `${cashAttendee.registration_id.slice(0, -1)}2`,
      display_name: "Second Member",
    };
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(
        json({ items: [cashAttendee], next_cursor: "next" }),
      )
      .mockResolvedValueOnce(json(summary))
      .mockResolvedValueOnce(
        json({ items: [cashAttendee], next_cursor: "next" }),
      )
      .mockResolvedValueOnce(json(summary))
      .mockResolvedValueOnce(json({ items: [second], next_cursor: null }))
      .mockResolvedValueOnce(json(summary))
      .mockResolvedValueOnce(
        json(
          {
            request_id: "019f9e7d-d7a0-7d86-9166-2053f7de2600",
            status: "queued",
          },
          202,
        ),
      );
    vi.stubGlobal("fetch", fetcher);
    view();
    await screen.findByText("Fixture Member");
    fireEvent.change(screen.getByLabelText("Search attendees"), {
      target: { value: "member" },
    });
    fireEvent.change(screen.getByLabelText("Registration state"), {
      target: { value: "cash_pending" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply filters" }));
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(4));
    expect(String(fetcher.mock.calls[2]?.[0])).toContain("state=cash_pending");
    expect(String(fetcher.mock.calls[2]?.[0])).toContain("search=member");
    fireEvent.click(
      screen.getByRole("button", { name: "Load more attendees" }),
    );
    expect(await screen.findByText("Second Member")).toBeVisible();
    fireEvent.click(
      screen.getByRole("button", { name: "Prepare private CSV" }),
    );
    expect(
      await screen.findByText(/Private CSV preparation is queued/),
    ).toBeVisible();
    expect(document.body).not.toHaveTextContent("request_id");
  });

  it("renders usable Arabic labels in RTL context and safe authorization errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn<typeof fetch>()
        .mockResolvedValueOnce(json({ error: { code: "forbidden" } }, 403))
        .mockResolvedValueOnce(json({ error: { code: "forbidden" } }, 403)),
    );
    view("ar");
    expect(
      await screen.findByText(translate("ar", "errors.forbidden")),
    ).toBeVisible();
    expect(screen.getByLabelText("البحث عن الحضور")).toBeVisible();
  });
});
