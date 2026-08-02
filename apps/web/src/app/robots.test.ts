import { describe, expect, it } from "vitest";

import robots from "./robots";

describe("robots", () => {
  it("keeps private workspaces and APIs out of indexing", () => {
    expect(robots()).toMatchObject({
      rules: {
        userAgent: "*",
        allow: ["/", "/api/media/"],
        disallow: ["/admin/", "/organizer/", "/api/"],
      },
      sitemap: "http://localhost:3000/sitemap.xml",
    });
  });
});
