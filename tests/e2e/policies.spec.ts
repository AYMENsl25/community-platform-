import { expect, test } from "@playwright/test";

const titles = {
  en: "Privacy notice",
  tr: "Gizlilik bildirimi",
  fr: "Avis de confidentialité",
  ar: "إشعار الخصوصية",
} as const;

for (const locale of ["en", "tr", "fr", "ar"] as const) {
  test(`${locale} policy and support paths are localized, linked, and narrow-safe`, async ({
    context,
    page,
  }) => {
    await context.addCookies([
      { name: "talaqi_locale", value: locale, url: "http://127.0.0.1:3100" },
    ]);
    await page.setViewportSize({ width: 320, height: 720 });
    await page.goto("/policies/privacy");
    await expect(page.locator(".tq-public-shell")).toHaveAttribute(
      "dir",
      locale === "ar" ? "rtl" : "ltr",
    );
    await expect(
      page.getByRole("heading", { level: 1, name: titles[locale] }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: /support|destek|assistance|الدعم/i }),
    ).toHaveAttribute("href", "/policies/support");
    expect(
      await page.evaluate(
        () =>
          document.documentElement.scrollWidth >
          document.documentElement.clientWidth,
      ),
    ).toBe(false);
  });
}
