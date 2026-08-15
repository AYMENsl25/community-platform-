import { describe, expect, it } from "vitest";
import { getPolicy, POLICY_SLUGS, POLICY_VERSION } from "./policies";

describe("closed beta policies", () => {
  it.each(["en", "tr", "fr", "ar"] as const)(
    "publishes every policy in %s",
    (locale) => {
      for (const slug of POLICY_SLUGS) {
        const policy = getPolicy(locale, slug);
        expect(policy.version).toBe(POLICY_VERSION);
        expect(policy.legalDraft).toBe(true);
        expect(policy.title.length).toBeGreaterThan(2);
        expect(policy.summary.length).toBeGreaterThan(8);
        expect(policy.points).toHaveLength(3);
      }
    },
  );

  it("publishes a support path without requesting secrets", () => {
    const support = getPolicy("en", "support").points.join(" ");
    expect(support).toContain("support@talaqi.app");
    expect(support).toContain("Do not email passwords");
  });
});
