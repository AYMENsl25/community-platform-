import { expect, test, type Page } from "@playwright/test";

const caseId = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee";

async function signIn(
  page: Page,
  kind: "platform-admin" | "platform-admin-no-mfa" | "member",
  locale = "en",
) {
  await page.context().addCookies([
    {
      name: "talaqi_access",
      value: `fixture-${kind}`,
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

async function confirmByKeyboard(
  page: Page,
  actionName: RegExp,
  reason: string,
) {
  const dialog = page.getByRole("alertdialog");
  const reasonInput = dialog.getByRole("textbox", { name: "Action reason" });
  await expect(reasonInput).toBeFocused();
  await page.keyboard.insertText(reason);
  await page.keyboard.press("Tab");
  await page.keyboard.press("Space");
  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  await expect(dialog.getByRole("button", { name: actionName })).toBeFocused();
  await page.keyboard.press("Enter");
}

test("MFA admin reviews emergency case, suspends and restores with audit evidence", async ({
  page,
}) => {
  await signIn(page, "platform-admin");
  await page.goto("/admin/review");
  await expect(
    page.getByRole("heading", { name: "Moderation review" }),
  ).toBeVisible();
  await expect(page.getByRole("alert")).toContainText(
    "contact local emergency services now",
  );
  await page.getByLabel("Target type").selectOption("club");
  await page.getByLabel("Search").fill("Istanbul");
  await page.getByRole("button", { name: "Search targets" }).click();
  await expect(page.getByText("Istanbul Neighbours").last()).toBeVisible();
  await page.getByRole("link", { name: "Open case" }).click();
  await expect(page).toHaveURL(new RegExp(`/admin/review/${caseId}`));
  await expect(page.getByText("PRIVATE_EXACT_ADDRESS_CANARY")).toHaveCount(0);
  const suspend = page.getByRole("button", { name: "Suspend target" });
  await suspend.focus();
  await page.keyboard.press("Enter");
  await confirmByKeyboard(page, /Suspend target/, "Immediate safety review");
  await expect(page.getByRole("status")).toContainText("completed");
  await expect(
    page.getByRole("button", { name: "Restore target" }),
  ).toBeVisible();
  await page.goto("/explore");
  await expect(
    page.getByRole("link", { name: /Istanbul Neighbours/i }),
  ).toHaveCount(0);
  await page.goto("/admin/audit");
  await expect(page.getByText("moderation.suspend")).toBeVisible();
  await expect(page.getByText("Immediate safety review")).toBeVisible();
  await page.goto(`/admin/review/${caseId}`);
  await page.getByRole("button", { name: "Restore target" }).click();
  await confirmByKeyboard(page, /Restore target/, "Safety review completed");
  await expect(page.getByRole("status")).toContainText("completed");
});

test("ordinary member receives no admin data or controls", async ({ page }) => {
  await signIn(page, "member");
  await page.goto("/admin/review");
  await expect(page.getByRole("alert")).toContainText("permission");
  await expect(page.getByText("Istanbul Neighbours")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: /Suspend|Restore|Unpublish/ }),
  ).toHaveCount(0);
});

test("admin without MFA is denied a protected action", async ({ page }) => {
  await signIn(page, "platform-admin-no-mfa");
  await page.goto(`/admin/review/${caseId}`);
  const action = page
    .getByRole("button", {
      name: /Suspend target|Restore target|Unpublish club/,
    })
    .first();
  await action.click();
  await confirmByKeyboard(
    page,
    /Suspend target|Restore target|Unpublish club/,
    "MFA denial check",
  );
  await expect(page.getByRole("alertdialog")).toBeVisible();
  await expect(page.locator(".tq-admin-alert")).toContainText("permission");
  await expect(page.getByRole("status")).toHaveCount(0);
});

test("Arabic admin review is RTL and narrow-screen safe", async ({ page }) => {
  await signIn(page, "platform-admin", "ar");
  await page.setViewportSize({ width: 360, height: 760 });
  await page.goto("/admin/review");
  await expect(page.locator(".tq-workspace-shell")).toHaveAttribute(
    "dir",
    "rtl",
  );
  await expect(
    page.getByRole("heading", { name: "مراجعة الإشراف" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () =>
        document.documentElement.scrollWidth >
        document.documentElement.clientWidth,
    ),
  ).toBe(false);
});
