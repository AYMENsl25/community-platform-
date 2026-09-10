import { expect, test } from "@playwright/test";

const eventPath = "/events/11111111-1111-4111-8111-111111111111";
const fixtureMemberPassword = "FixtureMember123!"; // pragma: allowlist secret

async function signInAsFixtureMember(
  context: import("@playwright/test").BrowserContext,
) {
  await context.addCookies([
    {
      name: "talaqi_access",
      value: "fixture-member-persona",
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
}

test.describe("public and member persona journeys", () => {
  test("visitor finds a local activity and receives a clear sign-in boundary", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto("/");

    await expect(
      page.getByRole("heading", {
        level: 2,
        name: "Featured near you",
      }),
    ).toBeVisible();
    await page
      .getByRole("link", { name: "Sports", exact: true })
      .last()
      .click();
    await expect(page).toHaveURL(/\/explore\?category=sports/);

    await page.getByRole("link", { name: "Istanbul Community Run" }).click();
    await expect(page).toHaveURL(new RegExp(`${eventPath}$`));
    await expect(page.getByText("Park entrance").first()).toBeVisible();
    await expect(page.getByText("Moda Community Hall, Kadikoy")).toHaveCount(0);

    await page.getByRole("button", { name: "Register" }).click();
    await expect(
      page.getByText("Sign in to register for this event."),
    ).toBeVisible({ timeout: 15_000 });
    await page.getByRole("link", { name: "Sign in to register" }).click();
    await expect(page).toHaveURL(
      /\/login\?returnTo=%2Fevents%2F11111111-1111-4111-8111-111111111111&locale=en$/,
    );
    await expect(
      page.getByRole("heading", { name: "Welcome back" }),
    ).toBeVisible();
    await page
      .getByRole("textbox", { name: "Email or username" })
      .fill("member@example.test");
    await page.getByLabel("Password").fill(fixtureMemberPassword);
    await page.getByRole("button", { name: "Sign in securely" }).click();
    await expect(page).toHaveURL(new RegExp(`${eventPath}$`));
    await expect(page.getByText("Moda Community Hall, Kadikoy")).toHaveCount(0);
  });

  test("member can save, register, view permitted venue information, and cancel", async ({
    context,
    page,
  }) => {
    await signInAsFixtureMember(context);
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(eventPath);

    const save = page.getByRole("button", { name: "Save event" });
    await save.click();
    await expect(
      page.getByRole("button", { name: "Remove saved event" }),
    ).toHaveAttribute("aria-pressed", "true", { timeout: 15_000 });

    await page.getByRole("button", { name: "Register" }).click();
    await expect(page.getByText("Registration confirmed")).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByText("Moda Community Hall, Kadikoy")).toBeVisible();

    await page.getByRole("button", { name: "Cancel registration" }).click();
    await expect(page.getByRole("button", { name: "Register" })).toBeVisible();
    await expect(page.getByText("Moda Community Hall, Kadikoy")).toHaveCount(0);
    await expect(page.getByText(/Private venue/i)).toBeVisible();
  });
});
