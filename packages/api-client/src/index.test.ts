import { describe, expect, it } from "vitest";

import { API_CLIENT_PLACEHOLDER } from "./index";

describe("API client placeholder", () => {
  it("identifies the generation owner", () => {
    expect(API_CLIENT_PLACEHOLDER).toBe("task-0.5");
  });
});
