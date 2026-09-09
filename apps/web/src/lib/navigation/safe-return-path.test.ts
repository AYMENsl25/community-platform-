import { describe, expect, it } from "vitest";

import { safeReturnPath } from "./safe-return-path";

describe("safeReturnPath", () => {
  it.each([
    [
      "/events/018f0000-0000-7000-8000-000000000201?locale=ar",
      "/events/018f0000-0000-7000-8000-000000000201?locale=ar",
    ],
    ["/explore?category=sports", "/explore?category=sports"],
    ["/organizer/events", "/organizer/events"],
  ])("keeps an allowlisted same-origin path", (value, expected) => {
    expect(safeReturnPath(value)).toBe(expected);
  });

  it.each([
    "https://attacker.test",
    "//attacker.test/path",
    "/\\attacker.test",
    "/api/public/api/v1/auth/logout",
    "/unknown",
    "/events/not-a-valid-id",
  ])("rejects an unsafe return target", (value) => {
    expect(safeReturnPath(value)).toBe("/");
  });
});
