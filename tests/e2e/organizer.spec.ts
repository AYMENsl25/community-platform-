import { expect, test, type Page } from "@playwright/test";

test.describe.configure({ mode: "serial" });

const organizerClubId = "77777777-7777-4777-8777-777777777777";

async function signInAs(
  page: Page,
  role: "owner" | "admin" | "member",
  locale = "en",
) {
  await page.context().addCookies([
    {
      name: "talaqi_access",
      value: `fixture-${role}`,
      domain: "127.0.0.1",
      path: "/",
    },
    {
      name: "talaqi_csrf",
      value: "fixture-csrf",
      domain: "127.0.0.1",
      path: "/",
    },
    { name: "talaqi_locale", value: locale, domain: "127.0.0.1", path: "/" },
  ]);
}

async function completeConfirmationByKeyboard(
  page: Page,
  dialogName: string,
  actionName: string,
  reason: string,
) {
  const dialog = page.getByRole("alertdialog", { name: dialogName });
  const reasonInput = dialog.getByRole("textbox", { name: "Audit reason" });
  const acknowledgment = dialog.getByRole("checkbox", {
    name: "I understand the effect of this action.",
  });
  const cancel = dialog.getByRole("button", { name: "Cancel" });
  const confirm = dialog.getByRole("button", { name: actionName });

  await expect(reasonInput).toBeFocused();
  await page.keyboard.insertText(reason);
  await page.keyboard.press("Tab");
  await expect(acknowledgment).toBeFocused();
  await page.keyboard.press("Space");
  await expect(acknowledgment).toBeChecked();
  await page.keyboard.press("Tab");
  await expect(cancel).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(confirm).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(reasonInput).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(confirm).toBeFocused();
  await page.keyboard.press("Enter");
}

test("owner completes a draft and confirms a role change entirely by keyboard", async ({
  page,
}) => {
  await signInAs(page, "owner");
  await page.goto("/organizer/clubs");
  await expect(
    page.getByRole("heading", { name: "Club organizer workspace" }),
  ).toBeVisible();

  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Skip to main content" }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#main-content")).toBeFocused();

  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("button", { name: /Workspace Runners/ }),
  ).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("button", { name: /Safe Switch Club/ }),
  ).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("textbox", { name: "Club name" })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("textbox", { name: "Public link name" }),
  ).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("textbox", { name: "Description" }),
  ).toBeFocused();
  await page.keyboard.insertText("A complete runner community.");
  await page.keyboard.press("Tab");
  await expect(page.getByLabel("Category")).toBeFocused();
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("Tab");
  await expect(page.getByLabel("Country")).toBeFocused();
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("Tab");
  await expect(page.getByLabel("City")).toBeFocused();
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("Tab");
  await expect(page.getByLabel("Membership policy")).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("button", { name: "Save club profile" }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("status")).toContainText("Club profile saved.");
  await expect(page.getByText("Published").first()).toBeVisible();

  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Open public profile" }),
  ).toBeFocused();
  await page.keyboard.press("Tab");
  const promoteButton = page.getByRole("button", {
    name: "Make club admin",
  });
  await expect(promoteButton).toBeFocused();
  await page.keyboard.press("Enter");
  const dialog = page.getByRole("alertdialog", { name: "Confirm role change" });
  await expect(dialog).toContainText("Fixture Member");
  await completeConfirmationByKeyboard(
    page,
    "Confirm role change",
    "Make club admin",
    "Trusted organizer",
  );
  await expect(page.getByRole("status")).toContainText(
    "The action was completed.",
  );
  await expect(
    page.getByRole("button", { name: "Remove club-admin role" }),
  ).toBeFocused();
});

