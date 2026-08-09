import { expect, test } from "@playwright/test";
import { translate } from "../../packages/translations/src/index";

const locales = [
  ["en", "ltr"],
  ["tr", "ltr"],
  ["fr", "ltr"],
  ["ar", "rtl"],
] as const;
const privateCanary = "PRIVATE_EXACT_ADDRESS_CANARY";
const eventPath = "/events/11111111-1111-4111-8111-111111111111";

async function registrationCookies(
  context: import("@playwright/test").BrowserContext,
  access: string,
  locale = "en",
) {
  await context.addCookies([
    { name: "talaqi_locale", value: locale, domain: "127.0.0.1", path: "/" },
    { name: "talaqi_access", value: access, domain: "127.0.0.1", path: "/" },
    {
      name: "talaqi_csrf",
      value: "fixture-csrf",
      domain: "127.0.0.1",
      path: "/",
    },
  ]);
}

for (const [locale, direction] of locales) {
  test(`${locale} discovers only public-safe content`, async ({
    context,
    page,
  }) => {
    await context.addCookies([
      { name: "talaqi_locale", value: locale, domain: "127.0.0.1", path: "/" },
    ]);
    await page.goto(
      "/explore?country=TR&city=istanbul&category=sports&price=free&search=run",
    );
    await expect(page.locator("html")).toHaveAttribute("lang", locale);
    await expect(page.locator("html")).toHaveAttribute("dir", direction);
    await expect(page).toHaveURL(/country=TR/);
    await expect(page).toHaveURL(/price=free/);
    await expect(page.getByText("Istanbul Community Run")).toBeVisible();
    await expect(page.getByText(privateCanary)).toHaveCount(0);
    await expect(page.locator("body")).not.toContainText("latitude");
    await expect(page.locator("body")).not.toContainText("longitude");
  });
}

test("member free registration is confirmed from refreshed server state and can be cancelled", async ({
  context,
  page,
}) => {
  await registrationCookies(context, "fixture-member-free");
  await page.setViewportSize({ width: 320, height: 720 });
  await page.goto(eventPath);
  await page.getByRole("button", { name: "Register" }).click();
  await expect(page.getByText("Registration confirmed")).toBeVisible();
  await expect(page.getByText("Moda Community Hall, Kadikoy")).toBeVisible();
  await page.getByRole("button", { name: "Cancel registration" }).click();
  await expect(page.getByRole("button", { name: "Register" })).toBeVisible();
  await expect(page.getByText("Moda Community Hall, Kadikoy")).toHaveCount(0);
});

test("cash reservation shows instructions and countdown in mobile RTL", async ({
  context,
  page,
}) => {
  await registrationCookies(context, "fixture-member-cash", "ar");
  await page.setViewportSize({ width: 320, height: 720 });
  await page.goto(`${eventPath}?locale=ar`);
  await page
    .getByRole("button", { name: translate("ar", "registration.register") })
    .click();
  await expect(
    page.getByText(translate("ar", "registration.cashPending")),
  ).toBeVisible();
  await expect(
    page.getByText(translate("ar", "registration.remaining")),
  ).toBeVisible();
  await expect(page.getByText("Moda Community Hall, Kadikoy")).toBeVisible();
  await expect(page.locator(".tq-public-shell")).toHaveAttribute("dir", "rtl");
  expect(
    await page.evaluate(
      () =>
        document.documentElement.scrollWidth >
        document.documentElement.clientWidth,
    ),
  ).toBe(false);
});

test("full event returns a server-authoritative waitlist state", async ({
  context,
  page,
}) => {
  await registrationCookies(context, "fixture-member-full");
  await page.goto(eventPath);
  await page.getByRole("button", { name: "Join waitlist" }).click();
  await expect(page.getByText("You are on the waitlist")).toBeVisible();
  await expect(page.getByText("Moda Community Hall, Kadikoy")).toHaveCount(0);
});

