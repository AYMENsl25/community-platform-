import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { LocaleProvider } from "@/lib/locale/locale-context";

import { CommunicationsPanel } from "./communications-panel";

afterEach(() => {
  vi.unstubAllGlobals();
  document.cookie = "talaqi_csrf=; Max-Age=0; path=/";
});

it("loads history and publishes a one-way audience-scoped event update", async () => {
  document.cookie = "talaqi_csrf=csrf-token; path=/";
  const published = {
    id: "019f9e7d-d7a0-7d86-9166-2053f7de2499",
    title: "New time",
    body: "Doors open at 18:30.",
    audience: "confirmed",
    published_at: "2026-08-10T12:00:00Z",
  };
  const fetcher = vi
    .fn<typeof fetch>()
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ items: [] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    )
    .mockResolvedValueOnce(
      new Response(JSON.stringify(published), {
        status: 201,
        headers: { "content-type": "application/json" },
      }),
    );
  vi.stubGlobal("fetch", fetcher);

  render(
    <LocaleProvider initialLocale="en">
      <CommunicationsPanel
        kind="event"
        resourceId="019f9e7d-d7a0-7d86-9166-2053f7de2401"
        revision={3}
      />
    </LocaleProvider>,
  );
  await screen.findByText("No updates have been published yet.");
  fireEvent.change(screen.getByLabelText("Subject"), {
    target: { value: published.title },
  });
  fireEvent.change(screen.getByLabelText("Message"), {
    target: { value: published.body },
  });
  fireEvent.change(screen.getByLabelText("Audience"), {
    target: { value: "confirmed" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Publish update" }));

  await screen.findByText(published.body);
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
  const [, request] = fetcher.mock.calls[1] ?? [];
  expect(request).toMatchObject({ method: "POST" });
  expect((request?.headers as Record<string, string>)["X-CSRF-Token"]).toBe(
    "csrf-token",
  );
  expect(JSON.parse(String(request?.body))).toMatchObject({
    audience: "confirmed",
    revision: 3,
    title: published.title,
  });
  expect(screen.queryByText(/repl/i)).toBeVisible();
  expect(screen.queryByRole("textbox", { name: /reply/i })).toBeNull();
});