test("ownership transfer confirmation names its target and preserves keyboard context", async ({
  page,
}) => {
  await signInAs(page, "owner");
  await page.goto("/organizer/clubs");
  let releaseRefresh = () => {};
  const refreshReleased = new Promise<void>((resolve) => {
    releaseRefresh = resolve;
  });
  let observeRefresh = () => {};
  const refreshObserved = new Promise<void>((resolve) => {
    observeRefresh = resolve;
  });
  await page.route("**/api/organizer/api/v1/clubs/managed", async (route) => {
    observeRefresh();
    await refreshReleased;
    await route.continue();
  });
  const memberRow = page.getByRole("row", { name: /Fixture Member/ });
  const transferButton = memberRow.getByRole("button", {
    name: "Transfer ownership",
  });

  await transferButton.focus();
  await page.keyboard.press("Enter");
  const firstDialog = page.getByRole("alertdialog", {
    name: "Confirm ownership transfer",
  });
  await expect(firstDialog).toContainText("Fixture Member");
  await expect(firstDialog).toContainText("Workspace Runners");
  await page.keyboard.press("Escape");
  await expect(firstDialog).toHaveCount(0);
  await expect(transferButton).toBeFocused();

  await page.keyboard.press("Enter");
  const transferRequest = page.waitForRequest(
    (request) =>
      request.method() === "POST" &&
      request
        .url()
        .endsWith(`/api/v1/clubs/${organizerClubId}/ownership-transfer`),
  );
  await completeConfirmationByKeyboard(
    page,
    "Confirm ownership transfer",
    "Transfer ownership",
    "Planned leadership handover",
  );
  const request = await transferRequest;
  expect(request.postDataJSON()).toEqual({
    target_user_id: "99999999-9999-4999-8999-999999999999",
    reason: "Planned leadership handover",
  });
  await refreshObserved;
  const pendingDialog = page.getByRole("alertdialog", {
    name: "Confirm ownership transfer",
  });
  await expect(
    pendingDialog.getByRole("button", { name: "Transfer ownership" }),
  ).toBeDisabled();
  await page.keyboard.press("Escape");
  await expect(pendingDialog).toBeVisible();
  releaseRefresh();
  await expect(page.getByRole("status")).toContainText(
    "The action was completed.",
  );
});

test("club closure confirmation identifies the effect and requires acknowledgment", async ({
  page,
}) => {
  await signInAs(page, "owner");
  await page.goto("/organizer/clubs");
  const closeButton = page.getByRole("button", { name: "Close club" });

  await closeButton.focus();
  await page.keyboard.press("Enter");
  const dialog = page.getByRole("alertdialog", {
    name: "Confirm club closure",
  });
  await expect(dialog).toContainText("Workspace Runners");
  await expect(dialog).toContainText(
    "This action changes access immediately and is recorded in the audit log.",
  );
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(closeButton).toBeFocused();

  await page.keyboard.press("Enter");
  const closeRequest = page.waitForRequest(
    (request) =>
      request.method() === "POST" &&
      request.url().endsWith(`/api/v1/clubs/${organizerClubId}/close`),
  );
  await completeConfirmationByKeyboard(
    page,
    "Confirm club closure",
    "Close club",
    "The club has completed its work",
  );
  const request = await closeRequest;
  expect(request.postDataJSON()).toEqual({
    reason: "The club has completed its work",
  });
  await expect(page.getByRole("status")).toContainText(
    "The action was completed.",
  );
  await expect(page.getByText("Closed").first()).toBeVisible();
  await expect(
    page.getByRole("button", { name: /Workspace Runners/ }),
  ).toBeFocused();
});

test("switching clubs clears stale people before delayed and failed loads settle", async ({
  page,
}) => {
  await signInAs(page, "owner");
  await page.goto("/organizer/clubs");
  await expect(page.getByText("Fixture Member", { exact: true })).toBeVisible();
  await expect(
    page.getByText("Pending Fixture", { exact: true }),
  ).toBeVisible();

  const secondClub = page.getByRole("button", { name: /Safe Switch Club/ });
  await secondClub.focus();
  await page.keyboard.press("Enter");

  expect(await page.getByText("Fixture Member", { exact: true }).count()).toBe(
    0,
  );
  expect(await page.getByText("Pending Fixture", { exact: true }).count()).toBe(
    0,
  );
  await expect(
    page.getByText("Second Club Member", { exact: true }),
  ).toBeVisible();
  await expect(page.locator(".tq-organizer__alert")).toContainText(
    "An internal service error occurred.",
  );
  await expect(page.getByText("Fixture Member", { exact: true })).toHaveCount(
    0,
  );
  await expect(page.getByText("Pending Fixture", { exact: true })).toHaveCount(
    0,
  );
});

test("club admin manages requests but receives no owner-only actions", async ({
  page,
}) => {
  await signInAs(page, "admin");
  await page.goto("/organizer/clubs");
  await expect(page.getByText("Club admin").first()).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Save club profile" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Transfer ownership" }),
  ).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Close club" })).toHaveCount(0);
  await page
    .getByRole("textbox", { name: "Decision reason" })
    .fill("Profile reviewed");
  await page.getByRole("button", { name: "Approve request" }).click();
  await expect(
    page.getByText("There are no pending join requests."),
  ).toBeVisible();
});

test("club admin explicitly confirms request rejection and returns to stable focus", async ({
  page,
}) => {
  await signInAs(page, "admin");
  await page.goto("/organizer/clubs");
  const reason = page.getByRole("textbox", { name: "Decision reason" });
  await reason.fill("Request does not meet club guidelines");
  const reject = page.getByRole("button", { name: "Reject request" });
  await reject.focus();
  await page.keyboard.press("Enter");
  const dialog = page.getByRole("alertdialog", {
    name: "Confirm join-request rejection",
  });
  await expect(dialog).toContainText("Pending Fixture");
  await expect(dialog).toContainText("Workspace Runners");
  const rejectRequest = page.waitForRequest(
    (request) =>
      request.method() === "POST" && request.url().endsWith("/reject"),
  );
  await completeConfirmationByKeyboard(
    page,
    "Confirm join-request rejection",
    "Reject request",
    "",
  );
  const request = await rejectRequest;
  expect(request.postDataJSON()).toEqual({
    reason: "Request does not meet club guidelines",
  });
  await expect(
    page.getByText("There are no pending join requests."),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: /Workspace Runners/ }),
  ).toBeFocused();
});

