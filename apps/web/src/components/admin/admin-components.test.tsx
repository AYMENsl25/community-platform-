import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type {
  ModerationCaseDetail,
  ModerationCaseSummary,
} from "@/lib/api/admin-client";
import { LocaleProvider } from "@/lib/locale/locale-context";

import { AdminAudit } from "./admin-audit";
import { AdminCaseDetail } from "./admin-case-detail";
import { AdminReview } from "./admin-review";

const target = {
  id: "77777777-7777-4777-8777-777777777777",
  target_type: "club" as const,
  display_name: "Safety Club",
  secondary_text: "Istanbul",
  status: "published",
};
const summary: ModerationCaseSummary = {
  id: "88888888-8888-4888-8888-888888888888",
  target,
  category: "safety",
  priority: "emergency",
  status: "open",
  is_emergency: true,
  available_actions: ["suspend", "unpublish"],
  created_at: "2026-07-27T00:00:00Z",
  updated_at: "2026-07-27T00:00:00Z",
};
const detail = {
  ...summary,
  action_history: [],
} satisfies ModerationCaseDetail;

function localized(children: React.ReactNode) {
  return render(<LocaleProvider initialLocale="en">{children}</LocaleProvider>);
}

afterEach(() => vi.unstubAllGlobals());

describe("admin moderation UI", () => {
  it("shows emergency guidance and safe case navigation", () => {
    localized(<AdminReview initialCases={[summary]} />);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "contact local emergency services now",
    );
    expect(screen.getByRole("link", { name: "Open case" })).toHaveAttribute(
      "href",
      `/admin/review/${summary.id}`,
    );
    expect(
      screen.getByRole("heading", { name: "Search platform targets" }),
    ).toBeVisible();
  });

  it("renders exactly the available actions and confirms with one idempotency key", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({
          action: "suspend",
          status: "actioned",
          case: {
            id: detail.id,
            target: {
              id: detail.target.id,
              type: detail.target.target_type,
              label: detail.target.display_name,
              secondary_label: detail.target.secondary_text,
              status: "suspended",
            },
            category: detail.category,
            priority: detail.priority,
            status: "actioned",
            emergency_notice: detail.is_emergency,
            available_actions: ["restore"],
            created_at: detail.created_at,
            updated_at: "2026-07-27T01:00:00Z",
          },
          events: [],
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetcher);
    vi.spyOn(crypto, "randomUUID").mockReturnValue(
      "11111111-1111-4111-8111-111111111111",
    );
    localized(<AdminCaseDetail initialCase={detail} />);
    expect(
      screen.getByRole("button", { name: "Suspend target" }),
    ).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Unpublish club" }),
    ).toBeVisible();
    expect(screen.queryByRole("button", { name: "Restore target" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Suspend target" }));
    fireEvent.change(screen.getByRole("textbox", { name: "Action reason" }), {
      target: { value: "Repeated safety violations" },
    });
    fireEvent.click(
      screen.getByRole("checkbox", {
        name: "I understand the effect of this action.",
      }),
    );
    fireEvent.submit(
      screen.getByRole("alertdialog").querySelector("form") as HTMLFormElement,
    );
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));
    expect(fetcher.mock.calls[0]?.[1]).toMatchObject({
      method: "POST",
      headers: expect.objectContaining({
        "Idempotency-Key": "11111111-1111-4111-8111-111111111111",
      }),
      body: JSON.stringify({
        action: "suspend",
        reason: "Repeated safety violations",
      }),
    });
    expect(
      await screen.findByRole("button", { name: "Restore target" }),
    ).toBeVisible();
  });

  it("shows safe audit evidence", () => {
    localized(
      <AdminAudit
        events={[
          {
            id: "99999999-9999-4999-8999-999999999999",
            action: "moderation.suspend",
            actor_kind: "admin",
            actor_user_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            target_type: "club",
            target_id: target.id,
            reason: "Safety review",
            request_id: "33333333-3333-4333-8333-333333333333",
            safe_before: { previous_status: "published" },
            safe_after: { status: "suspended" },
            created_at: "2026-07-27T01:00:00Z",
          },
        ]}
      />,
    );
    expect(screen.getByText("moderation.suspend")).toBeVisible();
    expect(screen.getByText("Safety review")).toBeVisible();
    expect(
      screen.getByText("33333333-3333-4333-8333-333333333333"),
    ).toBeVisible();
  });
});
