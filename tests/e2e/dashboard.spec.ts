import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { translate } from "../../packages/translations/src/index";

async function signIn(
  context: import("@playwright/test").BrowserContext,
  role: "member" | "owner",
  locale = "en",
) {
  await context.addCookies([
    {
      name: "talaqi_access",
      value: `fixture-${role}`,
      domain: "127.0.0.1",
      path: "/",
    },
    { name: "talaqi_locale", value: locale, domain: "127.0.0.1", path: "/" },
  ]);
}

test("member dashboard is scoped, responsive, and RTL", async ({
  context,
  page,
}) => {
  await signIn(context, "member", "ar");
  await page.setViewportSize({ width: 320, height: 720 });
  await page.goto("/overview");
  await expect(
    page.getByRole("heading", {
      name: translate("ar", "dashboard.member.title"),
    }),
  ).toBeVisible();
  await expect(page.getByText("Istanbul Community Run").first()).toBeVisible();
  await expect(
    page.getByRole("heading", { name: translate("ar", "dashboard.saved") }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", {
      name: translate("ar", "dashboard.managedClubs"),
    }),
  ).toHaveCount(0);
  await expect(page.locator(".tq-workspace-shell")).toHaveAttribute(
    "dir",
    "rtl",
  );
  expect(
    await page.evaluate(
      () =>
        document.documentElement.scrollWidth >
        document.documentElement.clientWidth,
    ),
  ).toBe(false);
  const accessibility = await new AxeBuilder({ page })
    .include("#main-content")
    .analyze();
  expect(
    accessibility.violations.filter((item) =>
      ["serious", "critical"].includes(item.impact ?? ""),
    ),
  ).toEqual([]);
  const ticket = page
    .getByRole("link", {
      name: translate("ar", "dashboard.action.ticket"),
    })
    .first();
  await ticket.focus();
  await expect(ticket).toBeFocused();
});

test("organizer dashboard shows queues, alerts, and quick actions", async ({
  context,
  page,
}) => {
  await signIn(context, "owner");
  await page.goto("/organizer/overview");
  await expect(
    page.getByRole("heading", { name: "Organizer dashboard" }),
  ).toBeVisible();
  await expect(page.getByText("Cash confirmations are waiting.")).toBeVisible();
  await expect(page.getByText(/Places held/)).toContainText("1/");
  await expect(page.getByRole("heading", { name: "Saved events" })).toHaveCount(
    0,
  );
  await expect(page.getByRole("link", { name: "Open" })).toHaveCount(2);
  const accessibility = await new AxeBuilder({ page })
    .include("#main-content")
    .analyze();
  expect(
    accessibility.violations.filter((item) =>
      ["serious", "critical"].includes(item.impact ?? ""),
    ),
  ).toEqual([]);
  const cashAlert = page.getByRole("link", {
    name: "Cash confirmations are waiting.",
  });
  await cashAlert.focus();
  await expect(cashAlert).toBeFocused();
});
