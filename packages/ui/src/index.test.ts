import { describe, expect, it } from "vitest";

import { UI_PACKAGE_PLACEHOLDER } from "./index";

describe("UI package placeholder", () => {
  it("identifies the primitives owner", () => {
    expect(UI_PACKAGE_PLACEHOLDER).toBe("task-0.6");
  });
});
