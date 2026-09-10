import { expect, test, type BrowserContext, type Page } from "@playwright/test";

test.describe.configure({ mode: "serial" });

const organizerClubId = "77777777-7777-4777-8777-777777777777";

async function signInAsFixtureRole(
  context: BrowserContext,
  role: "owner" | "member",
) {
  await context.addCookies([
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
    {
      name: "talaqi_locale",
      value: "en",
      domain: "127.0.0.1",
      path: "/",
    },
  ]);
}

async function completeClubProfile(page: Page) {
  await page
    .getByRole("textbox", { name: "Description" })
    .fill("Weekly runs where neighbors meet and train together.");
  await page.getByLabel("Category").selectOption("sports");
  await page.getByLabel("Country").selectOption("TR");
  await page.getByLabel("City").selectOption("istanbul");
  const profileForm = page.locator("form.tq-club-form");
  await expect(page.getByRole("textbox", { name: "Description" })).toHaveValue(
    "Weekly runs where neighbors meet and train together.",
  );
  expect(
    await profileForm.evaluate((form: HTMLFormElement) => form.checkValidity()),
  ).toBe(true);

  const [request] = await Promise.all([
    page.waitForRequest(
      (candidate) =>
        candidate.method() === "PATCH" &&
        candidate.url().includes(`/api/v1/clubs/${organizerClubId}`),
    ),
    page.getByRole("button", { name: "Save club profile" }).click(),
  ]);

  expect(request.url()).toContain(`/api/v1/clubs/${organizerClubId}`);
  expect(request.headers()["x-csrf-token"]).toBe("fixture-csrf");
  expect(request.postDataJSON()).toMatchObject({
    revision: 1,
    name: "Workspace Runners",
    slug: "workspace-runners",
    category_slug: "sports",
    country_code: "TR",
    city_slug: "istanbul",
  });
  await expect(page.getByRole("status")).toContainText("Club profile saved.");
  await expect(page.getByText("Published").first()).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Open public profile" }),
  ).toBeVisible();
}

test("club owner completes setup, approves a member, and publishes an announcement", async ({
  context,
  page,
}) => {
  test.setTimeout(60_000);
  await signInAsFixtureRole(context, "owner");
  const communicationsLoaded = page.waitForResponse(
    (response) =>
      response.request().method() === "GET" &&
      response.url().includes(`/api/v1/clubs/${organizerClubId}/announcements`),
  );
  await page.goto("/organizer/clubs");
  await expect(
    page.getByRole("heading", { name: "Club organizer workspace" }),
  ).toBeVisible();
  await communicationsLoaded;

  await completeClubProfile(page);

  const pendingMember = page.getByRole("listitem").filter({
    hasText: "Pending Fixture",
  });
  await pendingMember
    .getByRole("textbox", { name: "Decision reason" })
    .fill("Community guidelines accepted");
  await pendingMember.getByRole("button", { name: "Approve request" }).click();
  await expect(
    page.getByText("There are no pending join requests."),
  ).toBeVisible();

  const announcements = page
    .getByRole("heading", { name: "Club announcements" })
    .locator("..");
  await announcements
    .getByRole("textbox", { name: "Subject" })
    .fill("Saturday route confirmed");
  await announcements
    .getByRole("textbox", { name: "Message" })
    .fill("Meet at the park entrance at 8:00 AM.");

  const announcementRequest = page.waitForRequest(
    (request) =>
      request.method() === "POST" &&
      request.url().endsWith(`/api/v1/clubs/${organizerClubId}/announcements`),
  );
  await announcements.getByRole("button", { name: "Publish update" }).click();
  const request = await announcementRequest;

  expect(request.headers()["x-csrf-token"]).toBe("fixture-csrf");
  expect(request.headers()["idempotency-key"]).toMatch(
    /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
  );
  expect(request.postDataJSON()).toEqual({
    title: "Saturday route confirmed",
    body: "Meet at the park entrance at 8:00 AM.",
    audience: "all_members",
  });
  await expect(
    announcements.getByText("Saturday route confirmed"),
  ).toBeVisible();
  await expect(
    announcements.getByText("Meet at the park entrance at 8:00 AM."),
  ).toBeVisible();
});

test("ordinary member cannot access club owner data or actions", async ({
  context,
  page,
}) => {
  await signInAsFixtureRole(context, "member");
  await page.goto("/organizer/clubs");

  await expect(
    page.getByText("You do not own or manage a club yet."),
  ).toBeVisible();
  await expect(page.getByText("owner@example.test")).toHaveCount(0);
  await expect(page.getByText("pending@example.test")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Save club profile" }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Approve request" }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Publish update" }),
  ).toHaveCount(0);
});
