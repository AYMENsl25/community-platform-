import { defineConfig, devices } from "@playwright/test"

const webBaseURL = process.env.E2E_WEB_BASE_URL ?? "http://127.0.0.1:3000"

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  expect: {
    timeout: 5_000,
  },
  use: {
    baseURL: webBaseURL,
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
})
