import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { DashboardWorkspace } from "./dashboard-workspace";

afterEach(() => vi.unstubAllGlobals());

const event = {
  id: "11111111-1111-4111-8111-111111111111",
  title: "Community run",
  start_at: "2026-09-10T10:00:00Z",
  status: "published",
  registration_state: "confirmed",
  capacity: 20,
  held: 12,
  cash_pending: 2,
  action_path: "/events/11111111-1111-4111-8111-111111111111",
};
const club = {
  id: "22222222-2222-4222-8222-222222222222",
  name: "City runners",
  slug: "city-runners",
  role: "member",
  status: "published",
  pending_requests: 3,
  action_path: "/clubs/city-runners",
};

function response(value: object, status = 200) {
  vi.stubGlobal(
    "fetch",
    vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify(value), {
        status,
        headers: { "content-type": "application/json" },
      }),
    ),
  );
}

it("renders only member-scoped dashboard sections and actions", async () => {
  response({
    upcoming_events: [event],
    saved_events: [event],
    joined_clubs: [club],
    notifications: [],
    profile_blockers: ["profile_required"],
  });
  render(<DashboardWorkspace role="member" locale="en" />);
  expect(screen.getByRole("status")).toHaveTextContent("Loading dashboard");
  expect(
    await screen.findByRole("heading", { name: "Upcoming events" }),
  ).toBeVisible();
  expect(
    screen.getByText("Complete your profile to unlock all member actions."),
  ).toBeVisible();
  expect(screen.queryByRole("heading", { name: "Managed clubs" })).toBeNull();
});

it("renders organizer queues, alerts, and quick actions", async () => {
  response({
    clubs: [{ ...club, role: "owner" }],
    events: [{ ...event, registration_state: null }],
    alerts: [
      {
        key: "cash_pending",
        action_path: "/organizer/events?state=cash_pending",
      },
    ],
  });
  render(<DashboardWorkspace role="organizer" locale="en" />);
  expect(
    await screen.findByText("Cash confirmations are waiting."),
  ).toBeVisible();
  expect(screen.getByText(/Places held/)).toHaveTextContent("12/20");
  expect(screen.getAllByRole("link", { name: "Open" })).toHaveLength(2);
  expect(screen.queryByRole("heading", { name: "Saved events" })).toBeNull();
});

it("renders localized empty and error states", async () => {
  response({
    upcoming_events: [],
    saved_events: [],
    joined_clubs: [],
    notifications: [],
    profile_blockers: [],
  });
  const { unmount } = render(
    <div dir="rtl">
      <DashboardWorkspace role="member" locale="ar" />
    </div>,
  );
  expect(await screen.findAllByText("لا يوجد ما يُعرض بعد.")).toHaveLength(4);
  unmount();
  response({}, 503);
  render(<DashboardWorkspace role="member" locale="en" />);
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "could not be loaded",
  );
});
