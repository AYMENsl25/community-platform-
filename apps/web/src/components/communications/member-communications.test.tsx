import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { MemberCommunications } from "./member-communications";

afterEach(() => vi.unstubAllGlobals());

it("shows only the eligible member history returned by the scoped endpoint", async () => {
  const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
    new Response(
      JSON.stringify({
        items: [
          {
            id: "019f9e7d-d7a0-7d86-9166-2053f7de2499",
            title: "Confirmed members",
            body: "Your meeting point changed.",
            audience: "confirmed",
            published_at: "2026-08-10T12:00:00Z",
          },
        ],
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    ),
  );
  vi.stubGlobal("fetch", fetcher);

  render(
    <MemberCommunications
      kind="event"
      resourceId="019f9e7d-d7a0-7d86-9166-2053f7de2401"
      locale="en"
    />,
  );

  expect(await screen.findByText("Your meeting point changed.")).toBeVisible();
  expect(fetcher).toHaveBeenCalledWith(
    "/api/organizer/api/v1/events/019f9e7d-d7a0-7d86-9166-2053f7de2401/updates",
    expect.objectContaining({ credentials: "include" }),
  );
  expect(screen.queryByRole("textbox")).toBeNull();
});

it("does not disclose content when the scoped endpoint denies access", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(null, { status: 404 })),
  );
  const { container } = render(
    <MemberCommunications
      kind="club"
      resourceId="019f9e7d-d7a0-7d86-9166-2053f7de2402"
      locale="en"
    />,
  );
  await vi.waitFor(() => expect(container).toBeEmptyDOMElement());
});
