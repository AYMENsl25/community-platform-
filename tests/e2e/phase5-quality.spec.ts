import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import {
  translate,
  type LocaleCode,
} from "../../packages/translations/src/index";

const locales: LocaleCode[] = ["en", "tr", "fr", "ar"];

async function setMemberLocale(page: Page, locale: LocaleCode) {
  await page.context().addCookies([
    { name: "talaqi_locale", value: locale, url: "http://127.0.0.1:3100" },
    {
      name: "talaqi_access",
      value: "member-token",
      url: "http://127.0.0.1:3100",
    },
    {
      name: "talaqi_csrf",
      value: "fixture-csrf",
      url: "http://127.0.0.1:3100",
    },
  ]);
}

async function expectNoSeriousAccessibilityIssues(page: Page) {
  const result = await new AxeBuilder({ page }).analyze();
  expect(
    result.violations.filter(({ impact }) =>
      ["serious", "critical"].includes(impact ?? ""),
    ),
  ).toEqual([]);
}

async function expectAccessibleContrast(page: Page) {
  const result = await new AxeBuilder({ page })
    .withRules(["color-contrast"])
    .analyze();
  expect(result.violations).toEqual([]);
}

async function expectNoHorizontalOverflow(page: Page) {
  await expect
    .poll(() =>
      page.evaluate(() => {
        if (document.documentElement.scrollWidth <= window.innerWidth) {
          return [];
        }
        return [...document.querySelectorAll<HTMLElement>("body *")]
          .map((element) => {
            const bounds = element.getBoundingClientRect();
            return {
              element: `${element.tagName.toLowerCase()}.${element.className}`,
              left: Math.round(bounds.left),
              right: Math.round(bounds.right),
              width: Math.round(bounds.width),
            };
          })
          .filter(({ left, right }) => left < 0 || right > window.innerWidth)
          .slice(0, 10);
      }),
    )
    .toEqual([]);
}

for (const locale of locales) {
  test(`${locale} critical journey is localized, accessible, and mobile safe`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: 320, height: 720 });
    await page.emulateMedia({ reducedMotion: "reduce" });
    await setMemberLocale(page, locale);

    await page.goto("/");
    await expect(page.locator("html")).toHaveAttribute("lang", locale);
    await expect(page.locator("html")).toHaveAttribute(
      "dir",
      locale === "ar" ? "rtl" : "ltr",
    );
    await expect(
      page.getByRole("heading", { name: translate(locale, "home.title") }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => matchMedia("(prefers-reduced-motion: reduce)").matches,
      ),
    ).toBe(true);
    const transitionDurations = await page
      .getByRole("link", {
        name: translate(locale, "shell.navigation.explore"),
      })
      .first()
      .evaluate((element) =>
        getComputedStyle(element)
          .transitionDuration.split(",")
          .map((duration) => Number.parseFloat(duration) || 0),
      );
    expect(Math.max(...transitionDurations)).toBeLessThanOrEqual(0.001);
    await page.keyboard.press("Tab");
    await expect(
      page.getByRole("link", {
        name: translate(locale, "shell.skipToContent"),
      }),
    ).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page.locator("#main-content")).toBeFocused();
    const accessibleTree = await page.locator("body").ariaSnapshot();
    expect(accessibleTree).toContain(translate(locale, "home.title"));
    expect(accessibleTree).toContain(translate(locale, "a11y.localeSelector"));
    await expectNoHorizontalOverflow(page);
    await expectNoSeriousAccessibilityIssues(page);
    await expectAccessibleContrast(page);

    await page.goto("/explore");
    await expect(
      page.getByRole("heading", { name: translate(locale, "discovery.title") }),
    ).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await expectNoSeriousAccessibilityIssues(page);

    await page.goto("/overview");
    await expect(
      page.getByRole("heading", {
        name: translate(locale, "dashboard.member.title"),
      }),
    ).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await expectNoSeriousAccessibilityIssues(page);
  });
}

test("approved critical-route visual baselines", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await setMemberLocale(page, "en");
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("/");
  await expect(page).toHaveScreenshot("home-en-desktop.png", {
    animations: "disabled",
    maxDiffPixelRatio: 0.06,
  });

  await setMemberLocale(page, "ar");
  await page.setViewportSize({ width: 320, height: 720 });
  await page.goto("/overview");
  await expect(page).toHaveScreenshot("member-dashboard-ar-mobile.png", {
    animations: "disabled",
    maxDiffPixelRatio: 0.06,
  });
});