test("ordinary member sees no organizer data or actions", async ({ page }) => {
  await signInAs(page, "member");
  await page.goto("/organizer/clubs");
  await expect(
    page.getByText("You do not own or manage a club yet."),
  ).toBeVisible();
  await expect(page.getByText("owner@example.test")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Save club profile" }),
  ).toHaveCount(0);
});

test("Arabic organizer workspace is RTL, narrow-screen safe, and dismisses confirmation", async ({
  page,
}) => {
  await signInAs(page, "owner", "ar");
  await page.setViewportSize({ width: 360, height: 760 });
  await page.goto("/organizer/clubs");
  await expect(page.locator(".tq-workspace-shell")).toHaveAttribute(
    "dir",
    "rtl",
  );
  await expect(
    page.getByRole("heading", { name: "مساحة عمل منظّم النادي" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "تعيين مدير للنادي" }).click();
  await expect(page.getByRole("alertdialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("alertdialog")).toHaveCount(0);
  const hasOverflow = await page.evaluate(
    () =>
      document.documentElement.scrollWidth >
      document.documentElement.clientWidth,
  );
  expect(hasOverflow).toBe(false);
});

test("event owner sees server-owned club and independent workflows", async ({
  page,
}) => {
  await signInAs(page, "owner");
  await page.goto("/organizer/events");
  await expect(
    page.getByRole("heading", { name: "Event organizer workspace" }),
  ).toBeVisible();
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Skip to main content" }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#main-content")).toBeFocused();
  await expect(
    page.getByRole("option", { name: "Independent event" }),
  ).toHaveCount(1);
  await expect(
    page.getByRole("option", { name: "Workspace Runners" }),
  ).toHaveCount(1);
  await expect(
    page.getByRole("button", { name: "Duplicate as draft" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Delete draft" }),
  ).toBeVisible();
  await expect(page.getByText("Cash Fixture Member")).toBeVisible();
  await expect(page.getByText("Waiting Fixture Member")).toBeVisible();
  await expect(page.getByText("1").first()).toBeVisible();
  await page.getByRole("button", { name: "Confirm cash" }).click();
  await expect(
    page.getByText("Cash registration confirmed from the latest server state."),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Confirm cash" })).toHaveCount(
    0,
  );
  await page.getByRole("button", { name: "Prepare private CSV" }).click();
  await expect(
    page.getByText(/Private CSV preparation is queued/),
  ).toBeVisible();
});

test("club admin uses attendee filters in Arabic on a narrow keyboard-safe layout", async ({
  page,
}) => {
  await signInAs(page, "admin", "ar");
  await page.setViewportSize({ width: 360, height: 760 });
  await page.goto("/organizer/events");
  await expect(page.getByText("Waiting Fixture Member")).toBeVisible();
  await expect(page.locator(".tq-workspace-shell")).toHaveAttribute(
    "dir",
    "rtl",
  );
  const search = page.getByLabel("البحث عن الحضور");
  await search.focus();
  await expect(search).toBeFocused();
  await search.fill("waiting");
  await page.getByLabel("حالة التسجيل").selectOption("waitlisted");
  await page.getByRole("button", { name: "تطبيق المرشحات" }).click();
  await expect(page.getByText("Waiting Fixture Member")).toBeVisible();
  await expect(page.getByText("Cash Fixture Member")).toHaveCount(0);
  expect(
    await page.evaluate(
      () =>
        document.documentElement.scrollWidth >
        document.documentElement.clientWidth,
    ),
  ).toBe(false);
});

test("ordinary member is denied event ownership and Arabic stays RTL on mobile", async ({
  page,
}) => {
  await signInAs(page, "member", "ar");
  await page.setViewportSize({ width: 360, height: 760 });
  await page.goto("/organizer/events");
  await expect(page.locator(".tq-workspace-shell")).toHaveAttribute(
    "dir",
    "rtl",
  );
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.locator(".tq-organizer__header button")).toBeDisabled();
  await expect(page.getByRole("option")).toHaveCount(0);
  const hasOverflow = await page.evaluate(
    () =>
      document.documentElement.scrollWidth >
      document.documentElement.clientWidth,
  );
  expect(hasOverflow).toBe(false);
});
