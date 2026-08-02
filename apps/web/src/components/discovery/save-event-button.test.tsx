import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SaveEventButton } from "./save-event-button";

afterEach(() => {
  vi.unstubAllGlobals();
  document.cookie = "talaqi_csrf=; Max-Age=0; path=/";
});

describe("SaveEventButton", () => {
  it("saves with CSRF and exposes the updated pressed state", async () => {
    document.cookie = "talaqi_csrf=csrf-token; path=/";
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetcher);
    render(
      <SaveEventButton
        eventId="018f0000-0000-7000-8000-000000000201"
        initialSaved={false}
        locale="en"
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Save event" }));
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Remove saved event" }),
      ).toHaveAttribute("aria-pressed", "true"),
    );
    expect(fetcher).toHaveBeenCalledWith(
      "/api/public/api/v1/events/018f0000-0000-7000-8000-000000000201/saved",
      expect.objectContaining({
        method: "PUT",
        credentials: "same-origin",
        cache: "no-store",
        headers: { "X-CSRF-Token": "csrf-token" },
      }),
    );
  });

  it("shows only a localized generic error on failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn<typeof fetch>()
        .mockResolvedValue(
          new Response("private upstream detail", { status: 403 }),
        ),
    );
    render(
      <SaveEventButton eventId="event" initialSaved={false} locale="en" />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Save event" }));
    expect(
      await screen.findByText("We could not load this content."),
    ).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent("private upstream detail");
  });
});
