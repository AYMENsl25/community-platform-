import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
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
