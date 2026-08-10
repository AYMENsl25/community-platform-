import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  snapshotPathTemplate: "{testDir}/{testFilePath}-snapshots/{arg}{ext}",
  // The fixture API intentionally models cross-request moderation and organizer
  // state. Keep the repository-wide gate serial so suites cannot mutate the
  // same target while another suite is asserting its public state.
  fullyParallel: false,
  workers: 1,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:3100",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: "node scripts/testing/discovery-fixture-server.mjs",
      url: "http://127.0.0.1:4100/health",
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
    {
      command:
        "corepack pnpm --filter @talaqi/web start --hostname 127.0.0.1 --port 3100",
      url: "http://127.0.0.1:3100",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: { API_PUBLIC_URL: "http://127.0.0.1:4100" },
    },
  ],
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
