import { expect, test } from "@playwright/test";
import { translate } from "../../packages/translations/src/index";

for (const locale of ["en", "tr", "fr", "ar"] as const) {
  test(`${locale} renders localized content and direction without narrow overflow`, async ({
    context,
    page,
  }) => {
    await context.addCookies([
      { name: "talaqi_locale", value: locale, url: "http://127.0.0.1:3100" },
    ]);
    await page.setViewportSize({ width: 320, height: 720 });
    await page.goto("/");
    await expect(page.locator("html")).toHaveAttribute("lang", locale);
    await expect(page.locator("html")).toHaveAttribute(
      "dir",
      locale === "ar" ? "rtl" : "ltr",
    );
    await expect(page.locator(".tq-public-shell")).toHaveAttribute(
      "lang",
      locale,
    );
    await expect(page.locator(".tq-public-shell")).toHaveAttribute(
      "dir",
      locale === "ar" ? "rtl" : "ltr",
    );
    await expect(
      page.getByRole("heading", {
        level: 1,
        name: translate(locale, "home.title"),
      }),
    ).toBeVisible();
    await expect(
      page.getByRole("combobox", {
        name: translate(locale, "a11y.localeSelector"),
      }),
    ).toHaveValue(locale);
    expect(
      await page.evaluate(
        () =>
          document.documentElement.scrollWidth >
          document.documentElement.clientWidth,
      ),
    ).toBe(false);
  });
}

test.describe("request and client locale changes", () => {
  test.use({ locale: "fr-FR" });
  test("Accept-Language selects French and client switching rerenders Arabic immediately", async ({
    page,
  }) => {
    await page.goto("/");
    await expect(page.locator("html")).toHaveAttribute("lang", "fr");
    await page
      .getByRole("combobox", {
        name: translate("fr", "a11y.localeSelector"),
      })
      .selectOption("ar");
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
    await expect(page.locator(".tq-public-shell")).toHaveAttribute(
      "dir",
      "rtl",
    );
    await expect(
      page.getByRole("heading", {
        level: 1,
        name: translate("ar", "home.title"),
      }),
    ).toBeVisible();
  });
});

test("pseudo-long localized content remains contained at 320px", async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 720 });
  await page.goto("/");
  await page.locator("h1").evaluate((heading) => {
    heading.textContent = "[LONG] ".repeat(30);
  });
  expect(
    await page.evaluate(
      () =>
        document.documentElement.scrollWidth >
        document.documentElement.clientWidth,
    ),
  ).toBe(false);
});
