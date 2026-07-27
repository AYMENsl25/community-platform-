import { expect, test } from "@playwright/test";

const locales = [
  ["en", "ltr"],
  ["tr", "ltr"],
  ["fr", "ltr"],
  ["ar", "rtl"],
] as const;
const privateCanary = "PRIVATE_EXACT_ADDRESS_CANARY";

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

test("desktop navigation reaches club and event details", async ({ page }) => {
  await page.goto("/explore");
  await page.getByRole("link", { name: /Istanbul Community Run/i }).click();
  await expect(page).toHaveURL(
    /\/events\/11111111-1111-4111-8111-111111111111/,
  );
  await expect(page.getByText("Park entrance")).toBeVisible();
  await expect(page.getByText(privateCanary)).toHaveCount(0);

  await page.goto("/explore");
  await page.getByRole("link", { name: /Istanbul Neighbours/i }).click();
  await expect(page).toHaveURL(/\/clubs\/istanbul-neighbours/);
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
