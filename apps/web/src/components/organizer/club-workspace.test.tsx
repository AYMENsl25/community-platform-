import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type {
  ClubJoinRequest,
  ClubMember,
  ManagedClub,
} from "@/lib/api/organizer-client";
import { LocaleProvider } from "@/lib/locale/locale-context";

import { ClubWorkspace } from "./club-workspace";

vi.mock("./communications-panel", () => ({
  CommunicationsPanel: () => <section>Club announcements</section>,
}));

const clubBase = {
  id: "019f9e7d-d7a0-7d86-9166-2053f7de24a3",
  slug: "workspace-club",
  name: "Workspace Club",
  description: "A club profile",
  category_slug: "sports",
  country_code: "TR",
  city_slug: "istanbul",
  membership_policy: "approval_required",
  social_links: {},
  logo_media_id: null,
  cover_media_id: null,
  revision: 1,
  status: "published",
  missing_fields: [] as string[],
  published_at: "2026-07-26T12:00:00Z",
  suspended_at: null,
  suspension_reason: null,
  closed_at: null,
  created_at: "2026-07-26T11:00:00Z",
  updated_at: "2026-07-26T12:00:00Z",
} as const;

const ownerClub: ManagedClub = {
  ...clubBase,
  role: "owner",
  capabilities: [
    "edit_profile",
    "manage_members",
    "change_member_roles",
    "transfer_ownership",
    "close_club",
    "preview_profile",
  ],
};

const owner: ClubMember = {
  user_id: "019f9e7d-d7a0-7d86-9166-2053f7de24a4",
  display_name: "Club Owner",
  email: "owner@example.test",
  role: "owner",
  joined_at: "2026-07-26T11:00:00Z",
};

const member: ClubMember = {
  user_id: "019f9e7d-d7a0-7d86-9166-2053f7de24a5",
  display_name: "Club Member",
  email: "member@example.test",
  role: "member",
  joined_at: "2026-07-26T11:30:00Z",
};

const request: ClubJoinRequest = {
  id: "019f9e7d-d7a0-7d86-9166-2053f7de24a6",
  user_id: "019f9e7d-d7a0-7d86-9166-2053f7de24a7",
  display_name: "Pending Member",
  email: "pending@example.test",
  status: "pending",
  message: "Please add me",
  decision_reason: null,
  decided_at: null,
  created_at: "2026-07-26T11:45:00Z",
};

function renderWorkspace(
  club: ManagedClub = ownerClub,
  members: ClubMember[] = [owner, member],
) {
  return render(
    <LocaleProvider initialLocale="en">
      <ClubWorkspace
        initialClubs={[club]}
        initialMembers={members}
        initialRequests={[request]}
      />
    </LocaleProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("club organizer workspace", () => {
  it("renders owner capabilities, profile preview, member and request tables", () => {
    renderWorkspace();
    expect(
      screen.getByRole("heading", { name: "Club organizer workspace" }),
    ).toBeVisible();
    expect(
      screen.getByRole("heading", { name: "Profile preview" }),
    ).toBeVisible();
    expect(screen.getByRole("table")).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Make club admin" }),
    ).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Transfer ownership" }),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: "Close club" })).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Approve request" }),
    ).toBeDisabled();
    expect(screen.getByRole("option", { name: "Outdoors" })).toHaveValue(
      "outdoors",
    );
    expect(screen.getByRole("option", { name: "Games" })).toHaveValue("games");
  });

  it("renders only capabilities returned by the API", () => {
    renderWorkspace({
      ...ownerClub,
      role: "admin",
      capabilities: ["edit_profile", "manage_members", "preview_profile"],
    });
    expect(
      screen.getByRole("button", { name: "Save club profile" }),
    ).toBeVisible();
    expect(
      screen.queryByRole("button", { name: "Make club admin" }),
    ).toBeNull();
    expect(
      screen.queryByRole("button", { name: "Transfer ownership" }),
    ).toBeNull();
    expect(screen.queryByRole("button", { name: "Close club" })).toBeNull();
  });

  it("requires reason and acknowledgment, focuses the dialog, and supports Escape", async () => {
    renderWorkspace();
    const trigger = screen.getByRole("button", { name: "Make club admin" });
    fireEvent.click(trigger);
    const dialog = screen.getByRole("alertdialog", {
      name: "Confirm role change",
    });
    const reason = screen.getByRole("textbox", { name: "Audit reason" });
    const confirm = screen
      .getByRole("alertdialog")
      .querySelector<HTMLButtonElement>('button[type="submit"]');
    expect(confirm).not.toBeNull();
    await waitFor(() => expect(reason).toHaveFocus());
    expect(confirm).toBeDisabled();
    fireEvent.change(reason, { target: { value: "Trusted organizer" } });
    fireEvent.click(
      screen.getByRole("checkbox", {
        name: "I understand the effect of this action.",
      }),
    );
    expect(confirm).toBeEnabled();
    fireEvent.keyDown(dialog, { key: "Escape" });
    expect(screen.queryByRole("alertdialog")).toBeNull();
    await waitFor(() => expect(trigger).toHaveFocus());
  });

  it("requires explicit confirmation before rejecting a join request", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn<typeof fetch>()
        .mockResolvedValue(new Response(null, { status: 204 })),
    );
    renderWorkspace();
    fireEvent.change(screen.getByRole("textbox", { name: "Decision reason" }), {
      target: { value: "Request does not meet club guidelines" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Reject request" }));
    const dialog = screen.getByRole("alertdialog", {
      name: "Confirm join-request rejection",
    });
    expect(dialog).toHaveTextContent("Pending Member");
    expect(dialog).toHaveTextContent("Workspace Club");
    expect(screen.getByRole("textbox", { name: "Audit reason" })).toHaveValue(
      "Request does not meet club guidelines",
    );
    fireEvent.click(
      screen.getByRole("checkbox", {
        name: "I understand the effect of this action.",
      }),
    );
    fireEvent.submit(dialog.querySelector("form") as HTMLFormElement);
    await waitFor(() =>
      expect(
        screen.getByText("There are no pending join requests."),
      ).toBeVisible(),
    );
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /Workspace Club/ }),
      ).toHaveFocus(),
    );
  });

  it("maps stale server failures without exposing server messages", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: {
              code: "stale_revision",
              message_key: "private.database.message",
              field_errors: [],
              request_id: "33333333-3333-4333-8333-333333333333",
            },
          }),
          { status: 409, headers: { "content-type": "application/json" } },
        ),
      ),
    );
    renderWorkspace();
    const form = screen
      .getByRole("button", { name: "Save club profile" })
      .closest("form");
    expect(form).not.toBeNull();
    if (form) fireEvent.submit(form);
    expect(
      await screen.findByText(
        "This club changed elsewhere. Reload before saving again.",
      ),
    ).toBeVisible();
    expect(screen.queryByText("private.database.message")).toBeNull();
    expect(
      screen.getByText("33333333-3333-4333-8333-333333333333"),
    ).toBeVisible();
  });

  it("shows the member journey as an organizer-empty state", () => {
    render(
      <LocaleProvider initialLocale="en">
        <ClubWorkspace
          initialClubs={[]}
          initialMembers={[]}
          initialRequests={[]}
        />
      </LocaleProvider>,
    );
    expect(
      screen.getByText("You do not own or manage a club yet."),
    ).toBeVisible();
    expect(screen.queryByRole("button", { name: "Close club" })).toBeNull();
  });
});