test("unauthenticated registration gives an actionable sign-in error", async ({
  page,
}) => {
  await page.goto(eventPath);
  await page.getByRole("button", { name: "Register" }).click();
  await expect(
    page.getByText("Sign in to register for this event."),
  ).toBeVisible();
});

test("desktop navigation reaches club and event details", async ({ page }) => {
  await page.goto("/explore");
  await page.getByRole("link", { name: /Istanbul Community Run/i }).click();
  await expect(page).toHaveURL(
    /\/events\/11111111-1111-4111-8111-111111111111/,
  );
  await expect(page.getByText("Park entrance").first()).toBeVisible();
  await expect(page.getByText(privateCanary)).toHaveCount(0);

  await page.goto("/explore");
  await page
    .getByRole("link", { name: /Istanbul Neighbours/i })
    .first()
    .click();
  await expect(page).toHaveURL(/\/clubs\/istanbul-neighbours/);
  await expect(page.getByText("42 members")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Events from this club" }),
  ).toBeVisible();
  await expect(page.getByText("Istanbul Park Yoga")).toBeVisible();
});

test("filters are URL-backed and deterministic empty/error states are safe", async ({
  page,
}) => {
  await page.goto("/explore?search=fixture-empty");
  await expect(page.getByRole("status")).toBeVisible();
  await page.goto("/explore?search=fixture-error");
  await expect(page.locator(".tq-result-state--error")).toBeVisible();
  await expect(page.getByText(privateCanary)).toHaveCount(0);
});

test("mobile layout has skip navigation, keyboard filters, and no overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 720 });
  await page.goto("/explore");
  await page.keyboard.press("Tab");
  await expect(page.locator('a[href="#main-content"]')).toBeFocused();
  await page.getByRole("button", { name: /open filters/i }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(
    page.getByRole("button", { name: /open filters/i }),
  ).toBeFocused();
  const overflow = await page.evaluate(
    () =>
      document.documentElement.scrollWidth >
      document.documentElement.clientWidth,
  );
  expect(overflow).toBe(false);
});

for (const [locale, direction] of locales) {
  test(`${locale} event details are complete, safe, and keyboard usable`, async ({
    context,
    page,
  }) => {
    await context.addCookies([
      { name: "talaqi_locale", value: locale, domain: "127.0.0.1", path: "/" },
      {
        name: "talaqi_access",
        value: "fixture-member",
        domain: "127.0.0.1",
        path: "/",
      },
      {
        name: "talaqi_csrf",
        value: "fixture-csrf",
        domain: "127.0.0.1",
        path: "/",
      },
    ]);
    await page.setViewportSize({ width: 320, height: 720 });
    await page.goto(
      `/events/11111111-1111-4111-8111-111111111111?locale=${locale}`,
    );
    await expect(page.locator(".tq-public-shell")).toHaveAttribute(
      "lang",
      locale,
    );
    await expect(page.locator(".tq-public-shell")).toHaveAttribute(
      "dir",
      direction,
    );
    await expect(
      page.getByRole("heading", { level: 1, name: "Istanbul Community Run" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", {
        level: 2,
        name: translate(locale, "discovery.relatedEvents"),
      }),
    ).toBeVisible();
    await expect(page.getByText("Istanbul Park Yoga")).toBeVisible();
    await expect(
      page.getByText(translate(locale, "discovery.clubOrganized")),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: translate(locale, "discovery.openMap") }),
    ).toHaveAttribute("rel", "noreferrer");
    const save = page.getByRole("button", {
      name: translate(locale, "discovery.save"),
    });
    await save.focus();
    await expect(save).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(
      page.getByRole("button", { name: translate(locale, "discovery.unsave") }),
    ).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText(privateCanary)).toHaveCount(0);
    await expect(page.locator("body")).not.toContainText("canonical.webp");
    expect(
      await page.evaluate(
        () =>
          document.documentElement.scrollWidth >
          document.documentElement.clientWidth,
      ),
    ).toBe(false);
  });
}
